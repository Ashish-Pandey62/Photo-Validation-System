import cv2
import numpy as np
from .models import Config

def is_grey(img, config=None):
    try:
        # Load config or use defaults
        if config is None:
            config = Config.objects.first()

        # Single input threshold
        saturation_threshold = getattr(config, "greyness_threshold", 15) if config else 15

        # Fixed grey percentage cutoff
        grey_percentage_cutoff = 90  # fixed, not user-configurable

        # Convert image to HSV and extract saturation channel
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        saturation = hsv[:, :, 1]

        # Count pixels considered "grey"
        grey_pixels = np.sum(saturation <= saturation_threshold)
        total_pixels = saturation.size
        grey_percentage = (grey_pixels / total_pixels) * 100

        # Return True if more than cutoff % pixels are grey
        return grey_percentage > grey_percentage_cutoff

    except Exception as e:
        print(f"Error in is_grey: {e}")
        return False
