#!/usr/bin/env python3
"""Burn white @mattlyu text with a dark outline and soft shadow into JPEGs."""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
LEGACY_STYLE = {'version': 1, 'text': '@mattlyu', 'color': '#b8b8b8', 'opacity': 210,
                'font_ratio': 0.024, 'margin_ratio': 0.02, 'quality': 95}
ADAPTIVE_STYLE = {**LEGACY_STYLE, 'version': 2, 'color_mode': 'adaptive',
                  'dark_color': '#202020', 'luminance_threshold': 128}
STYLE = {**LEGACY_STYLE, 'version': 3, 'color': '#f5f5f5', 'opacity': 245,
         'stroke_color': '#202020', 'stroke_opacity': 210, 'stroke_ratio': 0.055,
         'shadow_opacity': 65, 'shadow_blur_ratio': 0.035, 'shadow_offset_ratio': 0.02}


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


def geometry(image, font_path):
    """Keep the text baseline and glyph positions identical to versions 1 and 2."""
    short_edge = min(image.size)
    font_size = max(12, round(short_edge * STYLE['font_ratio']))
    margin = max(8, round(short_edge * STYLE['margin_ratio']))
    font = ImageFont.truetype(str(font_path), font_size)
    stroke = max(1, round(font_size * 0.02))
    left, top, right, bottom = font.getbbox(STYLE['text'], stroke_width=stroke)
    x, y = margin - left, image.height - margin - bottom
    bounds = [margin, y + top, x + right, image.height - margin]
    return font, font_size, stroke, x, y, bounds


def legacy_overlay(image, font_path, color):
    font, _, stroke, x, y, bounds = geometry(image, font_path)
    overlay = Image.new('RGBA', (bounds[2] - bounds[0], bounds[3] - bounds[1]))
    draw = ImageDraw.Draw(overlay)
    gray = int(color[1:3], 16)
    draw.text((x - bounds[0], y - bounds[1]), STYLE['text'], font=font,
              fill=(gray, gray, gray, LEGACY_STYLE['opacity']),
              stroke_width=stroke, stroke_fill=(30, 30, 30, 85))
    return overlay, bounds


def outlined_overlay(image, font_path):
    """A near-opaque white fill, thin dark outline and restrained blurred shadow."""
    font, font_size, _, x, y, _ = geometry(image, font_path)
    stroke = max(1, round(font_size * STYLE['stroke_ratio']))
    blur = max(0.8, font_size * STYLE['shadow_blur_ratio'])
    offset = max(1, round(font_size * STYLE['shadow_offset_ratio']))
    left, top, right, bottom = font.getbbox(STYLE['text'], stroke_width=stroke)
    padding = math.ceil(blur * 3)
    bounds = [max(0, x + left - padding), max(0, y + top - padding),
              min(image.width, x + right + padding), min(image.height, y + bottom + offset + padding)]
    size = (bounds[2] - bounds[0], bounds[3] - bounds[1])
    origin = (x - bounds[0], y - bounds[1])
    shadow_mask = Image.new('L', size)
    ImageDraw.Draw(shadow_mask).text((origin[0], origin[1] + offset), STYLE['text'], font=font,
                                    fill=STYLE['shadow_opacity'], stroke_width=stroke,
                                    stroke_fill=STYLE['shadow_opacity'])
    shadow = Image.new('RGBA', size, (0, 0, 0, 0))
    shadow.putalpha(shadow_mask.filter(ImageFilter.GaussianBlur(blur)))
    ink = Image.new('RGBA', size)
    ImageDraw.Draw(ink).text(origin, STYLE['text'], font=font, fill=(245, 245, 245, STYLE['opacity']),
                            stroke_width=stroke, stroke_fill=(32, 32, 32, STYLE['stroke_opacity']))
    return Image.alpha_composite(shadow, ink), bounds


def draw_watermark(image, font_path):
    """Composite one outlined watermark on an unwatermarked image."""
    overlay, bounds = outlined_overlay(image, font_path)
    result = image.copy()
    patch = Image.alpha_composite(image.crop(bounds).convert('RGBA'), overlay).convert(image.mode)
    result.paste(patch, bounds)
    return result, bounds


def replace_watermark(image, old_overlay, new_overlay, bounds):
    """Replace the old alpha composite without stamping text on top of old ink.

    Recover only the background contribution needed for the new composite:
    new = a_new * ink_new + (old - a_old * ink_old) * (1-a_new)/(1-a_old).
    New ink must cover the old ink at least as opaquely, avoiding amplification of
    existing JPEG error. No clean original is inferred or saved.
    """
    patch = image.crop(bounds).convert('RGB')
    pixels = []
    for pixel, old, new in zip(patch.getdata(), old_overlay.getdata(), new_overlay.getdata()):
        if new[3] < old[3]:
            raise ValueError('New ink does not fully cover the old ink; use an unwatermarked original.')
        if old[3] == 255:
            pixels.append(new[:3])
            continue
        keep = (255 - new[3]) / (255 - old[3])
        pixels.append(tuple(max(0, min(255, round(new[channel] * new[3] / 255 +
                            (value - old[channel] * old[3] / 255) * keep)))
                            for channel, value in enumerate(pixel)))
    patch.putdata(pixels)
    result = image.copy()
    result.paste(patch.convert(image.mode), bounds)
    return result


def migration_overlays(image, font_path, previous):
    new, bounds = outlined_overlay(image, font_path)
    old, old_bounds = legacy_overlay(image, font_path, previous.get('color', LEGACY_STYLE['color']))
    if previous['dimensions'] != list(image.size) or previous['bounds'] != old_bounds:
        raise ValueError('Old watermark font or geometry does not match.')
    if not (bounds[0] <= old_bounds[0] and bounds[1] <= old_bounds[1]
            and bounds[2] >= old_bounds[2] and bounds[3] >= old_bounds[3]):
        raise ValueError('New watermark bounds do not cover the old watermark.')
    aligned_old = Image.new('RGBA', new.size)
    aligned_old.paste(old, (old_bounds[0] - bounds[0], old_bounds[1] - bounds[1]))
    if any(new_a < old_a for old_a, new_a in zip(aligned_old.getchannel('A').getdata(), new.getchannel('A').getdata())):
        raise ValueError('New watermark does not cover the old ink; use an unwatermarked original.')
    return aligned_old, new, bounds


def watermark_file(source, font_path, previous=None):
    if previous and digest(source) != previous['sha256']:
        raise RuntimeError(f'Photo changed since validation: {source}')
    original_stat = source.stat()
    with Image.open(source) as original:
        if original.format != 'JPEG' or original.mode not in ('RGB', 'L'):
            raise ValueError(f'Please first convert to a standard JPEG: {source}')
        if original.getexif().get(274, 1) != 1:
            raise ValueError(f'Normalize photo orientation before watermarking: {source}')
        original.load()
        dimensions = original.size
        metadata = original.info.copy()
        if previous:
            old_overlay, new_overlay, bounds = migration_overlays(original, font_path, previous)
            marked = replace_watermark(original, old_overlay, new_overlay, bounds)
        else:
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
    return {'sha256': digest(source), 'dimensions': list(dimensions), 'bounds': bounds,
            'style_version': STYLE['version'], 'color': STYLE['color']}


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
    parser.add_argument('--upgrade-existing', action='store_true',
                        help='Replace version-1/2 ink with outlined white text, without adding a second layer')
    parser.add_argument('--dry-run', action='store_true', help='Validate and preview choices without writing photos')
    args = parser.parse_args()
    folder = args.folder.expanduser().resolve()
    if not folder.is_dir() or folder.name == 'thumbs':
        parser.error('Specify an album directory or assets/photos, not thumbs.')
    if not args.font or not args.font.is_file():
        parser.error('No font found; use --font /path/to/font.ttf.')
    data = json.loads(args.manifest.read_text()) if args.manifest.exists() else {'style': STYLE, 'images': {}}
    if data['style'] not in (LEGACY_STYLE, ADAPTIVE_STYLE, STYLE):
        parser.error('Unsupported style change. Reimport unwatermarked backups first.')
    for entry in data['images'].values():
        entry.setdefault('style_version', data['style']['version'])
    photos = sorted(p for p in folder.rglob('*') if p.is_file()
                    and p.suffix.lower() in ('.jpg', '.jpeg')
                    and 'thumbs' not in p.relative_to(folder).parts)
    # Validate every file before changing any. Edited watermarked files cannot safely be stamped again.
    pending = []
    skipped = 0
    font_hash = digest(args.font)
    for source in photos:
        try:
            key = source.relative_to(ROOT).as_posix()
        except ValueError:
            key = source.as_posix()
        previous = data['images'].get(key)
        if previous:
            if previous['sha256'] != digest(source):
                parser.error(f'Previously watermarked file changed; restore the tracked copy or reimport a clean original: {key}')
            if previous['style_version'] == STYLE['version']:
                skipped += 1
                continue
            if previous['style_version'] not in (1, 2) or not args.upgrade_existing:
                parser.error('Use --upgrade-existing to replace version-1/2 watermarks.')
            if previous.get('font_sha256', font_hash) != font_hash:
                parser.error(f'Use the original watermark font to replace existing ink: {key}')
        with Image.open(source) as image:
            if image.format != 'JPEG' or image.mode not in ('RGB', 'L') or image.getexif().get(274, 1) != 1:
                parser.error(f'Convert to an orientation-normalized JPEG before watermarking: {key}')
            if previous:
                try:
                    migration_overlays(image, args.font, previous)
                except ValueError as error:
                    parser.error(f'{key}: {error}')
        pending.append((source, key, previous))
        print(f'{"Plan" if args.dry_run else "Checked"}: {key} → white fill, dark outline, soft shadow', flush=True)
    if args.dry_run:
        print(f'Would process {len(pending)}; already marked {skipped}. No files changed.')
        return
    data['style'] = STYLE
    made = 0
    for source, key, previous in pending:
        data['images'][key] = {**watermark_file(source, args.font, previous), 'font_sha256': font_hash}
        save_manifest(args.manifest, data)
        made += 1
        print(f'Watermarked: {key}', flush=True)
    print(f'Watermarked {made}; already marked {skipped}. Regenerate thumbs afterwards.')


if __name__ == '__main__':
    main()
