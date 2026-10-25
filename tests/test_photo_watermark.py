import hashlib
import importlib.util
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
