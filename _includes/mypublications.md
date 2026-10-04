<div id="preprints"></div>
<h2 class="preprints-heading">Preprints</h2>
<!-- <p class="author-note"><sup>*</sup> Equal contribution. <sup>†</sup> Corresponding author.</p> -->

<div class="publications">
<ol class="bibliography">

{% for link in site.data.mypublications.main %}

<li>
<div class="pub-row">
  <div class="col-sm-3 abbr" style="position: relative;padding-right: 15px;padding-left: 15px;">
    {% if link.image %}
    <img src="{{ link.image }}" class="teaser img-fluid z-depth-1" style="width: 420px; height: auto;" alt="{{ link.title }} teaser">
    {% if link.conference_short %}
    <abbr class="badge">{{ link.conference_short }}</abbr>
    {% endif %}
    {% endif %}
  </div>
  <div class="col-sm-9" style="position: relative;padding-right: 15px;padding-left: 20px;">
      <div class="title"><a href="{{ link.pdf }}">{{ link.title }}</a></div>
      {% if link.github %}
        <a href="{{ link.github }}/stargazers" target="_blank" rel="noopener">
          <img src="https://img.shields.io/github/stars/{{ link.github | split: 'https://github.com/' | last | split: '/' | first }}/{{ link.github | split: 'https://github.com/' | last | split: '/' | last }}.svg" alt="GitHub stars">
        </a>
      {% endif %}
      <div class="author">{{ link.authors }}</div>
      <div class="periodical"><em>{{ link.conference }}</em></div>
    <div class="links">
      {% if link.pdf %}
      <a href="{{ link.pdf }}" class="btn btn-sm z-depth-0" role="button" target="_blank" rel="noopener" style="font-size:12px;">PDF</a>
      {% endif %}
      {% if link.code %}
      <a href="{{ link.code }}" class="btn btn-sm z-depth-0" role="button" target="_blank" rel="noopener" style="font-size:12px;">Code</a>
      {% endif %}
      {% if link.page %}
      <a href="{{ link.page }}" class="btn btn-sm z-depth-0" role="button" target="_blank" rel="noopener" style="font-size:12px;">Project Page</a>
      {% endif %}
      {% if link.notes %}
      <strong><i style="color:#e74d3c">{{ link.notes }}</i></strong>
      {% endif %}
    </div>
  </div>
</div>
</li>

{% endfor %}

</ol>
</div>
