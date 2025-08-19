import logging
import time
import cv2
from .models import Config
from .performance_utils import resize_for_processing, get_cached_config, time_function

import api.background_check as background_check
import api.blur_check as blur_check
import api.file_format_check as file_format_check
import api.file_size_check as file_size_check
import api.grey_black_and_white_check as grey_black_and_white_check
import api.head_check as head_check
import api.symmetry_check as symmetry_check

logging.basicConfig(level=logging.INFO)

@time_function
def main_optimized(imgPath, max_image_dimension=800):
    """
    Optimized version of the main photo validator with performance improvements.
    """
    # Load config once using cache
    try:
        config = get_cached_config()
        if not config:
            config = Config.objects.create(
                min_height=100,
                max_height=2000,
                min_width=100,
                max_width=2000,
                min_size=10,
                max_size=5000,
                is_jpg=True,
                is_png=True,
                is_jpeg=True,
                bgcolor_threshold=40,
                bg_uniformity_threshold=25,
                blurness_threshold=30,
                pixelated_threshold=100,
                greyness_threshold=5,
                symmetry_threshold=35
            )
    except Exception as e:
        logging.error(f"Error loading config: {e}")
        return "Configuration error"
    
    initial = time.time()
    message = ""

    # Check image file format
    if config.bypass_format_check == False:
        is_file_format_valid = file_format_check.check_image(imgPath)
        if is_file_format_valid:
            message = message + "File format check: Passed (supported format)\n"
        else:
            message = message + "File format check: Failed (unsupported format)\n"
        logging.info(message)
    else:
        message = message + "Bypassed file format check\n"

    # Check image file size
    if config.bypass_size_check == False:
        is_file_size_valid = file_size_check.check_image(imgPath)
        if is_file_size_valid:
            message = message + "File size check: Passed (size within limits)\n"
        else:
            message = message + "File size check: Failed (size outside limits)\n"
        logging.info(message)
    else:
        message = message + "Bypassed file size check\n"

    # Check height of the image
    if config.bypass_height_check == False:
        is_file_height_valid = file_size_check.check_height(imgPath)
        if is_file_height_valid:
            message = message + "File Height check: Passed (height within limits)\n"
        else:
            message = message + "File Height check: Failed (height outside limits)\n"
        logging.info(message)
    else:
        message = message + "Bypassed file height check\n"

    # Check width of the image
    if config.bypass_width_check == False:
        is_file_width_valid = file_size_check.check_width(imgPath)
        if is_file_width_valid:
            message = message + "File Width check: Passed (width within limits)\n"
        else:
            message = message + "File Width check: Failed (width outside limits)\n"
        logging.info(message)
    else:
        message = message + "Bypassed file width check\n"

    # Load and optimize the image
    img = cv2.imread(imgPath)
    if img is None:
        return "Failed to load image"

    # Resize image for faster processing
    original_img = img.copy()  # Keep original for size-dependent checks
    img = resize_for_processing(img, max_image_dimension)

    if config.bypass_corrupted_check == False:
        is_corrupted = file_format_check.is_corrupted_image(img)
        if not is_corrupted:
            message = message + "File Open Test: Passed (image loads correctly)\n"
        else:
            message = message + "File Open Test: Failed (corrupted image)\n"
        logging.info(message)
        if is_corrupted:
            return "Corrupted image detected"
    else:
        message = message + "Bypassed corrupted file check\n"

    if config.bypass_greyness_check == False:
        is_grey = grey_black_and_white_check.is_grey(img, config)
        if is_grey:
            message = message + "Greyness check: Failed (image too grey/black and white)\n"
        else:
            message = message + "Greyness check: Passed (sufficient color variation)\n"
        logging.info(message)
    else:
        message = message + "Bypassed greyness check\n"

    # Check image for blurness and pixelation
    if config.bypass_blurness_check == False:
        is_blur, blur_details = blur_check.check_image_blurness(img, config)
        
        # Check if blur_details contains pixelation information
        if isinstance(blur_details, dict) and 'is_pixelated' in blur_details:
            is_pixelated = blur_details['is_pixelated']
            pixelated_value = blur_details.get('pixelated_value', 0)
            pixelated_threshold = blur_details.get('pixelated_threshold', config.pixelated_threshold)
            
            if is_blur and is_pixelated:
                message = message + "Blurness and pixelation check: Failed (both blur and pixelation detected)\n"
            elif is_blur:
                message = message + "Blurness check: Failed (image too blurry)\n"
            elif is_pixelated:
                message = message + "Pixelation check: Failed ({:.1f} lines detected, max allowed: {:.1f})\n".format(pixelated_value, pixelated_threshold)
            else:
                message = message + "Blurness and pixelation check: Passed\n"
        else:
            # Fallback to old behavior if no pixelation details
            message = message + "Blurness check: " + ('Passed' if not is_blur else 'Failed') + "\n"
        
        logging.info(message)
    else:
        message = message + "Bypassed blurness and pixelation check\n"

    # Check the background of image
    if config.bypass_background_check == False:
        is_background_ok = background_check.background_check(img, config)
        if is_background_ok:
            message = message + "Background check: Passed\n"
        else:
            message = message + "Background check: Failed\n"
        logging.info(message)
    else:
        message = message + "Bypassed background check\n"

    # Check image for head position and coverage (use original image for better accuracy)
    if config.bypass_head_check == False:
        is_head_valid, head_percent = head_check.valid_head_check(original_img)
        if not is_head_valid:
            if head_percent < 10:
                message = message + "Head check: Failed (Head Ratio Small: {:.1f}%)\n".format(head_percent)
            elif 100 > head_percent > 80:
                message = message + "Head check: Failed (Head Ratio Large: {:.1f}%)\n".format(head_percent)
            elif head_percent == 101:
                message = message + "Head check: Failed (Could not detect head)\n"
            else:
                message = message + "Head check: Failed (Multiple heads detected)\n"
        else:
            message = message + "Head check: Passed ({:.1f}% head coverage)\n".format(head_percent)
        logging.info(message)
    else:
        message = message + "Bypassed head check\n"

    # Check Eye Covered (use original image for better accuracy)
    if config.bypass_eye_check == False:
        is_eye_covered = head_check.detect_eyes(original_img)
        if is_eye_covered:
            message = message + "Eye check: Failed (eyes not visible or covered)\n"
        else:
            message = message + "Eye check: Passed (eyes visible)\n"
        logging.info(message)
    else:
        message = message + "Bypassed eye check\n"

    # Check for symmetry
    if not getattr(config, 'bypass_symmetry_check', False):
        try:
            is_symmetric, symmetry_percentage, threshold_percentage = symmetry_check.check_symmetry_with_head(img, config)
            if not is_symmetric:
                message = message + "Symmetry check: Failed ({:.1f}% symmetric, min required: {:.1f}%)\n".format(symmetry_percentage, threshold_percentage)
            else:
                message = message + "Symmetry check: Passed ({:.1f}% symmetric)\n".format(symmetry_percentage)
            logging.info(message)
        except Exception as e:
            logging.error(f"Error in symmetry check for {imgPath}: {e}")
            message = message + "Symmetry check error: " + str(e) + "\n"
    else:
        message = message + "Bypassed symmetry check\n"

    final = time.time()
    logging.info("Total time in second = " + str(final - initial))
    return message 