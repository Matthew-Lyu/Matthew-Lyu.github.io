const assert = require('node:assert/strict');
const { test } = require('node:test');
const { justifiedRows } = require('../assets/js/photo-layout.js');

const verify = (ratios, width) => {
  const rows = justifiedRows(ratios, width);
  assert.deepEqual(rows.flatMap(row => row.indices).sort((a, b) => a - b), ratios.map((_, index) => index));
  rows.forEach((row, index) => {
    assert.deepEqual(row.ratios, row.indices.map(index => ratios[index]));
    assert(row.height > 0 && Number.isFinite(row.height));
    const usedWidth = row.boxes
      ? Math.max(...row.boxes.map(box => box.x + box.width))
      : row.ratios.reduce((sum, ratio) => sum + row.height * ratio, 0) + 10 * (row.ratios.length - 1);
    if (row.boxes) {
      row.boxes.forEach((box, position) => {
        assert(Math.abs(box.width / box.height - row.ratios[position]) < 0.001, 'preserve the full composition');
        assert(box.y + box.height <= row.height + 0.001);
        row.boxes.slice(position + 1).forEach(other => {
          const overlapX = Math.min(box.x + box.width, other.x + other.width) - Math.max(box.x, other.x);
          const overlapY = Math.min(box.y + box.height, other.y + other.height) - Math.max(box.y, other.y);
          assert(overlapX < 0.001 || overlapY < 0.001, 'stacked photos must not overlap');
        });
      });
    }
    assert(usedWidth <= width + 0.001);
    if (width > 480 && index < rows.length - 1) {
      assert(Math.abs(usedWidth - width) < 0.001, 'earlier rows must fill the available width');
      assert(row.ratios.length > 1 || row.ratios[0] >= 1.9, 'unpaired ordinary photos belong at the end');
    }
  });
  return rows;
};
test('panoramas occupy their own full-width rows without dropping or duplicating photos', () => {
  const rows = verify([1.5, 2, 2 / 3, 16 / 9, 2.5, 4 / 3], 1200);
  [2, 2.5].forEach(ratio => {
    const row = rows.find(row => row.ratios.includes(ratio));
    assert.deepEqual(row.ratios, [ratio]);
    assert.equal(row.height * ratio, 1200);
  });
});
test('16:9 frames are never reduced to three across', () => {
  verify(Array(8).fill(16 / 9), 1200).forEach(row => assert(row.ratios.length <= 2));
});
test('ordinary photographs share equal-height rows', () => {
  const rows = verify(Array(6).fill(1.5), 1200);
  assert(rows.some(row => row.ratios.length > 1));
});
test('a final portrait stays a reasonable height', () => {
  const rows = verify([2, 2 / 3], 1200);
  assert(rows[1].height < 500);
});
test('4:3 borrows another 4:3 from beyond a panorama', () => {
  const rows = verify([4 / 3, 2, 4 / 3], 1200);
  assert.deepEqual(rows[0].indices, [0, 2]);
  assert.deepEqual(rows[1].indices, [1]);
});
test('16:9 preferentially borrows an ordinary landscape to complete its row', () => {
  const rows = verify([16 / 9, 2, 2 / 3, 4 / 3], 1200);
  assert.deepEqual(rows[0].indices, [0, 3]);
  assert.deepEqual(rows.at(-1).indices, [2]);
});
test('a portrait before panoramas borrows later photos instead of leaving white space', () => {
  const rows = verify([2 / 3, 2, 16 / 9, 2, 1.5, 1.5], 1200);
  assert.equal(rows[0].indices[0], 0);
  assert(rows[0].indices.length > 1);
});
test('an opening portrait is tall with two landscapes stacked to its right', () => {
  const rows = verify([2 / 3, 2, 16 / 9, 2, 1.5, 1.5], 1200);
  const row = rows[0];
  assert.deepEqual(row.indices, [0, 4, 5]);
  const [portrait, upper, lower] = row.boxes;
  assert(portrait.height > 600);
  assert.equal(upper.x, lower.x);
  assert(upper.x > portrait.x + portrait.width);
  assert.equal(upper.y, portrait.y);
  assert(Math.abs(lower.y - upper.height - 10) < 0.001);
  assert(Math.abs(lower.y + lower.height - portrait.height) < 0.001);
});
test('an opening portrait can stack landscapes of different proportions', () => {
  [600, 900, 1200].forEach(width => {
    const row = verify([3 / 4, 2, 16 / 9, 4 / 3], width)[0];
    assert.deepEqual(row.indices, [0, 2, 3]);
    assert(row.boxes[1].height < row.boxes[2].height);
  });
});
test('stacked opening needs two suitable landscapes and is disabled on mobile', () => {
  assert(!verify([2 / 3, 2, 4 / 3], 1200)[0].boxes);
  assert(verify([2 / 3, 1.5, 1.5], 335).every(row => !row.boxes));
});
test('the only unpaired ordinary photo moves after the remaining panoramas', () => {
  const rows = verify([1.5, 2, 2.5], 1200);
  assert.deepEqual(rows.map(row => row.indices), [[1], [2], [0]]);
});
test('mobile shows uncropped single-column photos', () => {
  const rows = verify([2, 1.5, 2 / 3], 335);
  assert(rows.every(row => row.ratios.length === 1));
  assert.deepEqual(rows.flatMap(row => row.indices), [0, 1, 2]);
  rows.forEach(row => assert.equal(row.height * row.ratios[0], 335));
});
test('empty, invalid, and narrow inputs remain safe', () => {
  assert.deepEqual(justifiedRows([], 1200), []);
  assert.deepEqual(justifiedRows([1.5], 0), []);
  assert(justifiedRows([0, NaN], 600).every(row => Number.isFinite(row.height)));
  [481, 600, 768, 1136].forEach(width => verify([2 / 3, 1.5, 16 / 9, 2, 4 / 3, 2 / 3, 1.5], width));
});
