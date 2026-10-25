"""Build isolated fixture albums with the project's installed Jekyll."""

import json
import os
from html.parser import HTMLParser
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.photos, self.images, self.text, self.cards = [], [], [], []
        self.feed(path.read_text())

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and 'data-photo' in attrs:
            self.photos.append(attrs)
        if tag == 'a' and 'album-card' in attrs.get('class', '').split():
            self.cards.append(attrs)
        if tag == 'img':
            self.images.append(attrs)

    def handle_data(self, text):
        self.text.append(text.strip())


class FolderAlbums(unittest.TestCase):
    def test_folder_and_legacy_albums(self):
        with tempfile.TemporaryDirectory(prefix='album-folders-') as directory:
            source = Path(directory).resolve()
            for name in ('_includes', '_layouts'):
                shutil.copytree(ROOT / name, source / name)
            (source / 'photography').mkdir()
            shutil.copy(ROOT / 'photography/index.html', source / 'photography/index.html')
            (source / '_config.yml').write_text('''
title: Album tests
favicon: /favicon.png
include:
  - _albums
defaults:
  - scope:
      path: '_albums'
    values:
      layout: album
      permalink: /photography/:basename/
''')
            albums = source / '_albums'
            albums.mkdir()
            folder = source / 'assets/photos/test album'
            (folder / 'thumbs').mkdir(parents=True)
            (folder / 'nested').mkdir()
            names = ['02.PNG', '01.jpg', '03.jpeg', '04.webp', '05.avif', '06.gif', '中文 照片.jpg']
            for name in names + ['notes.txt', 'raw.NEF']:
                (folder / name).write_bytes(b'fixture')
            (folder / 'thumbs/01.jpg').write_bytes(b'fixture')
            (folder / 'nested/99.jpg').write_bytes(b'fixture')
            (source / '_data').mkdir()
            (source / '_data/photo_exif.json').write_text(json.dumps({
                '/assets/photos/test%20album/01.jpg': {'camera': 'Test camera'}
            }))
            for name, settings in {
                'folder': 'photos: /assets/photos/test album/',
                'no-slashes': 'photos: assets/photos/test album',
                'empty': 'photos: /assets/photos/missing/',
                'explicit-cover': 'cover: /assets/photos/test%20album/02.PNG',
                'separate-descriptions': '''cover_description: Short cover sentence.
description: |
  Detailed album introduction.

  第二段详细介绍。''',
                'cover-only': 'cover_description: Cover text without a detailed introduction.',
                'detail-only': 'description: Detailed introduction without cover text.',
                'legacy': '''photos:
  - src: /assets/photos/test%20album/02.PNG
  - src: /assets/photos/test%20album/01.jpg
    thumb: /assets/photos/test%20album/thumbs/01.jpg
    alt: Custom description
    exif:
      camera: Override camera''',
            }.items():
                (albums / (name + '.md')).write_text(
                    '---\ntitle: ' + name + '\ndate: 2024-06-25\n' + settings + '\n---\n'
                )
            for name, date in {
                'month-old': '2025-07',
                'month-new': '2026-08',
                'full-before': '2026-07-31',
                'full-after': '2026-08-15',
                'same-month-first': '2026-08-01',
                'undated': None,
                'unpublished': '2026-10',
                'pinned-month': '2020-01',
            }.items():
                settings = '---\ntitle: ' + name + '\n'
                if date:
                    settings += 'date: ' + date + '\n'
                if name == 'unpublished':
                    settings += 'published: false\n'
                if name == 'pinned-month':
                    settings += 'pinned: true\npin_order: 1\nlast_modified_at: 2026-10\n'
                (albums / (name + '.md')).write_text(settings + '---\n')
            command = ['ruby', '-I', str(ROOT / 'vendor/tools/gems/bundler-2.4.22/lib'),
                       str(ROOT / 'vendor/tools/gems/bundler-2.4.22/exe/bundle'),
                       'exec', 'jekyll', 'build', '--config', str(source / '_config.yml'), '--source', str(source),
                       '--destination', str(source / '_site')]
            env = dict(os.environ, BUNDLE_GEMFILE=str(ROOT / 'Gemfile'))
            result = subprocess.run(command, cwd=source, env=env, check=True, capture_output=True, text=True)
            pages = {name: Page(source / '_site/photography' / name / 'index.html')
                     for name in ('folder', 'no-slashes', 'empty', 'legacy')}
            ordered = [item['href'] for item in pages['folder'].photos]
            self.assertEqual(len(ordered), 7, result.stdout + result.stderr + (source / '_site/photography/folder/index.html').read_text())
            self.assertTrue(ordered[0].endswith('/01.jpg'))
            self.assertTrue(ordered[1].endswith('/02.PNG'))
            self.assertTrue(ordered[-1].endswith('/%E4%B8%AD%E6%96%87%20%E7%85%A7%E7%89%87.jpg'))
            self.assertEqual(ordered, [item['href'] for item in pages['no-slashes'].photos])
            self.assertEqual([image['src'] for image in pages['folder'].images if 'src' in image], ordered)
            self.assertEqual(json.loads(pages['folder'].photos[0]['data-exif'])['camera'], 'Test camera')
            self.assertEqual(pages['folder'].images[0]['alt'], 'folder · 1')
            self.assertIn('7 photos', ' '.join(pages['folder'].text))
            self.assertFalse(pages['empty'].photos)
            self.assertIn('Photographs coming soon.', ' '.join(pages['empty'].text))
            self.assertTrue(pages['legacy'].photos[0]['href'].endswith('/02.PNG'))
            self.assertEqual(pages['legacy'].images[1]['alt'], 'Custom description')
            self.assertEqual(pages['legacy'].images[1]['src'], '/assets/photos/test%20album/01.jpg')
            self.assertEqual(json.loads(pages['legacy'].photos[1]['data-exif'])['camera'], 'Override camera')
            index = Page(source / '_site/photography/index.html')
            index_text = ' '.join(index.text)
            self.assertIn('Short cover sentence.', index_text)
            self.assertIn('Cover text without a detailed introduction.', index_text)
            self.assertNotIn('Detailed album introduction.', index_text)
            self.assertNotIn('Detailed introduction without cover text.', index_text)
            detail = Page(source / '_site/photography/separate-descriptions/index.html')
            self.assertIn('Detailed album introduction.', ' '.join(detail.text))
            self.assertIn('第二段详细介绍。', ' '.join(detail.text))
            self.assertNotIn('Short cover sentence.', ' '.join(detail.text))
            self.assertNotIn('class="album-description"', (source / '_site/photography/cover-only/index.html').read_text())
            detail_only = Page(source / '_site/photography/detail-only/index.html')
            self.assertIn('Detailed introduction without cover text.', ' '.join(detail_only.text))
            covers = [image['src'] for image in index.images]
            self.assertFalse(any('/thumbs/' in cover for cover in covers))
            self.assertEqual(covers.count('/assets/photos/test%20album/02.PNG'), 2, covers)
            self.assertEqual(covers.count('/assets/photos/test%20album/01.jpg'), 2, covers)
            card_urls = [card['href'] for card in index.cards]
            self.assertEqual(card_urls[0], '/photography/pinned-month/')
            self.assertEqual(card_urls[1], '/photography/full-after/')
            self.assertEqual(card_urls[-1], '/photography/undated/')
            self.assertLess(card_urls.index('/photography/month-new/'), card_urls.index('/photography/full-before/'))
            self.assertLess(card_urls.index('/photography/same-month-first/'), card_urls.index('/photography/full-before/'))
            self.assertLess(card_urls.index('/photography/full-before/'), card_urls.index('/photography/month-old/'))
            self.assertNotIn('/photography/unpublished/', card_urls)
            self.assertFalse((source / '_site/photography/unpublished/index.html').exists())
            month_page = (source / '_site/photography/month-new/index.html').read_text()
            day_page = (source / '_site/photography/full-after/index.html').read_text()
            pinned_page = (source / '_site/photography/pinned-month/index.html').read_text()
            self.assertIn('<time datetime="2026-08">2026-08</time>', month_page)
            self.assertIn('>2026-08-15</time>', day_page)
            self.assertIn('<time datetime="2026-10">2026-10</time>', pinned_page)


if __name__ == '__main__':
    unittest.main()
