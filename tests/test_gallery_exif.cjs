const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../assets/js/gallery.js'), 'utf8');

function openPhoto(built, manual = false) {
  const fields = ['camera', 'lens', 'focal_length', 'aperture', 'shutter', 'iso'].map(key => {
    const value = { textContent: '' };
    return { dataset: { exifField: key }, hidden: true, value, querySelector: () => value };
  });
  const elements = {};
  for (const name of ['image', 'counter', 'previous', 'next', 'close']) {
    elements[`.lightbox-${name}`] = { addEventListener() {} };
  }
  elements['.exif-settings'] = { children: fields.slice(2) };
  const exif = { hidden: true, querySelectorAll: () => fields,
    querySelector: selector => elements[selector] };
  elements['.lightbox-exif'] = exif;
  const dialog = { open: false, addEventListener() {},
    showModal() { this.open = true; }, querySelector: selector => elements[selector] };
  const preview = { alt: 'Photo', dataset: built === undefined ? {} : { photoExif: built } };
  let click;
  const link = { href: '/large-original.jpg', dataset: {
    exifManual: String(manual), exif: '{"camera":"Manual camera"}' },
    querySelector: () => preview, addEventListener: (event, callback) => { click = callback; } };
  let reads = 0;
  const window = { PhotoExif: { read: async () => { reads += 1; return {}; } } };
  const document = { querySelectorAll: () => [link], querySelector: () => dialog,
    body: { classList: { add() {} } } };
  vm.runInNewContext(source, { window, document });
  click({ preventDefault() {} });
  return { fields, exif, image: elements['.lightbox-image'], reads: () => reads };
}

(async () => {
  const built = openPhoto('{"camera":"NIKON Z6_3","iso":"ISO 100"}');
  assert.equal(built.fields[0].value.textContent, 'NIKON Z6_3');
  assert.equal(built.exif.hidden, false, 'EXIF must appear before the image load event');
  built.image.onload();
  assert.equal(built.reads(), 0, 'Build metadata must not download the original for parsing');
  const empty = openPhoto('{}');
  empty.image.onload();
  assert.equal(empty.exif.hidden, true);
  assert.equal(empty.reads(), 0, 'Known missing EXIF must not trigger a fallback download');
  const manual = openPhoto('{"camera":"Built camera"}', true);
  assert.equal(manual.fields[0].value.textContent, 'Manual camera');
  manual.image.onload();
  assert.equal(manual.reads(), 0);
  const legacy = openPhoto(undefined);
  legacy.image.onload();
  assert.equal(legacy.reads(), 1, 'Older pages retain the runtime EXIF fallback');
  console.log('Immediate EXIF display, empty/manual metadata and legacy fallback passed.');
})().catch(error => { console.error(error); process.exitCode = 1; });
