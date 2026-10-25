#!/usr/bin/env python3
"""Generate responsive album/cover previews in the build output; keep originals intact."""

import argparse
import hashlib
from html import escape
from html.parser import HTMLParser
import os
from pathlib import Path
import shutil
import tempfile
from urllib.parse import unquote, urlsplit

from PIL import Image, ImageOps, __version__ as pillow_version


WIDTHS = (480, 960)
QUALITY = 82
PHOTO_WIDTHS = (480, 960, 1600, 2400)
PHOTO_QUALITY = 85
PHOTO_SIZES = ('(max-width: 480px) calc(100vw - 40px), '
               '(max-width: 850px) calc((100vw - 58px) / 2), '
               '(max-width: 1344px) calc((100vw - 164px) / 3), 394px')
SIZES = ('(max-width: 480px) calc(100vw - 40px), '
         '(max-width: 600px) calc(100vw - 48px), '
         '(max-width: 850px) calc((100vw - 66px) / 2), '
         '(max-width: 1344px) calc((100vw - 188px) / 3), '
         '(max-width: 1400px) 386px, 284px')


def save_preview(image, target, width, profile, quality):
    height = max(1, round(image.height * width / image.width))
    resized = image.resize((width, height), Image.Resampling.LANCZOS)
    options = {'quality': quality, 'method': 4}
    if profile:
        options['icc_profile'] = profile
    with tempfile.NamedTemporaryFile(dir=target.parent, suffix='.webp', delete=False) as handle:
        temporary = Path(handle.name)
    try:
        resized.save(temporary, format='WEBP', **options)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


class Previews(HTMLParser):
    def __init__(self, html, source, destination, baseurl, kind='cover', shared=None):
        super().__init__(convert_charrefs=False)
        self.html = html
        self.source = source
        self.destination = destination
        self.baseurl = baseurl.rstrip('/')
        self.kind = kind
        self.widths = PHOTO_WIDTHS if kind == 'photo' else WIDTHS
        self.quality = PHOTO_QUALITY if kind == 'photo' else QUALITY
        self.photo_url = None
        self.cache = source / '.cover-cache'
        self.output = destination / 'assets/generated' / ('photos' if kind == 'photo' else 'covers')
        self.replacements = []
        self.previews = {} if shared is None else shared
        self.count = self.created = 0
        self.line_offsets = [0]
        for line in html.splitlines(keepends=True):
            self.line_offsets.append(self.line_offsets[-1] + len(line))

    def variants(self, original_url):
        parsed = urlsplit(original_url)
        if parsed.scheme or parsed.netloc:
            return None
        path = unquote(parsed.path)
        if self.baseurl:
            if not path.startswith(self.baseurl + '/'):
                return None
            path = path[len(self.baseurl):]
        relative = Path(path.lstrip('/'))
        if relative.parts[:2] != ('assets', 'photos'):
            return None
        original = (self.source / relative).resolve()
        original.relative_to(self.source)  # Reject paths outside this checkout.
        cache_key = (original, self.kind)
        if cache_key in self.previews:
            return self.previews[cache_key]
        if not original.is_file():
            raise FileNotFoundError(f'Album image does not exist: {relative}')
        digest = hashlib.sha256()
        digest.update(f'cover-v1-webp-{self.widths}-{self.quality}-{pillow_version}'.encode())
        with original.open('rb') as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b''):
                digest.update(chunk)
        key = digest.hexdigest()[:24]
        with Image.open(original) as image:
            if getattr(image, 'is_animated', False):
                return None
            source_width, source_height = image.size
            if image.getexif().get(274, 1) in (5, 6, 7, 8):
                source_width, source_height = source_height, source_width
            widths = sorted({min(width, source_width) for width in self.widths})
            self.cache.mkdir(parents=True, exist_ok=True)
            self.output.mkdir(parents=True, exist_ok=True)
            files = [(width, self.cache / f'{key}-{width}.webp') for width in widths]
            missing = [(width, target) for width, target in files if not target.is_file()]
            if missing:
                profile = image.info.get('icc_profile')
                oriented = ImageOps.exif_transpose(image)
                if oriented.mode not in ('RGB', 'RGBA', 'L'):
                    oriented = oriented.convert('RGBA' if 'transparency' in image.info else 'RGB')
                    profile = None
                for width, target in missing:
                    save_preview(oriented, target, width, profile, self.quality)
                    self.created += 1
        result = []
        for width, cached in files:
            target = self.output / cached.name
            if not target.is_file():
                with tempfile.NamedTemporaryFile(dir=self.output, suffix='.webp', delete=False) as handle:
                    temporary = Path(handle.name)
                try:
                    shutil.copyfile(cached, temporary)
                    os.replace(temporary, target)
                finally:
                    temporary.unlink(missing_ok=True)
            url = f'{self.baseurl}/assets/generated/{self.output.name}/{cached.name}'
            result.append((url, width, max(1, round(source_height * width / source_width))))
        data = {'variants': result, 'width': source_width, 'height': source_height}
        self.previews[cache_key] = data
        return data

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if self.kind == 'photo' and tag == 'a':
            self.photo_url = attrs.get('href') if 'data-photo' in attrs else None
        if tag != 'img':
            return
        if self.kind == 'cover':
            if 'album-cover' not in attrs.get('class', '').split():
                return
            original = attrs.get('data-cover-source', attrs.get('src', ''))
        else:
            if not self.photo_url:
                return
            original = self.photo_url
        data = self.variants(original)
        if not data:
            return
        previews = data['variants']
        attrs.update({
            'src': previews[0][0],
            'srcset': ', '.join(f'{url} {width}w' for url, width, _ in previews),
            'sizes': PHOTO_SIZES if self.kind == 'photo' else SIZES,
            'width': str(data['width'] if self.kind == 'photo' else previews[0][1]),
            'height': str(data['height'] if self.kind == 'photo' else previews[0][2]),
            f'data-{self.kind}-source': original,
            'loading': 'eager' if self.count < (1 if self.kind == 'photo' else 3) else 'lazy',
        })
        if self.kind == 'photo':
            # Stable source proportions prevent row reshuffling as srcset loads.
            attrs['data-photo-width'] = str(data['width'])
            attrs['data-photo-height'] = str(data['height'])
        if self.count == 0:
            attrs['fetchpriority'] = 'high'
        new_tag = '<img ' + ' '.join(
            key if value is None else f'{key}="{escape(value, quote=True)}"'
            for key, value in attrs.items()
        ) + '>'
        line, column = self.getpos()
        start = self.line_offsets[line - 1] + column
        self.replacements.append((start, start + len(self.get_starttag_text()), new_tag))
        self.count += 1

    handle_startendtag = handle_starttag

    def handle_endtag(self, tag):
        if tag == 'a':
            self.photo_url = None


def optimize_page(index, source, destination, baseurl, kind, shared):
    html = index.read_text(encoding='utf-8')
    parser = Previews(html, source, destination, baseurl, kind, shared)
    parser.feed(html)
    parser.close()
    for start, end, replacement in reversed(parser.replacements):
        html = html[:start] + replacement + html[end:]
    with tempfile.NamedTemporaryFile(dir=index.parent, suffix='.html', mode='w', encoding='utf-8', delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(html)
    try:
        os.replace(temporary, index)
    finally:
        temporary.unlink(missing_ok=True)
    return parser.count, parser.created


def optimize_site(source, destination, baseurl=''):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    root = destination / 'photography'
    result = {'covers': 0, 'photos': 0, 'created': 0}
    shared = {}
    for index in sorted(root.rglob('index.html')):
        kind = 'cover' if index == root / 'index.html' else 'photo'
        count, created = optimize_page(index, source, destination, baseurl, kind, shared)
        result['covers' if kind == 'cover' else 'photos'] += count
        result['created'] += created
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--baseurl', default='')
    args = parser.parse_args()
    result = optimize_site(args.source, args.destination, args.baseurl)
    print(f'Image previews: {result["covers"]} covers, {result["photos"]} album photos; '
          f'{result["created"]} new variants (others cached).')


if __name__ == '__main__':
    main()
