from PIL import Image
from .models import Config


def check_image(path):
    try:
        # Safely get config object
        config = Config.objects.first()
        if not config:
            # If no config exists, create default one
            config = Config.objects.create(
                min_height=100,
                max_height=2000,
                min_width=100,
                max_width=2000,
                min_size=10,
                max_size=5000,
                is_jpg=True,
                is_png=True,
                is_jpeg=True
            )
        
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
