#!/usr/bin/env python3
"""Burn a small gray @mattlyu watermark into album JPEGs, preserving photo metadata."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
STYLE = {'version': 1, 'text': '@mattlyu', 'color': '#b8b8b8', 'opacity': 210,
         'font_ratio': 0.024, 'margin_ratio': 0.02, 'quality': 95}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def default_font():
    candidates = (
        '/System/Library/Fonts/Helvetica.ttc',
        '/System/Library/Fonts/Supplemental/Arial.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        'C:/Windows/Fonts/arial.ttf',
    )
    return next((Path(name) for name in candidates if Path(name).is_file()), None)


def draw_watermark(image, font_path):
    """Return the composited image and watermark bounds in stored-pixel coordinates."""
    short_edge = min(image.size)
    font_size = max(12, round(short_edge * STYLE['font_ratio']))
    margin = max(8, round(short_edge * STYLE['margin_ratio']))
    font = ImageFont.truetype(str(font_path), font_size)
    stroke = max(1, round(font_size * 0.02))
    left, top, right, bottom = font.getbbox(STYLE['text'], stroke_width=stroke)
    x, y = margin - left, image.height - margin - bottom
    overlay = Image.new('RGBA', image.size)
    draw = ImageDraw.Draw(overlay)
    draw.text((x, y), STYLE['text'], font=font, fill=(184, 184, 184, STYLE['opacity']),
              stroke_width=stroke, stroke_fill=(30, 30, 30, 85))
    result = Image.alpha_composite(image.convert('RGBA'), overlay).convert(image.mode)
    return result, [margin, y + top, x + right, image.height - margin]


def watermark_file(source, font_path):
    original_stat = source.stat()
    with Image.open(source) as original:
        if original.format != 'JPEG' or original.mode not in ('RGB', 'L'):
            raise ValueError(f'Please first convert to a standard JPEG: {source}')
        if original.getexif().get(274, 1) != 1:
            raise ValueError(f'Normalize photo orientation before watermarking: {source}')
        original.load()
        dimensions = original.size
        metadata = original.info.copy()
        marked, bounds = draw_watermark(original, font_path)
        options = dict(quality=STYLE['quality'], subsampling=0, optimize=True, progressive=True)
        for key in ('exif', 'icc_profile', 'xmp', 'dpi'):
            if metadata.get(key):
                options[key] = metadata[key]
        with tempfile.NamedTemporaryFile(dir=source.parent, prefix='.watermark-', suffix='.tmp', delete=False) as handle:
            temporary = Path(handle.name)
        try:
            marked.save(temporary, format='JPEG', **options)
            with Image.open(temporary) as check:
                check.load()
                assert check.size == dimensions
                for key in ('exif', 'icc_profile', 'xmp'):
                    assert check.info.get(key, b'') == metadata.get(key, b''), (source, key)
            current = source.stat()
            if (current.st_mtime_ns, current.st_size) != (original_stat.st_mtime_ns, original_stat.st_size):
                raise RuntimeError(f'Photo was edited concurrently: {source}')
            os.chmod(temporary, original_stat.st_mode & 0o777)
            os.replace(temporary, source)
        finally:
            temporary.unlink(missing_ok=True)
    return {'sha256': digest(source), 'dimensions': list(dimensions), 'bounds': bounds}


def save_manifest(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, suffix='.tmp', mode='w', delete=False) as handle:
        temporary = Path(handle.name)
        json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write('\n')
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', nargs='?', type=Path, default=ROOT / 'assets/photos')
    parser.add_argument('--font', type=Path, default=default_font())
    parser.add_argument('--manifest', type=Path, default=ROOT / '_data/photo_watermarks.json')
    args = parser.parse_args()
    folder = args.folder.expanduser().resolve()
    if not folder.is_dir() or folder.name == 'thumbs':
        parser.error('Specify an album directory or assets/photos, not thumbs.')
    if not args.font or not args.font.is_file():
        parser.error('No font found; use --font /path/to/font.ttf.')
    data = json.loads(args.manifest.read_text()) if args.manifest.exists() else {'style': STYLE, 'images': {}}
    if data['style'] != STYLE:
        parser.error('Watermark style changed. Reimport unwatermarked backups before changing style.')
    photos = sorted(p for p in folder.rglob('*') if p.is_file()
                    and p.suffix.lower() in ('.jpg', '.jpeg')
                    and 'thumbs' not in p.relative_to(folder).parts)
    made = skipped = 0
    for source in photos:
        try:
            key = source.relative_to(ROOT).as_posix()
        except ValueError:
            key = source.as_posix()
        if data['images'].get(key, {}).get('sha256') == digest(source):
            skipped += 1
            continue
        data['images'][key] = watermark_file(source, args.font)
        save_manifest(args.manifest, data)
        made += 1
        print(f'Watermarked: {key}', flush=True)
    print(f'Watermarked {made}; already marked {skipped}. Regenerate thumbs afterwards.')


if __name__ == '__main__':
    main()
