(() => {
  document.querySelectorAll('.photo-grid').forEach(grid => {
    const items = Array.from(grid.children).filter(item => item.classList.contains('photo-item'));
    if (!items.length) return;

    let lastWidth = 0;
    let frame = 0;
    let forceLayout = false;

    const layout = force => {
      const width = grid.getBoundingClientRect().width;
      if (width <= 0 || (!force && Math.abs(width - lastWidth) < 0.5)) return;
      lastWidth = width;
      const css = getComputedStyle(grid);
      const columns = Math.max(1, parseInt(css.getPropertyValue('--photo-columns'), 10) || 1);
      const gap = parseFloat(css.getPropertyValue('--photo-gap')) || 0;
      const columnWidth = (width - gap * (columns - 1)) / columns;

      grid.classList.add('is-masonry');
      items.forEach(item => {
        item.style.width = `${columnWidth}px`;
        const image = item.querySelector('img');
        // Imported images have dimensions, so their space is known before loading.
        // For other images, reserve a temporary ratio until their dimensions arrive.
        if (image && !(Number(image.getAttribute('width')) > 0 && Number(image.getAttribute('height')) > 0)) {
          image.style.aspectRatio = image.naturalWidth && image.naturalHeight
            ? `${image.naturalWidth} / ${image.naturalHeight}` : '3 / 2';
        }
      });

      const itemHeights = items.map(item => item.getBoundingClientRect().height);
      const columnHeights = Array(columns).fill(0);
      const positions = itemHeights.map(height => {
        let column = 0;
        for (let i = 1; i < columns; i += 1) {
          if (columnHeights[i] < columnHeights[column]) column = i;
        }
        const position = { x: column * (columnWidth + gap), y: columnHeights[column] };
        columnHeights[column] += height + gap;
        return position;
      });
      items.forEach((item, index) => {
        item.style.transform = `translate(${positions[index].x}px, ${positions[index].y}px)`;
      });
      grid.style.height = `${Math.max(0, ...columnHeights) - gap}px`;
    };

    const schedule = (force = false) => {
      forceLayout = forceLayout || force;
      if (frame) return;
      frame = requestAnimationFrame(() => {
        frame = 0;
        const force = forceLayout;
        forceLayout = false;
        layout(force);
      });
    };

    items.forEach(item => {
      const image = item.querySelector('img');
      if (image) {
        image.addEventListener('load', () => schedule(true));
        image.addEventListener('error', () => schedule(true));
      }
    });
    if (typeof ResizeObserver === 'function') {
      new ResizeObserver(() => schedule()).observe(grid);
    }
    window.addEventListener('resize', () => schedule(true), { passive: true });
    if (document.fonts) document.fonts.ready.then(() => schedule(true));
    layout(true);
  });
})();
