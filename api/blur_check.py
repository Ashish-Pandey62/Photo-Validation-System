import cv2
import numpy as np


def check_image_blurness(image, config=None):
    """
    Check if an image is blurry using Laplacian variance.

    Returns (is_blurry: bool, details: dict).
    The pixelation check has been removed — the old approach measured edge
    density (gradient magnitude), which incorrectly flagged sharp, detailed
    images as "pixelated."
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # --- threshold from config or sensible default ---
    if config is not None:
        threshold = getattr(config, "blurness_threshold", 100)
    else:
        threshold = 100

    # Laplacian variance — higher = sharper
    lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    # NOTE: The old code multiplied lap_var by (mean_brightness / 30) for
    # dark photos.  That *reduced* the score for dark-but-sharp images,
    # causing them to be wrongly rejected.  Removed.

    is_blur = lap_var < threshold

    return is_blur, {
        "blur_value": lap_var,
        "blur_threshold": threshold,
        "is_blur": is_blur,
    }
