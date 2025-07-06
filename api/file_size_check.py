import os.path
from .models import Config
from PIL import Image


def check_image(path):
    size = os.path.getsize(path) / 1000.00#TO KILOBYTES

    tolerance = 10.00

    config = Config.objects.all()[0]
    min_size = config.min_size - tolerance
    max_size = config.max_size + tolerance

    # Check if the size of the file is greater than 1MB or not
    if min_size <= size <= max_size:
        return True
    return False

def check_height(path):
    im = Image.open(path)
    width, height = im.size

    tolerance = 10.00

    config = Config.objects.all()[0]
    min_height = config.min_height - tolerance
    max_height = config.max_height + tolerance

    # Check if the height of the image is ok
    if min_height <= height <= max_height:
        return True
    return False

def check_width(path):
    im = Image.open(path)
    width, height = im.size

    tolerance = 10.00

    config = Config.objects.all()[0]
    min_width = config.min_width - tolerance
    max_width = config.max_width + tolerance

    # Check if the width of the image is ok
    if min_width <= width <= max_width:
        return True
    return False



