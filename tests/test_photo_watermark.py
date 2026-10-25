import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image, ImageChops, ImageCms


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('photo_watermarks', ROOT / 'scripts/watermark-photos.py')
watermarks = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(watermarks)


@unittest.skipUnless(watermarks.default_font(), 'A TrueType font is required')
class PhotoWatermarkTests(unittest.TestCase):
    def test_watermark_is_gray_and_confined_to_bottom_left(self):
        image = Image.new('RGB', (1600, 1000), (245, 245, 245))
        marked, bounds = watermarks.draw_watermark(image, watermarks.default_font())
        changed = ImageChops.difference(image, marked).getbbox()
        self.assertIsNotNone(changed)
        self.assertGreaterEqual(changed[0], bounds[0])
        self.assertLessEqual(changed[2], bounds[2])
        self.assertGreater(changed[1], 900)
        self.assertLess(changed[2], 250)
        self.assertTrue(all(r == g == b for r, g, b in marked.crop(changed).getdata()))

    def test_ink_uses_local_background_not_whole_photo(self):
        for background, corner, expected in [(245, 20, '#b8b8b8'), (20, 245, '#202020')]:
            image = Image.new('RGB', (1600, 1000), (background,) * 3)
            overlay, bounds = watermarks.watermark_overlay(image, watermarks.default_font(), '#b8b8b8')
            image.paste((corner,) * 3, bounds)
            color, _ = watermarks.adaptive_color(image, overlay, bounds)
            self.assertEqual(color, expected)

    def test_recolor_replaces_ink_without_double_stamping(self):
        image = Image.new('RGB', (1600, 1000), (225, 235, 245))
        old, bounds = watermarks.watermark_overlay(image, watermarks.default_font(), '#b8b8b8')
        new, _ = watermarks.watermark_overlay(image, watermarks.default_font(), '#202020')
        marked = image.copy()
        marked.paste(Image.alpha_composite(image.crop(bounds).convert('RGBA'), old).convert('RGB'), bounds)
        expected = image.copy()
        expected.paste(Image.alpha_composite(image.crop(bounds).convert('RGBA'), new).convert('RGB'), bounds)
        actual = watermarks.recolor_watermark(marked, old, new, bounds)
        self.assertLessEqual(max(channel[1] for channel in ImageChops.difference(actual, expected).getextrema()), 1)
        # The transparent pixels and the background outside the original ink remain untouched.
        outside = ImageChops.difference(actual, marked)
        outside.paste((0, 0, 0), bounds)
        self.assertIsNone(outside.getbbox())

    def test_legacy_upgrade_and_dry_run_are_safe_and_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory).resolve()
            manifest = folder / 'manifest.json'
            records = {}
            originals = {}
            for name, level in [('bright.jpg', 245), ('dark.jpg', 20)]:
                image = Image.new('RGB', (1600, 1000), (level,) * 3)
                overlay, bounds = watermarks.watermark_overlay(image, watermarks.default_font(), '#b8b8b8')
                image.paste(Image.alpha_composite(image.crop(bounds).convert('RGBA'), overlay).convert('RGB'), bounds)
                source = folder / name
                image.save(source, quality=95)
                originals[name] = source.read_bytes()
                records[source.as_posix()] = {'sha256': watermarks.digest(source), 'dimensions': [1600, 1000], 'bounds': bounds}
            manifest.write_text(json.dumps({'style': watermarks.LEGACY_STYLE, 'images': records}))
            command = [sys.executable, str(ROOT / 'scripts/watermark-photos.py'), str(folder), '--manifest', str(manifest)]
            rejected = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(rejected.returncode, 0)
            dry_run = subprocess.run(command + ['--upgrade-existing', '--dry-run'], check=True, capture_output=True, text=True)
            self.assertIn('No files changed', dry_run.stdout)
            self.assertEqual((folder / 'bright.jpg').read_bytes(), originals['bright.jpg'])
            subprocess.run(command + ['--upgrade-existing'], check=True, capture_output=True, text=True)
            data = json.loads(manifest.read_text())
            self.assertEqual(data['images'][(folder / 'bright.jpg').as_posix()]['color'], '#202020')
            self.assertEqual(data['images'][(folder / 'dark.jpg').as_posix()]['color'], '#b8b8b8')
            self.assertEqual((folder / 'dark.jpg').read_bytes(), originals['dark.jpg'])
            new_bytes = (folder / 'bright.jpg').read_bytes()
            again = subprocess.run(command, check=True, capture_output=True, text=True)
            self.assertIn('already marked 2', again.stdout)
            self.assertEqual((folder / 'bright.jpg').read_bytes(), new_bytes)

    def test_metadata_and_dimensions_survive_and_second_run_is_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            source = folder / 'photo.jpg'
            thumb_folder = folder / 'thumbs'
            thumb_folder.mkdir()
            thumb = thumb_folder / 'photo.jpg'
            image = Image.new('RGB', (1600, 1000), (80, 120, 150))
            exif = Image.Exif()
            exif[272] = 'NIKON Z6_3'
            exif[274] = 1
            icc = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
            xmp = b'<x:xmpmeta xmlns:x="adobe:ns:meta/">test metadata</x:xmpmeta>'
            image.save(source, quality=95, exif=exif, icc_profile=icc, xmp=xmp)
            image.resize((160, 100)).save(thumb)
            original_thumb = thumb.read_bytes()
            with Image.open(source) as original:
                original_exif = original.info['exif']
            command = [sys.executable, str(ROOT / 'scripts/watermark-photos.py'),
                       str(folder), '--manifest', str(folder / 'manifest.json')]
            subprocess.run(command, check=True, capture_output=True, text=True)
            with Image.open(source) as marked:
                self.assertEqual(marked.size, (1600, 1000))
                self.assertEqual(marked.info['exif'], original_exif)
                self.assertEqual(marked.info['icc_profile'], icc)
                self.assertEqual(marked.info['xmp'], xmp)
            first = hashlib.sha256(source.read_bytes()).digest()
            rerun = subprocess.run(command, check=True, capture_output=True, text=True)
            self.assertIn('already marked 1', rerun.stdout)
            self.assertEqual(hashlib.sha256(source.read_bytes()).digest(), first)
            self.assertEqual(thumb.read_bytes(), original_thumb)


if __name__ == '__main__':
    unittest.main()
