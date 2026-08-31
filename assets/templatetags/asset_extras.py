from django import template
import json

register = template.Library()


@register.simple_tag(takes_context=True)
def query_replace(context, **changes):
    '''Return the current query string with selected keys replaced or removed.'''
    query = context['request'].GET.copy()
    for key, value in changes.items():
        if value is None or value == '':
            query.pop(key, None)
        else:
            query[key] = value
    return query.urlencode()
 
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

@register.filter
def to_json(value):
    """
    Convert Python dict/list to JSON string for use in JavaScript.
    
    Usage:
        {{ object.dynamic_data|to_json }}
    
    This ensures proper JSON formatting when passing data to JavaScript,
    avoiding issues with Python dict representation (single quotes, None, etc.)
    """
    if value is None:
        return 'null'
    
    try:
        return json.dumps(value, ensure_ascii=False, separators=(',', ':'))
    except (TypeError, ValueError) as e:
        # Fallback for non-serializable data
        return '{}'
