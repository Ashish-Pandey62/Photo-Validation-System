# custom_filters.py

from django import template
import os

register = template.Library()

@register.filter
def get_image_name(image_path):
    return os.path.basename(image_path)


@register.filter
def getattr_safe(obj, attr_name):
    """Safely get attribute of a model. Returns False if attribute doesn't exist."""
    return getattr(obj, attr_name, False)


@register.filter
def get(d, key):
    """Get value from dictionary by key"""
    return d.get(key)