from PIL import Image
from .config_utils import get_cached_config


def check_image(path, config=None):
    try:
        if not config:
            config = get_cached_config()
        
        img = Image.open(path)
        format = img.format
        print("format = ", format)
        
        # Handle different format variations
        format_upper = format.upper() if format else ""
        
        # Check against configured formats
        is_valid = False
        if format_upper in ["JPG", "JPEG"] and (config.is_jpg or config.is_jpeg):
            is_valid = True
        elif format_upper == "PNG" and config.is_png:
            is_valid = True
            
        print(f"Format check result: {is_valid} for format {format}")
        return is_valid
    except IOError:
        return False


def is_corrupted_image(img):
    try:
        w, h, channel = img.shape
        return False
    except:
        return True
