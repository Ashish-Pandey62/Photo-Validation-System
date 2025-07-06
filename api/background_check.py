import numpy as np
from .models import Config

def background_check(image):
    config = Config.objects.all()[0]
    average_color_threshold = config.bgcolor_threshold

    h, w, channels = image.shape

    pixels_of_r = []
    pixels_of_g = []
    pixels_of_b = []

    for height in range(0, h):
        for width in range(0, w):
            if (height <= 0.35 * h and (width <= 0.14 * w or width >= 0.86 * w)) or height <= 0.015*h:
                r = image[height, width, 0]
                g = image[height, width, 1]
                b = image[height, width, 2]
            
                pixels_of_r.append(r)
                pixels_of_g.append(g)
                pixels_of_b.append(b)

    average_r = np.mean(pixels_of_r)
    average_g = np.mean(pixels_of_g)
    average_b = np.mean(pixels_of_b)

    average_color = (average_r+average_g+average_b)/3

    return average_color>=average_color_threshold
