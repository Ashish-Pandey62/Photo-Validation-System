import cv2
import numpy as np
import logging
from .config_utils import get_cached_config


def is_grey(img, config=None):
    """
    Determine whether an image is greyscale / black-and-white.

    KEY CHANGE: Skin-tone pixels (low saturation, hue in the warm range) are
    excluded from the grey-pixel count so that close-up portraits — where most
    pixels are naturally low-saturation skin — are not wrongly flagged.
    """
    try:
        if config is None:
            config = get_cached_config()

        saturation_threshold = getattr(config, "greyness_threshold", 15) if config else 15

        # Fixed cutoff — not user-configurable
        grey_percentage_cutoff = 95

        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        hue = hsv[:, :, 0]          # 0-179 in OpenCV
        saturation = hsv[:, :, 1]    # 0-255
        value = hsv[:, :, 2]         # 0-255

        # A pixel is "grey" if its saturation is very low
        low_sat_mask = saturation <= saturation_threshold

        # Skin-tone mask: hue roughly 0-25 (warm tones) AND value > 40
        # (not too dark — actual skin, not shadow)
        skin_mask = (hue <= 25) & (value > 40)

        # Exclude skin-tone pixels from "grey" classification
        grey_mask = low_sat_mask & ~skin_mask

        total_pixels = saturation.size
        grey_pixels = int(np.sum(grey_mask))
        grey_percentage = (grey_pixels / total_pixels) * 100

        return grey_percentage > grey_percentage_cutoff

    except Exception as e:
        logging.debug(f"Error in is_grey: {e}")
        return False
