(() => {
  let links = Array.from(document.querySelectorAll('[data-photo]'));
  const dialog = document.querySelector('.lightbox');
  if (!links.length || !dialog || typeof dialog.showModal !== 'function') return;
  const image = dialog.querySelector('.lightbox-image');
  const exif = dialog.querySelector('.lightbox-exif');
  const exifFields = Array.from(exif.querySelectorAll('[data-exif-field]'));
  const settings = exif.querySelector('.exif-settings');
  const counter = dialog.querySelector('.lightbox-counter');
  const previous = dialog.querySelector('.lightbox-previous');
  const next = dialog.querySelector('.lightbox-next');
  let index = 0;
  let opener;
  let touchStart;
  let requestId = 0;

  const renderExif = metadata => {
    if (!metadata || typeof metadata !== 'object' || Array.isArray(metadata)) metadata = {};
    let populated = 0;
    exifFields.forEach(field => {
      const key = field.dataset.exifField;
      const value = metadata[key] == null ? '' : String(metadata[key]).trim();
      field.hidden = !value;
      field.querySelector('[data-exif-value]').textContent = value;
      if (value) populated += 1;
    });
    settings.hidden = !Array.from(settings.children).some(field => !field.hidden);
    exif.hidden = populated === 0;
  };

  const show = requested => {
    const currentRequest = ++requestId;
    index = (requested + links.length) % links.length;
    const link = links[index];
    const preview = link.querySelector('img');
    const manualExif = link.dataset.exifManual === 'true';
    const builtExif = preview.dataset.photoExif;
    image.alt = preview.alt;
    let metadata;
    try {
      metadata = JSON.parse(!manualExif && builtExif !== undefined ? builtExif : link.dataset.exif || '{}');
    } catch {
      metadata = null;
    }
    renderExif(metadata);
    // Normal builds embed EXIF in the page, so it is visible before the original
    // image downloads. Only older/unprocessed pages need the runtime fallback.
    image.onload = () => {
      if (currentRequest !== requestId || !dialog.open || manualExif || builtExif !== undefined || !window.PhotoExif) return;
      window.PhotoExif.read(link.href).then(result => {
        // Ignore a late response after changing photos or closing the viewer.
        if (currentRequest === requestId && dialog.open && Object.keys(result).length) renderExif(result);
      });
    };
    image.src = link.href;
    counter.textContent = `${index + 1} / ${links.length}`;
    previous.hidden = next.hidden = links.length < 2;
  };
  links.forEach(link => link.addEventListener('click', event => {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    opener = link;
    // Follow the displayed order, including photos borrowed to fill earlier rows.
    links = Array.from(document.querySelectorAll('[data-photo]'));
    show(links.indexOf(link));
    dialog.showModal();
    document.body.classList.add('lightbox-open');
  }));
  dialog.querySelector('.lightbox-close').addEventListener('click', () => dialog.close());
  previous.addEventListener('click', () => show(index - 1));
  next.addEventListener('click', () => show(index + 1));
  dialog.addEventListener('keydown', event => {
    if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
      event.preventDefault();
      show(index + (event.key === 'ArrowRight' ? 1 : -1));
    }
  });
  dialog.addEventListener('click', event => {
    if (event.target === dialog) dialog.close();
  });
  dialog.addEventListener('close', () => {
    requestId += 1;
    image.onload = null;
    document.body.classList.remove('lightbox-open');
    image.removeAttribute('src');
    if (opener) opener.focus({ preventScroll: true });
  });
  image.addEventListener('pointerdown', event => {
    touchStart = event.pointerType === 'touch' ? { x: event.clientX, y: event.clientY } : null;
  });
  image.addEventListener('pointerup', event => {
    if (!touchStart) return;
    const dx = event.clientX - touchStart.x;
    const dy = event.clientY - touchStart.y;
    if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy)) show(index + (dx < 0 ? 1 : -1));
    touchStart = null;
  });
  image.addEventListener('pointercancel', () => { touchStart = null; });
})();
