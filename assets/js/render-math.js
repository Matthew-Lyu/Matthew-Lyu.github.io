(function () {
  'use strict';

  document.querySelectorAll('.prose script[type^="math/tex"]').forEach(function (source) {
    var displayMode = source.type.indexOf('mode=display') !== -1;
    var element = document.createElement(displayMode ? 'div' : 'span');
    element.className = displayMode ? 'math-block' : 'math-inline';
    katex.render(source.textContent, element, {
      displayMode: displayMode,
      throwOnError: false
    });
    source.replaceWith(element);
  });

  // GitHub Pages emits delimiters instead of the legacy math/tex script nodes.
  document.querySelectorAll('.prose').forEach(function (prose) {
    renderMathInElement(prose, {
      delimiters: [
        { left: '$$', right: '$$', display: true },
        { left: '\\[', right: '\\]', display: true },
        { left: '\\(', right: '\\)', display: false }
      ],
      ignoredClasses: ['katex', 'math-block', 'math-inline'],
      throwOnError: false
    });
    prose.querySelectorAll('.katex-display').forEach(function (display) {
      display.parentElement.classList.add('math-block');
    });
  });
}());
