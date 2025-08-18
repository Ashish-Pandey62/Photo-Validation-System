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
                is_jpeg=True
            )
    except Exception as e:
        logging.error(f"Error loading config: {e}")
        return "Configuration error"
    
    initial = time.time()
    message = ""

    # Check image file format
    if config.bypass_format_check == False:
        is_file_format_valid = file_format_check.check_image(imgPath)
        message = message + "File format check: " + ('Passed' if is_file_format_valid else 'Failed') + "\n"
        logging.info(message)
    else:
        message = message + "Bypassed file format check\n"

    # Check image file size
    if config.bypass_size_check == False:
        is_file_size_valid = file_size_check.check_image(imgPath)
        message = message + "File size check: " + ('Passed' if is_file_size_valid else 'Failed') + "\n"
        logging.info(message)
    else:
        message = message + "Bypassed file size check\n"

    # Check height of the image
    if config.bypass_height_check == False:
        is_file_height_valid = file_size_check.check_height(imgPath)
        message = message + "File Height check: " + ('Passed' if is_file_height_valid else 'Failed') + "\n"
        logging.info(message)
    else:
        message = message + "Bypassed file height check\n"

    # Check width of the image
    if config.bypass_width_check == False:
        is_file_width_valid = file_size_check.check_width(imgPath)
        message = message + "File Width check: " + ('Passed' if is_file_width_valid else 'Failed') + "\n"
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
        message = message + "File Open Test: " + ('Passed' if not is_corrupted else 'Failed') + "\n"
        logging.info(message)
        if is_corrupted:
            return "Corrupted image detected"
    else:
        message = message + "Bypassed corrupted file check\n"

    if config.bypass_greyness_check == False:
        message = message + "Greyscale check: " + ('Passed' if not grey_black_and_white_check.is_grey(img, config) else 'Failed') + "\n"
        logging.info(message)
    else:
        message = message + "Bypassed greyness check\n"

    # Check image for blurness
    if config.bypass_blurness_check == False:
        is_blur, blur_details = blur_check.check_image_blurness(img, config)
        message = message + "Blurness check: " + ('Passed' if not is_blur else 'Failed') + "\n"
        logging.info(message)
    else:
        message = message + "Bypassed blurness check\n"

    # Check the background of image
    if config.bypass_background_check == False:
        is_background_ok = background_check.background_check(img, config)
        message = message + "Background check: " + ('Passed' if is_background_ok else 'Failed') + "\n"
        logging.info(message)
    else:
        message = message + "Bypassed background check\n"

    # Check image for head position and coverage (use original image for better accuracy)
    if config.bypass_head_check == False:
        is_head_valid, head_percent = head_check.valid_head_check(original_img)
        if not is_head_valid:
            if head_percent < 10:
                message = message + "Head check: " + ('Head Ratio Small') + "\n"
            elif 100 > head_percent > 80:
                message = message + "Head check: " + ('Head Ratio Large') + "\n"
            elif head_percent == 101:
                message = message + "Head check: " + ('Couldnot detect head') + "\n"
            else:
                message = message + "Head check: multiple heads detected" + "\n"
        logging.info(message)
    else:
        message = message + "Bypassed head check\n"

    # Check Eye Covered (use original image for better accuracy)
    if config.bypass_eye_check == False:
        is_eye_covered = head_check.detect_eyes(original_img)
        message = message + "Eye check: " + ('Passed' if not is_eye_covered else 'Failed') + "\n"
        logging.info(message)
    else:
        message = message + "Bypassed eye check\n"

    # Check for symmetry
    if config.bypass_symmetry_check == False:
        is_symmetric = symmetry_check.issymmetric(img, config)
        message = message + "Symmetry check: " + ('Passed' if is_symmetric else 'Failed') + "\n"
        logging.info(message)
    else:
        message = message + "Bypassed symmetry check\n"

    final = time.time()
    logging.info("Total time in second = " + str(final - initial))
    return message 