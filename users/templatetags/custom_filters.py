from django import template

register = template.Library()

@register.filter(name='replace_underscore')
def replace_underscore(value):
    """Replace underscores with spaces in a string."""
    return value.replace('_', ' ')
