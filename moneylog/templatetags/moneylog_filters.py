from django import template

register = template.Library()


@register.filter
def itatformat(value, decimal_places=2):
    """
    Format a number using Italian conventions:
      - '.' as thousands separator
      - ',' as decimal separator
    Example: 1234567.89 → '1.234.567,89'
    """
    try:
        value = float(value)
    except (TypeError, ValueError):
        return value

    decimal_places = int(decimal_places)
    formatted = f"{value:,.{decimal_places}f}"   # e.g. '1,234,567.89'
    # Swap separators: , → X, . → ,, X → .
    formatted = formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
    return formatted
