import numpy as np
from .models import Config

def background_check(image, config=None):
    try:
        if config is None:
            config = Config.objects.first()
        if not config:
            brightness_threshold = 30
            uniformity_threshold = 25
        else:
            brightness_threshold = config.bgcolor_threshold
            uniformity_threshold = getattr(config, "bg_uniformity_threshold", 40)
    except Exception:
        brightness_threshold = 30
        uniformity_threshold = 40

    h, w, _ = image.shape

    # Background candidate regions
    top = image[:int(0.05 * h), :, :]
    bottom = image[int(0.95 * h):, :, :]
    left = image[:int(0.50 * h), :int(0.15 * w), :]
    right = image[:int(0.50 * h), int(0.85 * w):, :]

    background_pixels = np.vstack([
        top.reshape(-1, 3),
        bottom.reshape(-1, 3),
        left.reshape(-1, 3),
        right.reshape(-1, 3)
    ])

    if len(background_pixels) == 0:
        return True

    # Convert to grayscale brightness
    gray = np.mean(background_pixels, axis=1)

    avg_brightness = np.mean(gray)
    std_brightness = np.std(gray)

    # Conditions
    bright_enough = avg_brightness >= brightness_threshold
    not_too_dark = avg_brightness > 20
    uniform_enough = std_brightness < uniformity_threshold  # low variance means plain background

    return bright_enough and not_too_dark and uniform_enough
