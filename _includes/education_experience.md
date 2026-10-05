<h2>Education &amp; Experience</h2>

<div class="experience-list">
{% for item in site.data.education_experience.main %}
  <div class="experience-item">
    <div class="experience-content">
      <div class="experience-title">{{ item.title }}</div>
      <div class="experience-unit">{{ item.unit }}</div>
      <div class="experience-meta">
        <span>{{ item.period }}</span><span class="experience-separator">|</span>{% if item.institution_url %}<a href="{{ item.institution_url }}">{{ item.institution }}</a>{% else %}<span>{{ item.institution }}</span>{% endif %}
      </div>
      {% if item.advisor %}
      <div class="experience-advisor">Advisor: Prof. <a href="{{ item.advisor.url }}">{{ item.advisor.name }}</a>.</div>
      {% endif %}
    </div>
    <img class="experience-logo" src="{{ item.logo }}" alt="{{ item.institution }} logo">
  </div>
{% endfor %}
</div>
