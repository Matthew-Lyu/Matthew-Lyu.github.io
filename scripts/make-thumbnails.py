#!/usr/bin/env python3
"""Create same-name thumbnails in an album's thumbs/ folder; preserve originals."""

import argparse
import os
from pathlib import Path
import tempfile

from PIL import Image, ImageOps


EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.avif', '.gif'}


def make_thumbnail(source, target, size):
    with Image.open(source) as original:
        if getattr(original, 'is_animated', False):
            return False
        image_format = original.format
        profile = original.info.get('icc_profile')
        image = ImageOps.exif_transpose(original)
        image.thumbnail((size, size), Image.Resampling.LANCZOS)
        if image_format == 'JPEG' and image.mode not in ('RGB', 'L'):
            image = image.convert('RGB')
            profile = None
        options = {}
        if profile:
            options['icc_profile'] = profile
        if image_format == 'JPEG':
            options.update(quality=85, optimize=True, progressive=True)
        elif image_format == 'PNG':
            options['optimize'] = True
        elif image_format == 'WEBP':
            options.update(quality=85, method=6)
        elif image_format == 'AVIF':
            options['quality'] = 70
        # Do not carry large camera metadata into thumbnail files.
        image.info.pop('exif', None)
        with tempfile.NamedTemporaryFile(dir=target.parent, suffix='.tmp', delete=False) as handle:
            temporary = Path(handle.name)
        try:
            image.save(temporary, format=image_format, **options)
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
        return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('album', type=Path, help='Album image folder')
    parser.add_argument('--size', type=int, default=960, help='Maximum long edge in pixels (default: 960)')
    parser.add_argument('--overwrite', action='store_true', help='Regenerate existing thumbnails')
    args = parser.parse_args()
    album = args.album.expanduser().resolve()
    if not album.is_dir():
        parser.error('相册文件夹不存在。')
    if args.size < 1:
        parser.error('--size 必须为正整数。')
    if album.name.lower() == 'thumbs':
        parser.error('请指定相册文件夹，而不是 thumbs 文件夹。')
    destination = album / 'thumbs'
    destination.mkdir(exist_ok=True)
    made = skipped = errors = 0
    for source in sorted(album.iterdir(), key=lambda path: path.name.casefold()):
        if not source.is_file() or source.suffix.lower() not in EXTENSIONS:
            continue
        target = destination / source.name
        if target.exists() and not args.overwrite:
            skipped += 1
            continue
        try:
            if make_thumbnail(source, target, args.size):
                made += 1
            else:
                skipped += 1
                print(f'跳过动画图片：{source.name}')
        except (OSError, ValueError) as error:
            errors += 1
            print(f'未能处理 {source.name}：{error}')
    print(f'生成 {made} 张，跳过 {skipped} 张，失败 {errors} 张。\n缩略图目录：{destination}')
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
