"""
Custom template tags and filters for admin dashboard
"""
from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Get item from dictionary using key
    Usage: {{ dict|get_item:key }}
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None


@register.filter
def multiply(value, arg):
    """
    Multiply value by argument
    Usage: {{ value|multiply:2 }}
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def percentage(value, total):
    """
    Calculate percentage
    Usage: {{ value|percentage:total }}
    """
    try:
        if float(total) == 0:
            return 0
        return round((float(value) / float(total)) * 100, 2)
    except (ValueError, TypeError):
        return 0


@register.filter
def format_duration(seconds):
    """
    Format duration in seconds to human readable format
    Usage: {{ seconds|format_duration }}
    """
    try:
        seconds = float(seconds)
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"
    except (ValueError, TypeError):
        return "0s"


@register.filter
def format_bytes(bytes_value):
    """
    Format bytes to human readable format
    Usage: {{ bytes|format_bytes }}
    """
    try:
        bytes_value = float(bytes_value)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"
    except (ValueError, TypeError):
        return "0 B"


@register.filter
def replace(value, args):
    """
    Replace substring in value
    Usage: {{ value|replace:"old,new" }}
    """
    try:
        old, new = args.split(',', 1)
        return str(value).replace(old, new)
    except (ValueError, AttributeError):
        return value


@register.simple_tag
def get_model_status_color(status):
    """
    Get color class for model status
    Usage: {% get_model_status_color status %}
    """
    colors = {
        'active': 'success',
        'training': 'warning',
        'testing': 'info',
        'inactive': 'danger',
        'deprecated': 'secondary',
    }
    return colors.get(status, 'secondary')


@register.simple_tag
def get_confidence_color(confidence):
    """
    Get color class for confidence level
    Usage: {% get_confidence_color confidence %}
    """
    try:
        confidence = float(confidence)
        if confidence >= 80:
            return 'success'
        elif confidence >= 60:
            return 'warning'
        else:
            return 'danger'
    except (ValueError, TypeError):
        return 'secondary'


@register.inclusion_tag('admin_dashboard/partials/progress_bar.html')
def progress_bar(value, max_value=100, color='primary', show_percentage=True):
    """
    Render a progress bar
    Usage: {% progress_bar value max_value color show_percentage %}
    """
    try:
        percentage = (float(value) / float(max_value)) * 100
        percentage = min(100, max(0, percentage))
    except (ValueError, TypeError, ZeroDivisionError):
        percentage = 0
    
    return {
        'percentage': percentage,
        'value': value,
        'max_value': max_value,
        'color': color,
        'show_percentage': show_percentage,
    }


@register.inclusion_tag('admin_dashboard/partials/metric_card.html')
def metric_card(title, value, icon, color='primary', change=None, change_type=None):
    """
    Render a metric card
    Usage: {% metric_card "Title" value "fas fa-icon" "primary" change "positive" %}
    """
    return {
        'title': title,
        'value': value,
        'icon': icon,
        'color': color,
        'change': change,
        'change_type': change_type,
    }
