#!/usr/bin/env python3
"""Burn an adaptive @mattlyu watermark into JPEGs, preserving photo metadata."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
LEGACY_STYLE = {'version': 1, 'text': '@mattlyu', 'color': '#b8b8b8', 'opacity': 210,
                'font_ratio': 0.024, 'margin_ratio': 0.02, 'quality': 95}
STYLE = {**LEGACY_STYLE, 'version': 2, 'color_mode': 'adaptive',
         'dark_color': '#202020', 'luminance_threshold': 128}


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


def watermark_overlay(image, font_path, color):
    """Render only the watermark rectangle, keeping the legacy glyph geometry."""
    short_edge = min(image.size)
    font_size = max(12, round(short_edge * STYLE['font_ratio']))
    margin = max(8, round(short_edge * STYLE['margin_ratio']))
    font = ImageFont.truetype(str(font_path), font_size)
    stroke = max(1, round(font_size * 0.02))
    left, top, right, bottom = font.getbbox(STYLE['text'], stroke_width=stroke)
    x, y = margin - left, image.height - margin - bottom
    bounds = [margin, y + top, x + right, image.height - margin]
    overlay = Image.new('RGBA', (right - left, bottom - top))
    draw = ImageDraw.Draw(overlay)
    gray = int(color[1:3], 16)
    draw.text((-left, -top), STYLE['text'], font=font, fill=(gray, gray, gray, STYLE['opacity']),
              stroke_width=stroke, stroke_fill=(30, 30, 30, 85))
    return overlay, bounds


def adaptive_color(image, overlay, bounds):
    """Sample the local background, excluding the existing or future ink pixels."""
    background = image.crop(bounds).convert('L')
    clear = overlay.getchannel('A').point(lambda alpha: 0 if alpha else 255)
    histogram = background.histogram(mask=clear)
    total = sum(histogram)
    if not total:
        histogram = background.histogram()
        total = sum(histogram)
    cumulative = 0
    for median, count in enumerate(histogram):
        cumulative += count
        if cumulative >= total / 2:
            break
    color = STYLE['dark_color'] if median >= STYLE['luminance_threshold'] else STYLE['color']
    return color, median


def draw_watermark(image, font_path):
    """Composite one watermark, choosing ink from the background under its text."""
    overlay, bounds = watermark_overlay(image, font_path, STYLE['color'])
    color, _ = adaptive_color(image, overlay, bounds)
    if color != STYLE['color']:
        overlay, _ = watermark_overlay(image, font_path, color)
    result = image.copy()
    patch = Image.alpha_composite(image.crop(bounds).convert('RGBA'), overlay).convert(image.mode)
    result.paste(patch, bounds)
    return result, bounds


def recolor_watermark(image, old_overlay, new_overlay, bounds):
    """Replace old ink, rather than alpha-compositing another text layer.

    With equal alpha, new_pixel = old_pixel + alpha * (new_ink - old_ink).
    This keeps the existing background contribution, including anti-aliased edges.
    JPEG rounding in the already published image cannot be reversed exactly.
    """
    if old_overlay.getchannel('A').tobytes() != new_overlay.getchannel('A').tobytes():
        raise ValueError('Changing watermark opacity requires unwatermarked originals.')
    patch = image.crop(bounds).convert('RGB')
    pixels = []
    for pixel, old, new in zip(patch.getdata(), old_overlay.getdata(), new_overlay.getdata()):
        pixels.append(tuple(max(0, min(255, round(value + old[3] * (new[channel] - old[channel]) / 255)))
                            for channel, value in enumerate(pixel)))
    patch.putdata(pixels)
    result = image.copy()
    result.paste(patch.convert(image.mode), bounds)
    return result


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
        old_overlay, bounds = watermark_overlay(original, font_path, STYLE['color'])
        color, brightness = adaptive_color(original, old_overlay, bounds)
        if previous:
            if previous['dimensions'] != list(dimensions) or previous['bounds'] != bounds:
                raise ValueError(f'Watermark geometry does not match the original font: {source}')
            if color == STYLE['color']:
                # Dark backgrounds already have the correct gray ink. No JPEG re-encoding.
                return {**previous, 'style_version': STYLE['version'], 'color': color,
                        'background_luminance': brightness}
            new_overlay, _ = watermark_overlay(original, font_path, color)
            marked = recolor_watermark(original, old_overlay, new_overlay, bounds)
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
            'style_version': STYLE['version'], 'color': color, 'background_luminance': brightness}


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
                        help='Replace version-1 gray ink with adaptive ink, without adding a second layer')
    parser.add_argument('--dry-run', action='store_true', help='Validate and preview choices without writing photos')
    args = parser.parse_args()
    folder = args.folder.expanduser().resolve()
    if not folder.is_dir() or folder.name == 'thumbs':
        parser.error('Specify an album directory or assets/photos, not thumbs.')
    if not args.font or not args.font.is_file():
        parser.error('No font found; use --font /path/to/font.ttf.')
    data = json.loads(args.manifest.read_text()) if args.manifest.exists() else {'style': STYLE, 'images': {}}
    if data['style'] not in (LEGACY_STYLE, STYLE):
        parser.error('Unsupported style change. Reimport unwatermarked backups first.')
    for entry in data['images'].values():
        entry.setdefault('style_version', data['style']['version'])
    photos = sorted(p for p in folder.rglob('*') if p.is_file()
                    and p.suffix.lower() in ('.jpg', '.jpeg')
                    and 'thumbs' not in p.relative_to(folder).parts)
    # Validate every file before changing any. Edited watermarked files cannot safely be stamped again.
    pending = []
    skipped = 0
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
            if previous['style_version'] != 1 or not args.upgrade_existing:
                parser.error('Use --upgrade-existing to convert version-1 gray watermarks.')
        with Image.open(source) as image:
            if image.format != 'JPEG' or image.mode not in ('RGB', 'L') or image.getexif().get(274, 1) != 1:
                parser.error(f'Convert to an orientation-normalized JPEG before watermarking: {key}')
            overlay, bounds = watermark_overlay(image, args.font, STYLE['color'])
            if previous and (previous['bounds'] != bounds or previous['dimensions'] != list(image.size)):
                parser.error(f'Old font or geometry does not match: {key}')
            color, brightness = adaptive_color(image, overlay, bounds)
        pending.append((source, key, previous))
        print(f'{"Plan" if args.dry_run else "Checked"}: {key} → {color} (background {brightness}/255)', flush=True)
    if args.dry_run:
        print(f'Would process {len(pending)}; already marked {skipped}. No files changed.')
        return
    data['style'] = STYLE
    made = 0
    font_hash = digest(args.font)
    for source, key, previous in pending:
        data['images'][key] = {**watermark_file(source, args.font, previous), 'font_sha256': font_hash}
        save_manifest(args.manifest, data)
        made += 1
        print(f'Watermarked: {key}', flush=True)
    print(f'Watermarked {made}; already marked {skipped}. Regenerate thumbs afterwards.')


if __name__ == '__main__':
    main()
