(() => {
  const cache = new Map();
  const tags = ['Model', 'LensModel', 'FocalLength', 'FNumber', 'ExposureTime', 'ISO'];
  const positive = value => Number.isFinite(Number(value)) && Number(value) > 0;
  const number = value => Number(Number(value).toPrecision(5)).toString();
  const text = value => typeof value === 'string' ? value.replace(/\0/g, '').trim() : '';

  const format = (raw = {}) => {
    const result = {};
    if (text(raw.Model)) result.camera = text(raw.Model);
    if (text(raw.LensModel)) result.lens = text(raw.LensModel);
    if (positive(raw.FocalLength)) result.focal_length = `${number(raw.FocalLength)} mm`;
    if (positive(raw.FNumber)) result.aperture = `f/${number(raw.FNumber)}`;
    if (positive(raw.ISO)) result.iso = `ISO ${number(raw.ISO)}`;
    if (positive(raw.ExposureTime)) {
      const seconds = Number(raw.ExposureTime);
      const denominator = Math.round(1 / seconds);
      result.shutter = seconds < 1 && denominator > 1 && Math.abs(1 / denominator - seconds) / seconds < .001
        ? `1/${denominator} s` : `${number(seconds)} s`;
    }
    return result;
  };

  const read = url => {
    if (!window.exifr) return Promise.resolve({});
    if (!cache.has(url)) {
      // Reuse the complete image response instead of issuing partial requests
      // to the same URL while it is also used by an <img> element.
      cache.set(url, fetch(url, { cache: 'force-cache' }).then(response => {
        if (!response.ok) throw new Error('Photo could not be loaded');
        return response.arrayBuffer();
      }).then(bytes => window.exifr.parse(bytes, tags))
        .then(raw => format(raw || {})).catch(() => ({})));
    }
    return cache.get(url);
  };

  window.PhotoExif = { read, format };
})();
