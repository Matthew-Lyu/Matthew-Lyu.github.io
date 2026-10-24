const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const source = fs.readFileSync(path.join(__dirname, '../assets/js/photo-exif.js'), 'utf8');
let calls = 0;
const window = { exifr: { parse: async url => {
  calls += 1;
  if (url === 'broken.jpg') throw new Error('unreadable image');
  return { Model: 'NIKON Z6_3', LensModel: 'NIKKOR Z 24-120mm f/4 S',
    FocalLength: 54, FNumber: 22, ExposureTime: 25, ISO: 50 };
} } };
vm.runInNewContext(source, { window });
const plain = object => JSON.parse(JSON.stringify(object));

(async () => {
  assert.deepEqual(plain(window.PhotoExif.format({})), {});
  assert.deepEqual(plain(window.PhotoExif.format({ ExposureTime: .01 })), { shutter: '1/100 s' });
  assert.deepEqual(plain(window.PhotoExif.format({ ExposureTime: .6 })), { shutter: '0.6 s' });
  assert.deepEqual(plain(window.PhotoExif.format({ Model: ' Canon EOS 60D\0 ', ISO: 0, FNumber: NaN })),
    { camera: 'Canon EOS 60D' });
  const first = window.PhotoExif.read('renamed.JPG');
  assert.equal(first, window.PhotoExif.read('renamed.JPG'));
  assert.deepEqual(plain(await first), { camera: 'NIKON Z6_3', lens: 'NIKKOR Z 24-120mm f/4 S',
    focal_length: '54 mm', aperture: 'f/22', shutter: '25 s', iso: 'ISO 50' });
  assert.equal(calls, 1);
  assert.deepEqual(plain(await window.PhotoExif.read('broken.jpg')), {});
  delete window.exifr;
  assert.deepEqual(plain(await window.PhotoExif.read('offline.jpg')), {});
  console.log('EXIF formatting, request caching and missing-metadata/error handling passed.');
})().catch(error => { console.error(error); process.exitCode = 1; });
