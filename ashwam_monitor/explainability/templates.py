from jinja2 import Template


PM_TEMPLATE = Template("""## System Health - {{ timestamp }}

**Status**: {{ status }}

### Key Metrics
| Metric | Value | Status |
|--------|-------|--------|
{% for m in metrics %}| {{ m.name }} | {{ m.value }} | {{ m.status }} |
{% endfor %}

### Alerts
{% for a in alerts %}
- {{ a }}
{% endfor %}

### Actions
{% for action in actions %}
{{ loop.index }}. {{ action }}
{% endfor %}
""")


CLINICIAN_TEMPLATE = Template("""## Extraction Review - {{ journal_id }}

### Decision
- **Extracted**: "{{ evidence_span }}"
- **Domain**: {{ domain }}
- **Polarity**: {{ polarity }}
- **Confidence**: {{ confidence }}%

### Evidence
> {{ context }}

{% if conflict %}
### Conflict Detected
{{ conflict }}
{% endif %}

### Limitations
{% for lim in limitations %}
- {{ lim }}
{% endfor %}
""")


USER_TEMPLATE = Template("""### What We Noticed

{{ summary }}

{% if items %}
{% for item in items %}
- {{ item }}
{% endfor %}
{% endif %}

{% if needs_confirmation %}
**Does this look right?** You can edit your journal anytime.
{% endif %}
""")
