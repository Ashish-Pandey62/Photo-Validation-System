import numpy as np
from .models import Config

def background_check(image, config=None):
    try:
        if config is None:
            config = Config.objects.first()
        if not config:
            # Use default threshold if no config
            average_color_threshold = 50
        else:
            average_color_threshold = config.bgcolor_threshold
    except Exception:
        # Fallback to default
        average_color_threshold = 50

    h, w, channels = image.shape

    # Define background regions more efficiently
    # Top 1.5% of image
    top_region = image[:int(0.015 * h), :, :]
    
    # Left and right edges (top 35% of image)
    left_edge = image[:int(0.35 * h), :int(0.14 * w), :]
    right_edge = image[:int(0.35 * h), int(0.86 * w):, :]
    
    # Combine all background regions
    background_pixels = np.vstack([
        top_region.reshape(-1, 3),
        left_edge.reshape(-1, 3),
        right_edge.reshape(-1, 3)
    ])
    
    if len(background_pixels) == 0:
        return True  # No background pixels to check
    
    # Calculate average color using vectorized operations
    average_color = np.mean(background_pixels)
    
    # Check if background is too dark (average color below threshold)
    return average_color >= average_color_threshold
