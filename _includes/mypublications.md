<h2 id="preprints">Preprints</h2>

<div class="publications">
  <ol class="bibliography">
    {% for link in site.data.mypublications.main %}
    {% assign title_url = link.page | default: link.arxiv | default: link.pdf %}
    <li>
      <div class="publication-card">
        <div class="publication-teaser-wrap">
          <img src="{{ link.image }}" class="publication-teaser" alt="{{ link.title }} teaser">
          {% if link.conference_short %}
          <span class="publication-badge">{{ link.conference_short }}</span>
          {% endif %}
        </div>
        <div class="publication-info">
          <div class="title">
            {% if title_url %}<a href="{{ title_url }}" target="_blank" rel="noopener">{{ link.title }}</a>{% else %}{{ link.title }}{% endif %}
          </div>
          <div class="author">{{ link.authors }}</div>
          <div class="periodical"><em>{{ link.conference }}</em></div>
          <div class="links">
            {% if link.arxiv %}<a href="{{ link.arxiv }}" class="btn" target="_blank" rel="noopener">arXiv</a>{% endif %}
            {% if link.pdf %}<a href="{{ link.pdf }}" class="btn" target="_blank" rel="noopener">PDF</a>{% endif %}
            {% if link.code %}<a href="{{ link.code }}" class="btn" target="_blank" rel="noopener">Code</a>{% endif %}
            {% if link.page %}<a href="{{ link.page }}" class="btn" target="_blank" rel="noopener">Project Page</a>{% endif %}
          </div>
        </div>
      </div>
    </li>
    {% endfor %}
  </ol>
</div>

<small><sup>*</sup> Equal contribution. <sup>†</sup> Corresponding author.</small>
