# custom_filters.py

from django import template
import os

register = template.Library()

@register.filter
def get_image_name(image_path):
    return os.path.basename(image_path)
