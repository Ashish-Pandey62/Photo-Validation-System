import cv2
import numpy as np
from .models import Config
import logging
from api.grey_black_and_white_check import is_grey

def check_image_blurness(image, config=None):
    grey = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    is_blur_result, blur_value, blur_threshold = check_if_blur(grey, config)
    is_pixelated_result, pixelated_value, pixelated_threshold = check_if_pixaleted(grey, config)
    
    # Debug logging
    logging.info(f"Blur check: {is_blur_result}, Pixelated check: {is_pixelated_result}")
    
    # Return overall result and detailed values
    overall_is_blur = (is_pixelated_result or is_blur_result)
    return overall_is_blur, {
        'blur_value': blur_value,
        'blur_threshold': blur_threshold,
        'pixelated_value': pixelated_value,
        'pixelated_threshold': pixelated_threshold,
        'is_blur': is_blur_result,
        'is_pixelated': is_pixelated_result
    }

def check_if_blur(gray, config=None):
    try:
        if config is None:
            config = Config.objects.first()
        if not config:
            blurness_threshold = 20  # More sensitive threshold
        else:
            blurness_threshold = config.blurness_threshold
        
        # compute the Laplacian of the image and then return the focus
        # measure, which is simply the variance of the Laplacian
        laplacianVar = cv2.Laplacian(gray, cv2.CV_64F).var()
        logging.info(f"Laplacian variance: {laplacianVar}, Threshold: {blurness_threshold}")
        
        # More sensitive blur detection
        # Also check for very low variance which indicates extreme blur
        is_blur = laplacianVar < blurness_threshold
        is_extremely_blur = laplacianVar < 5  # Very blurry images
        
        # Return boolean result, actual value, and threshold
        return (is_blur or is_extremely_blur), laplacianVar, blurness_threshold
    except Exception as e:
        print(f"Error in check_if_blur: {e}")
        return False, 0, 20


def check_if_pixaleted(gray, config=None):
    try:
        if config is None:
            config = Config.objects.first()
        if not config:
            pixelated_threshold = 100  # Updated to match new model default (was 80)
        else:
            pixelated_threshold = config.pixelated_threshold
    except Exception:
        pixelated_threshold = 100  # Updated fallback value
    
    # Get image dimensions
    height, width = gray.shape
    image_area = height * width
    
    # More conservative adaptive parameters
    # For smaller images, use higher thresholds (less sensitive)
    # For larger images, use lower thresholds (more sensitive)
    if image_area < 500000:  # Small images (< 500K pixels)
        # Less sensitive for small images
        low_threshold = 100  # Increased from 80
        high_threshold = 250  # Increased from 200
        minLineLength = 120   # Increased from 100
        maxLineGap = 25       # Increased from 20
        threshold = 180       # Increased from 150
    elif image_area < 2000000:  # Medium images (< 2M pixels)
        # Balanced sensitivity
        low_threshold = 80    # Increased from 60
        high_threshold = 220  # Increased from 180
        minLineLength = 180   # Increased from 150
        maxLineGap = 20       # Increased from 15
        threshold = 150       # Increased from 120
    else:  # Large images (>= 2M pixels)
        # More sensitive for large images
        low_threshold = 60    # Increased from 40
        high_threshold = 200  # Increased from 160
        minLineLength = 250   # Increased from 200
        maxLineGap = 15       # Increased from 10
        threshold = 130       # Increased from 100
    
    # Edge detection using canny with conservative parameters
    edges = cv2.Canny(gray, low_threshold, high_threshold, apertureSize=3)
    
    # Line detection using hough with conservative parameters
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold, minLineLength, maxLineGap)

    if(lines is None):
        lines = []
    
    num_lines = len(lines)
    logging.info(f"Image area: {image_area}, Lines detected: {num_lines}, Threshold: {pixelated_threshold}")
    logging.info(f"Canny params: low={low_threshold}, high={high_threshold}, Hough params: threshold={threshold}, minLineLength={minLineLength}, maxLineGap={maxLineGap}")
        
    # Return boolean result, actual value, and threshold
    return num_lines > pixelated_threshold, num_lines, pixelated_threshold

def debug_blur_detection(image_path):
    """
    Debug function to test blur detection on a specific image
    """
    try:
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            print(f"Failed to load image: {image_path}")
            return
        
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Get image info
        height, width = gray.shape
        image_area = height * width
        print(f"Image dimensions: {width}x{height} ({image_area} pixels)")
        
        # Test blur detection
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        print(f"Laplacian variance: {laplacian_var}")
        
        # Test pixelation detection
        is_blur, blur_value, blur_threshold = check_if_blur(gray)
        is_pixelated, pixelated_value, pixelated_threshold = check_if_pixaleted(gray)
        
        print(f"Blur detection result: {is_blur} (value: {blur_value}, threshold: {blur_threshold})")
        print(f"Pixelation detection result: {is_pixelated} (lines: {pixelated_value}, threshold: {pixelated_threshold})")
        print(f"Overall blur check result: {is_blur or is_pixelated}")
        
        return {
            'laplacian_variance': laplacian_var,
            'is_blur': is_blur,
            'blur_value': blur_value,
            'blur_threshold': blur_threshold,
            'is_pixelated': is_pixelated,
            'pixelated_value': pixelated_value,
            'pixelated_threshold': pixelated_threshold,
            'overall_result': is_blur or is_pixelated
        }
        
    except Exception as e:
        print(f"Error in debug_blur_detection: {e}")
        return None

