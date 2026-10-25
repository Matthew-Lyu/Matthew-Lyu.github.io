const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const source = fs.readFileSync(path.join(__dirname, '../assets/js/photo-exif.js'), 'utf8');
let calls = 0;
let fetches = 0;
const window = { exifr: { parse: async bytes => {
  calls += 1;
  assert.ok(bytes instanceof ArrayBuffer, 'Parse bytes without making partial image requests');
  if (new Uint8Array(bytes)[0] === 0) throw new Error('unreadable image');
  return { Model: 'NIKON Z6_3', LensModel: 'NIKKOR Z 24-120mm f/4 S',
    FocalLength: 54, FNumber: 22, ExposureTime: 25, ISO: 50 };
} } };
const fetch = async (url, options) => {
  fetches += 1;
  assert.equal(options.cache, 'force-cache');
  return { ok: url !== 'missing.jpg', arrayBuffer: async () =>
    new Uint8Array([url === 'broken.jpg' ? 0 : 1]).buffer };
};
vm.runInNewContext(source, { window, fetch });
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
  assert.equal(fetches, 1);
  assert.deepEqual(plain(await window.PhotoExif.read('broken.jpg')), {});
  assert.deepEqual(plain(await window.PhotoExif.read('missing.jpg')), {});
  assert.equal(calls, 2, 'HTTP errors must not reach the EXIF parser');
  delete window.exifr;
  assert.deepEqual(plain(await window.PhotoExif.read('offline.jpg')), {});
  console.log('EXIF formatting, request caching and missing-metadata/error handling passed.');
})().catch(error => { console.error(error); process.exitCode = 1; });
