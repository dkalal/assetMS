from django import template

register = template.Library()


@register.filter(name='replace')
def replace(value, args):
    """Replace occurrences: usage in template: {{ value|replace:"old: new" }}

    To keep compatibility with existing code that expects two arguments separated by 
    a colon in the filter string, accept "old:replacement" or "old":"replacement".
    """
    if value is None:
        return ''
    try:
        # args may be provided as 'old:replacement' or 'old','replacement' depending on render
        if isinstance(args, str) and ':' in args:
            old, new = args.split(':', 1)
        else:
            # fallback: if args is a tuple/list
            old, new = args
        return str(value).replace(old, new)
    except Exception:
        return value
