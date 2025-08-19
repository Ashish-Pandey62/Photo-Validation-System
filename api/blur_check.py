import cv2
import numpy as np
from .models import Config

def check_image_blurness(image, config=None):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    is_blur_result, blur_value, blur_threshold = check_if_blur(gray, config)
    is_pixelated_result, pixelated_value, pixelated_threshold = check_if_pixalated(gray, config)

    overall_is_bad = is_blur_result or is_pixelated_result

    return overall_is_bad, {
        'blur_value': blur_value,
        'blur_threshold': blur_threshold,
        'pixelated_value': pixelated_value,
        'pixelated_threshold': pixelated_threshold,
        'is_blur': is_blur_result,
        'is_pixelated': is_pixelated_result
    }


def check_if_blur(gray, config=None):
    if config is None:
        threshold = 100  # sensible default
    else:
        threshold = getattr(config, "blurness_threshold", 100)

    lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()

    mean_brightness = np.mean(gray)
    if mean_brightness < 30:  # dark photo compensation
        lap_var *= (mean_brightness / 30)

    is_blur = lap_var < threshold
    is_extreme = lap_var < (threshold * 0.25)

    return (is_blur or is_extreme), float(lap_var), threshold


def check_if_pixalated(gray, config=None):
    if config is None:
        threshold = 120  # sensible default
    else:
        threshold = getattr(config, "pixelated_threshold", 120)

    small = cv2.resize(gray, (128, 128), interpolation=cv2.INTER_LINEAR)

    dx = np.abs(np.diff(small, axis=1)).mean()
    dy = np.abs(np.diff(small, axis=0)).mean()
    blockiness = (dx + dy) / 2

    is_pixelated = blockiness > threshold
    return is_pixelated, float(blockiness), threshold
