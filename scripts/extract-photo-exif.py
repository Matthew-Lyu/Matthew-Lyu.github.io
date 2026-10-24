#!/usr/bin/env python3
"""Extract the six displayed EXIF fields from original photos, without re-encoding them."""

import argparse
import json
import math
from pathlib import Path
from urllib.parse import quote, unquote

from PIL import Image


def clean_text(value):
    if value is None:
        return None
    if isinstance(value, bytes):
        value = value.decode('utf-8', errors='replace')
    return str(value).replace('\x00', '').strip() or None


def positive_number(value):
    if isinstance(value, (tuple, list)):
        value = value[0] if value else None
    try:
        number = float(value)
        return number if math.isfinite(number) and number > 0 else None
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def extract(path):
    with Image.open(path) as image:
        top = image.getexif()
        details = top.get_ifd(34665)
        get = lambda tag: details.get(tag, top.get(tag))
        values = {
            'camera': clean_text(get(272)),
            'lens': clean_text(get(42036)),
        }
        focal = positive_number(get(37386))
        aperture = positive_number(get(33437))
        shutter = positive_number(get(33434))
        iso = positive_number(get(34855))
        if focal is not None:
            values['focal_length'] = f'{focal:g} mm'
        if aperture is not None:
            values['aperture'] = f'f/{aperture:g}'
        if shutter is not None:
            denominator = round(1 / shutter)
            if shutter < 1 and denominator > 1 and abs(1 / denominator - shutter) / shutter < 0.001:
                values['shutter'] = f'1/{denominator} s'
            else:
                values['shutter'] = f'{shutter:g} s'
        if iso is not None:
            values['iso'] = f'ISO {iso:g}'
        return {key: value for key, value in values.items() if value}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='Original photo directory')
    parser.add_argument('--prefix', required=True, help='Exported image URL directory, e.g. /assets/photos/selected/')
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / '_data/photo_exif.json')
    args = parser.parse_args()
    if not args.source.is_dir():
        parser.error('Source must be an existing directory.')
    prefix = '/' + args.prefix.strip('/') + '/'
    data = json.loads(args.output.read_text()) if args.output.exists() else {}
    files = sorted(path for path in args.source.iterdir() if path.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'})
    populated = 0
    for path in files:
        # Prefer the actual website filename, including uppercase .JPG extensions.
        # Also recognize older exports that normalized the extension to .jpg.
        root = Path(__file__).resolve().parents[1]
        exact = root / unquote(prefix + path.name).lstrip('/')
        exported = root / unquote(prefix + path.stem + '.jpg').lstrip('/')
        name = exported.name if not exact.exists() and exported.exists() else path.name
        key = quote(prefix + name, safe='/')
        fields = extract(path)
        if fields:
            data[key] = fields
            populated += 1
        else:
            data.pop(key, None)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + '\n')
    print(f'Extracted EXIF for {populated}/{len(files)} photos into {args.output}')


if __name__ == '__main__':
    main()
