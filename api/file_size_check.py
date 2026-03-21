import os.path
import logging
from PIL import Image
from .config_utils import get_cached_config


def check_image(path, config=None):
    size = os.path.getsize(path) / 1000.00#TO KILOBYTES

    tolerance = 10.00

    try:
        if not config:
            config = get_cached_config()
    except Exception:
        # Use default values if config fails
        min_size = 10 - tolerance
        max_size = 5000 + tolerance
        if min_size <= size <= max_size:
            return True
        return False
        
    min_size = config.min_size - tolerance
    max_size = config.max_size + tolerance

    # Check if the size of the file is greater than 1MB or not
    if min_size <= size <= max_size:
        return True
    return False

def check_height(path, config=None):
    try:
        im = Image.open(path)
        width, height = im.size

        tolerance = 10.00

        if not config:
            config = get_cached_config()
        min_height = getattr(config, "min_height", 100) - tolerance
        max_height = getattr(config, "max_height", 2000) + tolerance

        # Check if the height of the image is ok
        if min_height <= height <= max_height:
            return True
        return False
    except Exception as e:
        logging.debug(f"Error in check_height: {e}")
        return False

def check_width(path, config=None):
    try:
        im = Image.open(path)
        width, height = im.size

        tolerance = 10.00

        if not config:
            config = get_cached_config()
        min_width = getattr(config, "min_width", 100) - tolerance
        max_width = getattr(config, "max_width", 2000) + tolerance

        # Check if the width of the image is ok
        if min_width <= width <= max_width:
            return True
        return False
    except Exception as e:
        logging.debug(f"Error in check_width: {e}")
        return False



