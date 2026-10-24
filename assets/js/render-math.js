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
}());
