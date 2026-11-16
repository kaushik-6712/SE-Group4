from django import forms
from django import template

register = template.Library()

SWATCHES = {
    "black": "#1f1f1f",
    "white": "#f7f7f5",
    "cream": "#efe5cf",
    "navy": "#1f2f4f",
    "navy plaid": "#33415e",
    "navy stripe": "#2a3654",
    "indigo": "#2e3a6e",
    "mid blue": "#4b6a95",
    "light blue": "#a9c6e4",
    "powder blue": "#9fb6d9",
    "grey": "#8b8b8b",
    "charcoal": "#3f3f3f",
    "sand": "#d8c49c",
    "khaki": "#c2a878",
    "camel": "#b98a52",
    "champagne": "#b5a27d",
    "olive": "#5f6b3a",
    "sage": "#a3b4a8",
    "brown": "#5e4330",
    "red": "#b33a3a",
    "tomato": "#e0502b",
    "burgundy": "#6e1f2e",
    "rust": "#a4532b",
}


@register.filter
def swatch(color):
    """Map a color name to a hex value for the small color dots."""
    return SWATCHES.get(str(color).lower(), "#cccccc")


@register.filter
def bs(field):
    """Render a form field with Bootstrap classes (and is-invalid when it has errors)."""
    widget = field.field.widget
    if isinstance(widget, forms.Select):
        css = "form-select"
    elif isinstance(widget, (forms.CheckboxInput, forms.RadioSelect)):
        css = "form-check-input"
    else:
        css = "form-control"
    if field.errors:
        css += " is-invalid"
    return field.as_widget(attrs={"class": css})


@register.simple_tag(takes_context=True)
def page_url(context, page):
    """Build a pagination link that keeps the current search and filters."""
    params = context["request"].GET.copy()
    params["page"] = page
    return "?" + params.urlencode()
