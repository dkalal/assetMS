from django import template
register = template.Library()
 
@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, '')

@register.filter
def startswith(text, starts):
    if isinstance(text, str):
        return text.startswith(starts)
    return False

@register.filter
def field_by_name(form, name):
    return form[name] 