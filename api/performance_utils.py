import cv2
import numpy as np
from functools import lru_cache
import time

def resize_for_processing(image, max_dimension=800):
    """
    Resize image for faster processing while maintaining aspect ratio.
    This dramatically improves performance for large images.
    """
    height, width = image.shape[:2]
    
    if max(height, width) <= max_dimension:
        return image
    
    # Calculate new dimensions
    if height > width:
        new_height = max_dimension
        new_width = int(width * max_dimension / height)
    else:
        new_width = max_dimension
        new_height = int(height * max_dimension / width)
    
    # Resize image
    resized = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
    return resized

@lru_cache(maxsize=128)
def get_cached_config():
    """
    Cache config object to avoid repeated database queries.
    """
    from .models import Config
    return Config.objects.first()

def time_function(func):
    """
    Decorator to time function execution for performance monitoring.
    """
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"{func.__name__} took {end_time - start_time:.4f} seconds")
        return result
    return wrapper

def optimize_image_loading(image_path, max_dimension=800):
    """
    Optimize image loading by resizing large images for processing.
    """
    # Load image
    image = cv2.imread(image_path)
    if image is None:
        return None
    
    # Resize if too large
    return resize_for_processing(image, max_dimension) 