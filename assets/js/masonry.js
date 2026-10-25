(() => {
  document.querySelectorAll('.photo-grid').forEach(grid => {
    const items = Array.from(grid.children).filter(item => item.classList.contains('photo-item'));
    if (!items.length) return;

    let lastWidth = 0;
    let frame = 0;
    let forceLayout = false;
    const controls = document.querySelector('.photo-layout-switch');
    const buttons = controls ? Array.from(controls.querySelectorAll('[data-photo-layout]')) : [];
    let mode = 'masonry';
    try {
      if (localStorage.getItem('photo-layout') === 'justified') mode = 'justified';
    } catch (_) { /* Layout switching also works when browser storage is unavailable. */ }

    const ratioOf = image => {
      if (!image) return 1.5;
      const width = Number(image.dataset.photoWidth) || image.naturalWidth || Number(image.getAttribute('width'));
      const height = Number(image.dataset.photoHeight) || image.naturalHeight || Number(image.getAttribute('height'));
      return width > 0 && height > 0 ? width / height : 1.5;
    };

    const orderItems = ordered => {
      ordered.forEach((item, index) => {
        if (grid.children[index] !== item) grid.insertBefore(item, grid.children[index] || null);
      });
    };

    const layout = force => {
      const width = grid.getBoundingClientRect().width;
      if (width <= 0 || (!force && Math.abs(width - lastWidth) < 0.5)) return;
      lastWidth = width;
      const css = getComputedStyle(grid);
      const columns = Math.max(1, parseInt(css.getPropertyValue('--photo-columns'), 10) || 1);
      const gap = parseFloat(css.getPropertyValue('--photo-gap')) || 0;
      const columnWidth = (width - gap * (columns - 1)) / columns;

      grid.classList.add('is-masonry');
      grid.dataset.layout = mode;
      buttons.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.photoLayout === mode)));
      if (mode === 'justified' && window.PhotoLayout) {
        const rows = window.PhotoLayout.justifiedRows(items.map(item => ratioOf(item.querySelector('img'))), width, gap);
        orderItems(rows.flatMap(row => row.indices.map(index => items[index])));
        let top = 0;
        rows.forEach(row => {
          let left = 0;
          const rowItems = [];
          row.ratios.forEach((ratio, position) => {
            const item = items[row.indices[position]];
            const image = item.querySelector('img');
            const box = row.boxes && row.boxes[position];
            const itemWidth = box ? box.width : row.height * ratio;
            let offsetY = box ? box.y : 0;
            // Explicit captions may add space below the upper landscape.
            if (box && position === 2) offsetY += Math.max(0, rowItems[1].item.getBoundingClientRect().height - row.boxes[1].height);
            item.style.width = `${itemWidth}px`;
            item.style.transform = `translate(${box ? box.x : left}px, ${top + offsetY}px)`;
            if (image) {
              if (image.dataset.photoSource) image.sizes = `${Math.ceil(itemWidth)}px`;
              image.style.aspectRatio = String(ratio);
            }
            rowItems.push({ item, offsetY });
            left += itemWidth + gap;
          });
          top += Math.max(...rowItems.map(({ item, offsetY }) => offsetY + item.getBoundingClientRect().height)) + gap;
        });
        grid.style.height = `${Math.max(0, top - gap)}px`;
        return;
      }
      orderItems(items);
      items.forEach(item => {
        item.style.width = `${columnWidth}px`;
        const image = item.querySelector('img');
        // Imported images have dimensions, so their space is known before loading.
        // For other images, reserve a temporary ratio until their dimensions arrive.
        if (image) {
          if (image.dataset.photoSource) image.sizes = `${Math.ceil(columnWidth)}px`;
          image.style.aspectRatio = String(ratioOf(image));
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

    buttons.forEach(button => button.addEventListener('click', () => {
      mode = button.dataset.photoLayout;
      try { localStorage.setItem('photo-layout', mode); } catch (_) { /* Optional preference. */ }
      schedule(true);
    }));

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
    if (controls) controls.hidden = false;
  });
})();
