import numpy as np
from .models import Config

def is_grey(img, config=None):
    try:
        if config is None:
            config = Config.objects.first()
        if not config:
            greyness_threshold = 15  # More sensitive threshold
        else:
            greyness_threshold = config.greyness_threshold
        
        # Use vectorized operations instead of loops
        # Calculate differences between color channels
        r, g, b = img[:, :, 0], img[:, :, 1], img[:, :, 2]
        
        # Calculate absolute differences between channels
        diff_rg = np.abs(r.astype(np.int16) - g.astype(np.int16))
        diff_rb = np.abs(r.astype(np.int16) - b.astype(np.int16))
        diff_gb = np.abs(g.astype(np.int16) - b.astype(np.int16))
        
        # Check if any pixel exceeds the threshold
        max_diff = np.maximum(np.maximum(diff_rg, diff_rb), diff_gb)
        
        # Calculate percentage of pixels that are grey
        grey_pixels = np.sum(max_diff <= greyness_threshold)
        total_pixels = max_diff.size
        grey_percentage = (grey_pixels / total_pixels) * 100
        
        # Return True if more than 90% of pixels are grey (indicating a mostly grey image)
        return grey_percentage > 90
        
    except Exception as e:
        print(f"Error in is_grey: {e}")
        return False