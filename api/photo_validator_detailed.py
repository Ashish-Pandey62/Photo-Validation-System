import logging
import time
import cv2
from .models import Config
import api.background_check as background_check
import api.blur_check as blur_check
import api.file_format_check as file_format_check
import api.file_size_check as file_size_check
import api.grey_black_and_white_check as grey_black_and_white_check
import api.head_check as head_check
import api.symmetry_check as symmetry_check
import os

logging.basicConfig(level=logging.INFO)

def get_detailed_blur_info(image, config=None):
    """Get detailed blur information with percentages"""
    try:
        # Use the updated blur_check function that returns detailed values
        is_blur, blur_details = blur_check.check_image_blurness(image, config)
        
        # Extract the detailed information
        blur_value = blur_details['blur_value']
        blur_threshold = blur_details['blur_threshold']
        pixelated_value = blur_details['pixelated_value']
        pixelated_threshold = blur_details['pixelated_threshold']
        
        # Convert blur value to percentage (higher laplacian variance = sharper image)
        sharpness_percentage = min(100, (blur_value / 500) * 100)
        
        return {
            'is_blur': is_blur,
            'sharpness_percentage': round(sharpness_percentage, 1),
            'laplacian_variance': round(blur_value, 2),
            'threshold': blur_threshold,
            'is_pixelated': blur_details['is_pixelated'],
            'pixelated_lines': pixelated_value,
            'pixelated_threshold': pixelated_threshold
        }
    except Exception as e:
        logging.error(f"Error in get_detailed_blur_info: {e}")
        return {'is_blur': False, 'sharpness_percentage': 0, 'laplacian_variance': 0, 'threshold': 20, 'is_pixelated': False, 'pixelated_lines': 0, 'pixelated_threshold': 100}

def get_detailed_background_info(image, config=None):
    """Get detailed background information with percentages"""
    try:
        if config is None:
            config = Config.objects.first()
        average_color_threshold = config.bgcolor_threshold if config else 30
        
        h, w, channels = image.shape
        
        # Define background regions
        top_region = image[:int(0.05 * h), :, :]
        left_edge = image[:int(0.50 * h), :int(0.15 * w), :]
        right_edge = image[:int(0.50 * h), int(0.85 * w):, :]
        bottom_region = image[int(0.95 * h):, :, :]
        
        # Combine all background regions
        import numpy as np
        background_pixels = np.vstack([
            top_region.reshape(-1, 3),
            left_edge.reshape(-1, 3),
            right_edge.reshape(-1, 3),
            bottom_region.reshape(-1, 3)
        ])
        
        if len(background_pixels) == 0:
            return {'is_background_ok': True, 'brightness_percentage': 100, 'threshold': average_color_threshold}
        
        # Calculate average brightness
        average_color = np.mean(background_pixels)
        brightness_percentage = min(100, (average_color / 255) * 100)
        
        is_background_ok = average_color >= average_color_threshold
        
        return {
            'is_background_ok': is_background_ok,
            'brightness_percentage': round(brightness_percentage, 1),
            'average_color': round(average_color, 2),
            'threshold': average_color_threshold
        }
    except Exception as e:
        logging.error(f"Error in get_detailed_background_info: {e}")
        return {'is_background_ok': False, 'brightness_percentage': 0, 'threshold': 30}

def get_detailed_file_size_info(imgPath, config=None):
    """Get detailed file size information"""
    try:
        if config is None:
            config = Config.objects.first()
        
        min_size = config.min_size if config else 10  # KB
        max_size = config.max_size if config else 5000  # KB
        
        # Get file size in KB
        file_size_bytes = os.path.getsize(imgPath)
        file_size_kb = file_size_bytes / 1024
        
        is_valid = min_size <= file_size_kb <= max_size
        
        return {
            'is_valid': is_valid,
            'actual_size_kb': round(file_size_kb, 2),
            'min_size_kb': min_size,
            'max_size_kb': max_size
        }
    except Exception as e:
        logging.error(f"Error in get_detailed_file_size_info: {e}")
        return {'is_valid': False, 'actual_size_kb': 0, 'min_size_kb': 10, 'max_size_kb': 5000}

def get_detailed_dimension_info(imgPath, config=None):
    """Get detailed dimension information"""
    try:
        if config is None:
            config = Config.objects.first()
        
        min_height = config.min_height if config else 100
        max_height = config.max_height if config else 2000
        min_width = config.min_width if config else 100
        max_width = config.max_width if config else 2000
        
        # Read image to get dimensions
        img = cv2.imread(imgPath)
        if img is None:
            return {'height_valid': False, 'width_valid': False, 'actual_height': 0, 'actual_width': 0}
        
        height, width = img.shape[:2]
        
        height_valid = min_height <= height <= max_height
        width_valid = min_width <= width <= max_width
        
        return {
            'height_valid': height_valid,
            'width_valid': width_valid,
            'actual_height': height,
            'actual_width': width,
            'min_height': min_height,
            'max_height': max_height,
            'min_width': min_width,
            'max_width': max_width
        }
    except Exception as e:
        logging.error(f"Error in get_detailed_dimension_info: {e}")
        return {'height_valid': False, 'width_valid': False, 'actual_height': 0, 'actual_width': 0}

def main_detailed(imgPath):
    """
    Main validation function that returns detailed failure reasons with percentages
    """
    try:
        config = Config.objects.first()
        if not config:
            config = Config.objects.create(
                min_height=100, max_height=2000, min_width=100, max_width=2000,
                min_size=10, max_size=5000, is_jpg=True, is_png=True, is_jpeg=True
            )
    except Exception as e:
        logging.error(f"Error loading config: {e}")
        return []

    detailed_failures = []
    
    # File format check
    if not config.bypass_format_check:
        is_file_format_valid = file_format_check.check_image(imgPath)
        if not is_file_format_valid:
            detailed_failures.append("File format check failed (only JPG, JPEG, PNG allowed)")

    # File size check
    if not config.bypass_size_check:
        size_info = get_detailed_file_size_info(imgPath, config)
        if not size_info['is_valid']:
            detailed_failures.append(f"File size check failed ({size_info['actual_size_kb']}KB, required: {size_info['min_size_kb']}-{size_info['max_size_kb']}KB)")

    # Dimension checks
    if not config.bypass_height_check or not config.bypass_width_check:
        dim_info = get_detailed_dimension_info(imgPath, config)
        
        if not config.bypass_height_check and not dim_info['height_valid']:
            detailed_failures.append(f"Height check failed ({dim_info['actual_height']}px, required: {dim_info['min_height']}-{dim_info['max_height']}px)")
        
        if not config.bypass_width_check and not dim_info['width_valid']:
            detailed_failures.append(f"Width check failed ({dim_info['actual_width']}px, required: {dim_info['min_width']}-{dim_info['max_width']}px)")

    # Load image for further checks
    img = cv2.imread(imgPath)
    if img is None:
        detailed_failures.append("File corrupted (could not load image)")
        return detailed_failures

    # Corrupted image check
    if not config.bypass_corrupted_check:
        is_corrupted = file_format_check.is_corrupted_image(img)
        if is_corrupted:
            detailed_failures.append("File corrupted")

    # Greyscale check
    if not config.bypass_greyness_check:
        is_grey = grey_black_and_white_check.is_grey(img, config)
        if is_grey:
            detailed_failures.append("Greyscale check failed (image should be in color)")

    # Blur check
    if not config.bypass_blurness_check:
        blur_info = get_detailed_blur_info(img, config)
        if blur_info['is_blur']:
            min_sharpness_percent = (blur_info['threshold'] / 500) * 100
            detailed_failures.append(f"Blurness check failed ({blur_info['sharpness_percentage']}% sharpness, min required: {min_sharpness_percent:.1f}%)")

    # Background check
    if not config.bypass_background_check:
        bg_info = get_detailed_background_info(img, config)
        if not bg_info['is_background_ok']:
            min_brightness_percent = (bg_info['threshold'] / 255) * 100
            detailed_failures.append(f"Background check failed ({bg_info['brightness_percentage']}% brightness, min required: {min_brightness_percent:.1f}%)")

    # Head check
    if not config.bypass_head_check:
        is_head_valid, head_percent = head_check.valid_head_check(img)
        if not is_head_valid:
            if head_percent < 10:
                detailed_failures.append(f"Head check failed ({head_percent:.1f}% head coverage, min required: 10%)")
            elif head_percent > 80:
                detailed_failures.append(f"Head check failed ({head_percent:.1f}% head coverage, max allowed: 80%)")
            elif head_percent == 101:
                detailed_failures.append("Head check failed (no face detected)")
            elif head_percent == 102:
                detailed_failures.append("Head check failed (multiple faces detected)")
            else:
                detailed_failures.append(f"Head check failed ({head_percent:.1f}% head coverage, required: 10-80%)")

    # Eye check
    if not config.bypass_eye_check:
        is_eye_covered = head_check.detect_eyes(img)
        if is_eye_covered:
            detailed_failures.append("Eye check failed (eyes not visible or covered)")

    # Symmetry check
    if not config.bypass_symmetry_check:
        is_symmetric, symmetry_percentage, threshold_percentage = symmetry_check.issymmetric(img, config)
        if not is_symmetric:
            detailed_failures.append(f"Symmetry check failed ({symmetry_percentage:.1f}% symmetric, min required: {threshold_percentage:.1f}%)")

    return detailed_failures
