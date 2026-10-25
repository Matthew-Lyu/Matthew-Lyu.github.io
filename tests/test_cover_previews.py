import hashlib
from html.parser import HTMLParser
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import unquote, urlsplit

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('cover_previews', ROOT / 'scripts/optimize-covers.py')
covers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(covers)


class Images(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.images = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == 'img':
            self.images.append(dict(attrs))


class CoverPreviews(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='cover-previews-')
        self.addCleanup(self.directory.cleanup)
        self.source = Path(self.directory.name).resolve()
        self.destination = self.source / '_site'
        self.original = self.source / 'assets/photos/中文 album/01.jpg'
        self.original.parent.mkdir(parents=True)
        Image.new('RGB', (1800, 1200), '#6d2077').save(self.original, quality=95)
        self.index = self.destination / 'photography/index.html'
        self.index.parent.mkdir(parents=True)

    def write_index(self, baseurl=''):
        url = baseurl + '/assets/photos/%E4%B8%AD%E6%96%87%20album/01.jpg?v=original'
        self.index.write_text(f'''<!DOCTYPE html><h1>摄影作品</h1>
<img class="album-cover" src="{url}" style="object-position: 50% 30%" alt="封面 &amp; 照片">
<a data-photo href="{url}"><img src="{url}"></a>
<img class="album-cover" src="https://example.com/remote.jpg">
''')
        return url

    def test_generated_covers_preserve_originals_and_other_images(self):
        original_url = self.write_index()
        digest = hashlib.sha256(self.original.read_bytes()).hexdigest()
        result = covers.optimize_site(self.source, self.destination)
        self.assertEqual(result, {'covers': 1, 'created': 2})
        images = Images(self.index.read_text()).images
        cover = images[0]
        self.assertEqual(cover['style'], 'object-position: 50% 30%')
        self.assertEqual(cover['alt'], '封面 & 照片')
        self.assertEqual(cover['data-cover-source'], original_url)
        self.assertEqual(cover['fetchpriority'], 'high')
        self.assertIn('480w', cover['srcset'])
        self.assertIn('960w', cover['srcset'])
        self.assertEqual(images[1]['src'], original_url)
        self.assertEqual(images[2]['src'], 'https://example.com/remote.jpg')
        for candidate in cover['srcset'].split(', '):
            url, descriptor = candidate.split()
            path = self.destination / url.lstrip('/')
            with Image.open(path) as image:
                self.assertEqual(image.width, int(descriptor[:-1]))
                self.assertEqual(image.width / image.height, 1.5)
        self.assertEqual(hashlib.sha256(self.original.read_bytes()).hexdigest(), digest)

    def test_cache_reused_after_output_cleaned_and_html_processing_is_idempotent(self):
        self.write_index()
        covers.optimize_site(self.source, self.destination)
        html = self.index.read_text()
        self.assertEqual(covers.optimize_site(self.source, self.destination)['created'], 0)
        self.assertEqual(self.index.read_text(), html)
        shutil.rmtree(self.destination / 'assets/generated')
        self.write_index()
        self.assertEqual(covers.optimize_site(self.source, self.destination)['created'], 0)
        self.assertEqual(self.index.read_text(), html)
        self.assertEqual(len(list((self.destination / 'assets/generated/covers').glob('*.webp'))), 2)

    def test_replacing_an_original_automatically_changes_the_cover_urls(self):
        self.write_index()
        covers.optimize_site(self.source, self.destination)
        before = Images(self.index.read_text()).images[0]['src']
        Image.new('RGB', (1800, 1200), '#123456').save(self.original, quality=95)
        self.assertEqual(covers.optimize_site(self.source, self.destination)['created'], 2)
        self.assertNotEqual(Images(self.index.read_text()).images[0]['src'], before)

    def test_project_baseurl_and_small_rotated_source(self):
        original_url = self.write_index('/project')
        image = Image.new('RGB', (90, 180), '#abcdef')
        exif = image.getexif()
        exif[274] = 6
        image.save(self.original, exif=exif)
        self.assertEqual(covers.optimize_site(self.source, self.destination, '/project')['created'], 1)
        cover = Images(self.index.read_text()).images[0]
        self.assertTrue(cover['src'].startswith('/project/assets/generated/covers/'))
        self.assertEqual(cover['data-cover-source'], original_url)
        path = self.destination / unquote(urlsplit(cover['src']).path).removeprefix('/project/')
        with Image.open(path) as result:
            self.assertEqual(result.size, (180, 90))

    def test_jekyll_hook_generates_previews_during_normal_build(self):
        for name in ('_includes', '_layouts', '_plugins'):
            shutil.copytree(ROOT / name, self.source / name)
        (self.source / 'scripts').mkdir()
        shutil.copy(ROOT / 'scripts/optimize-covers.py', self.source / 'scripts/optimize-covers.py')
        (self.source / '_albums').mkdir()
        (self.source / '_albums/example.md').write_text('''---
title: Example
cover: /assets/photos/中文%20album/01.jpg
photos: /assets/photos/中文 album/
---
''')
        (self.source / 'photography').mkdir(exist_ok=True)
        shutil.copy(ROOT / 'photography/index.html', self.source / 'photography/index.html')
        (self.source / '_config.yml').write_text('''title: Test
include: [_albums]
exclude: [scripts, .cover-cache]
defaults:
  - scope:
      path: _albums
    values:
      layout: album
      permalink: /photography/:basename/
''')
        command = ['ruby', '-I', str(ROOT / 'vendor/tools/gems/bundler-2.4.22/lib'),
                   str(ROOT / 'vendor/tools/gems/bundler-2.4.22/exe/bundle'),
                   'exec', 'jekyll', 'build', '--source', str(self.source),
                   '--destination', str(self.destination)]
        env = dict(os.environ, BUNDLE_GEMFILE=str(ROOT / 'Gemfile'))
        env.pop('SKIP_COVER_PREVIEWS', None)
        result = subprocess.run(command, cwd=self.source, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        cover = Images(self.index.read_text()).images[0]
        self.assertIn('/assets/generated/covers/', cover['src'])
        self.assertTrue((self.destination / cover['src'].lstrip('/')).is_file())
        album = (self.destination / 'photography/example/index.html').read_text()
        self.assertNotIn('/assets/generated/covers/', album)
        self.assertFalse((self.destination / '.cover-cache').exists())
        # The Pages workflow uses its official Jekyll build, then the same Python
        # step separately, including when Jekyll runs with custom hooks disabled.
        expected = cover['src']
        env['SKIP_COVER_PREVIEWS'] = '1'
        result = subprocess.run(command, cwd=self.source, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn('/assets/generated/covers/', Images(self.index.read_text()).images[0]['src'])
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/optimize-covers.py'),
                                 '--source', str(self.source), '--destination', str(self.destination)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(Images(self.index.read_text()).images[0]['src'], expected)


if __name__ == '__main__':
    unittest.main()
