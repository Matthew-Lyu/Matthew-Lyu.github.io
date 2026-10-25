#!/usr/bin/env python3
"""Optimize rendered album covers; originals and album pages are never modified."""

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
SIZES = ('(max-width: 480px) calc(100vw - 40px), '
         '(max-width: 600px) calc(100vw - 48px), '
         '(max-width: 850px) calc((100vw - 66px) / 2), '
         '(max-width: 1344px) calc((100vw - 188px) / 3), '
         '(max-width: 1400px) 386px, 284px')


def save_preview(image, target, width, profile):
    height = max(1, round(image.height * width / image.width))
    resized = image.resize((width, height), Image.Resampling.LANCZOS)
    options = {'quality': QUALITY, 'method': 4}
    if profile:
        options['icc_profile'] = profile
    with tempfile.NamedTemporaryFile(dir=target.parent, suffix='.webp', delete=False) as handle:
        temporary = Path(handle.name)
    try:
        resized.save(temporary, format='WEBP', **options)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


class Covers(HTMLParser):
    def __init__(self, html, source, destination, baseurl):
        super().__init__(convert_charrefs=False)
        self.html = html
        self.source = source
        self.destination = destination
        self.baseurl = baseurl.rstrip('/')
        self.cache = source / '.cover-cache'
        self.output = destination / 'assets/generated/covers'
        self.replacements = []
        self.previews = {}
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
        if original in self.previews:
            return self.previews[original]
        if not original.is_file():
            raise FileNotFoundError(f'Album cover does not exist: {relative}')
        digest = hashlib.sha256()
        digest.update(f'cover-v1-webp-{WIDTHS}-{QUALITY}-{pillow_version}'.encode())
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
            widths = sorted({min(width, source_width) for width in WIDTHS})
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
                    save_preview(oriented, target, width, profile)
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
            url = f'{self.baseurl}/assets/generated/covers/{cached.name}'
            result.append((url, width, max(1, round(source_height * width / source_width))))
        self.previews[original] = result
        return result

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag != 'img' or 'album-cover' not in attrs.get('class', '').split():
            return
        original = attrs.get('data-cover-source', attrs.get('src', ''))
        previews = self.variants(original)
        if not previews:
            return
        attrs.update({
            'src': previews[0][0],
            'srcset': ', '.join(f'{url} {width}w' for url, width, _ in previews),
            'sizes': SIZES,
            'width': str(previews[0][1]),
            'height': str(previews[0][2]),
            'data-cover-source': original,
            'loading': 'eager' if self.count < 3 else 'lazy',
        })
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


def optimize_site(source, destination, baseurl=''):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    index = destination / 'photography/index.html'
    if not index.is_file():
        return {'covers': 0, 'created': 0}
    html = index.read_text(encoding='utf-8')
    parser = Covers(html, source, destination, baseurl)
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
    return {'covers': parser.count, 'created': parser.created}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--baseurl', default='')
    args = parser.parse_args()
    result = optimize_site(args.source, args.destination, args.baseurl)
    print(f'Cover previews: {result["covers"]} covers; {result["created"]} new variants (others cached).')


if __name__ == '__main__':
    main()
