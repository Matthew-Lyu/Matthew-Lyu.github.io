/* Geometry shared by the album renderer and its layout checks. */
((root, factory) => {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.PhotoLayout = factory();
})(typeof window === 'undefined' ? this : window, () => {
  const justifiedRows = (ratios, width, gap = 10) => {
    if (!ratios.length || width <= 0) return [];
    const pending = ratios.map((ratio, index) => ({
      ratio: Number.isFinite(ratio) && ratio > 0 ? ratio : 1.5, index
    }));
    const makeRow = (photos, height) => ({
      ratios: photos.map(photo => photo.ratio),
      indices: photos.map(photo => photo.index), height
    });
    if (width <= 480) return pending.map(photo => makeRow([photo], width / photo.ratio));
    const target = Math.min(360, Math.max(240, width * 0.3));
    const rows = [];
    if (pending[0].ratio < 1) {
      const landscapes = pending.slice(1).filter(photo => photo.ratio >= 1.2 && photo.ratio < 1.9);
      const regular = landscapes.filter(photo => photo.ratio <= 1.65);
      const companions = (regular.length >= 2 ? regular : landscapes).slice(0, 2);
      if (companions.length === 2) {
        const portrait = pending[0];
        const [upper, lower] = companions;
        // Solve both column widths together so three uncropped images form one
        // rectangle: a tall portrait on the left, two landscapes on the right.
        const inverseSum = 1 / upper.ratio + 1 / lower.ratio;
        const height = (width - gap + gap / inverseSum) / (portrait.ratio + 1 / inverseSum);
        const leftWidth = height * portrait.ratio;
        const rightWidth = width - gap - leftWidth;
        const row = makeRow([portrait, upper, lower], height);
        row.boxes = [
          { x: 0, y: 0, width: leftWidth, height },
          { x: leftWidth + gap, y: 0, width: rightWidth, height: rightWidth / upper.ratio },
          { x: leftWidth + gap, y: rightWidth / upper.ratio + gap, width: rightWidth, height: rightWidth / lower.ratio }
        ];
        rows.push(row);
        const used = new Set(row.indices);
        for (let index = pending.length - 1; index >= 0; index -= 1) {
          if (used.has(pending[index].index)) pending.splice(index, 1);
        }
      }
    }
    while (pending.length) {
      const first = pending[0];
      if (first.ratio >= 1.9) {
        rows.push(makeRow([pending.shift()], width / first.ratio));
        continue;
      }
      const companions = pending.slice(1).filter(photo => photo.ratio < 1.9);
      if (!companions.length) {
        // Only the album's very last row may have an unpaired ordinary photo.
        if (pending.length > 1) {
          pending.push(pending.shift());
          continue;
        }
        rows.push(makeRow([pending.shift()], Math.min(width / first.ratio, target * 1.15)));
        continue;
      }
      // Fill the current row across panorama boundaries. Normal landscape frames
      // preferentially pair with a 4:3 / 3:2 frame further down the album.
      const partner = first.ratio >= 1
        ? companions.find(photo => photo.ratio >= 1.2 && photo.ratio <= 1.65) || companions[0]
        : companions[0];
      const candidates = [[first, partner]];
      if (first.ratio < 1.7) {
        const smaller = companions.filter(photo => photo.ratio < 1.7).slice(0, 2);
        if (smaller.length === 2) candidates.push([first, ...smaller]);
      }
      let best;
      let bestCost = Infinity;
      candidates.forEach(photos => {
        const sum = photos.reduce((total, photo) => total + photo.ratio, 0);
        const height = (width - gap * (photos.length - 1)) / sum;
        const remaining = companions.length + 1 - photos.length;
        const cost = Math.pow((height - target) / target, 2) + (remaining === 1 ? 0.5 : 0);
        if (cost < bestCost) {
          bestCost = cost;
          best = makeRow(photos, height);
        }
      });
      rows.push(best);
      const used = new Set(best.indices);
      for (let index = pending.length - 1; index >= 0; index -= 1) {
        if (used.has(pending[index].index)) pending.splice(index, 1);
      }
    }
    return rows;
  };
  return { justifiedRows };
});
