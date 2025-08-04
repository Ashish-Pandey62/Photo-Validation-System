import numpy as np
from .models import Config

def background_check(image, config=None):
    try:
        if config is None:
            config = Config.objects.first()
        if not config:
            # Use default threshold if no config
            average_color_threshold = 30  # More sensitive threshold
        else:
            average_color_threshold = config.bgcolor_threshold
    except Exception:
        # Fallback to default
        average_color_threshold = 30  # More sensitive fallback value

    h, w, channels = image.shape

    # Define background regions more comprehensively
    # Top 5% of image (increased from 1.5%)
    top_region = image[:int(0.05 * h), :, :]
    
    # Left and right edges (top 50% of image, increased from 35%)
    left_edge = image[:int(0.50 * h), :int(0.15 * w), :]
    right_edge = image[:int(0.50 * h), int(0.85 * w):, :]
    
    # Bottom 5% of image (new check)
    bottom_region = image[int(0.95 * h):, :, :]
    
    # Combine all background regions
    background_pixels = np.vstack([
        top_region.reshape(-1, 3),
        left_edge.reshape(-1, 3),
        right_edge.reshape(-1, 3),
        bottom_region.reshape(-1, 3)
    ])
    
    if len(background_pixels) == 0:
        return True  # No background pixels to check
    
    # Calculate average color using vectorized operations
    average_color = np.mean(background_pixels)
    
    # Also check for very dark backgrounds (average color < 20)
    is_very_dark = average_color < 20
    
    # Check if background is too dark (average color below threshold)
    return average_color >= average_color_threshold and not is_very_dark
