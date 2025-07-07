import os.path
from .models import Config
from PIL import Image


def check_image(path):
    size = os.path.getsize(path) / 1000.00#TO KILOBYTES

    tolerance = 10.00

    # Safely get config object
    try:
        config = Config.objects.first()
        if not config:
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

def check_height(path):
    try:
        im = Image.open(path)
        width, height = im.size

        tolerance = 10.00

        config = Config.objects.first()
        if not config:
            # Use default values if no config
            min_height = 100 - tolerance
            max_height = 2000 + tolerance
        else:
            min_height = config.min_height - tolerance
            max_height = config.max_height + tolerance

        # Check if the height of the image is ok
        if min_height <= height <= max_height:
            return True
        return False
    except Exception as e:
        print(f"Error in check_height: {e}")
        return False

def check_width(path):
    try:
        im = Image.open(path)
        width, height = im.size

        tolerance = 10.00

        config = Config.objects.first()
        if not config:
            # Use default values if no config
            min_width = 100 - tolerance
            max_width = 2000 + tolerance
        else:
            min_width = config.min_width - tolerance
            max_width = config.max_width + tolerance

        # Check if the width of the image is ok
        if min_width <= width <= max_width:
            return True
        return False
    except Exception as e:
        print(f"Error in check_width: {e}")
        return False



