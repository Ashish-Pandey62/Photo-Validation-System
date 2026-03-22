import logging
import time
import cv2
from .performance_utils import resize_for_processing, time_function
from .config_utils import get_cached_config

import api.background_check as background_check
import api.blur_check as blur_check
import api.file_format_check as file_format_check
import api.file_size_check as file_size_check
import api.grey_black_and_white_check as grey_black_and_white_check
import api.head_check as head_check
import api.symmetry_check as symmetry_check
import api.printed_photo_check as printed_photo_check
import api.dust_noise_check as dust_noise_check
import api.text_detection_check as text_detection_check

@time_function
def main_optimized(imgPath, max_image_dimension=800, config=None):
    """
    Optimized version of the main photo validator with performance improvements.
    """
    # Load config once using cache
    try:
        if config is None:
            config = get_cached_config()
    except Exception as e:
        logging.error(f"Error loading config: {e}")
        return "Configuration error"
    
    initial = time.time()
    message = ""

    # Check image file format
    if config.bypass_format_check == False:
        is_file_format_valid = file_format_check.check_image(imgPath,config)
        if is_file_format_valid:
            message = message + "File format check: Passed (supported format)\n"
        else:
            message = message + "File format check: Failed (unsupported format)\n"
        logging.debug(message)
    else:
        message = message + "Bypassed file format check\n"

    # Check image file size
    if config.bypass_size_check == False:
        is_file_size_valid = file_size_check.check_image(imgPath,config)
        if is_file_size_valid:
            message = message + "File size check: Passed (size within limits)\n"
        else:
            message = message + "File size check: Failed (size outside limits)\n"
        logging.debug(message)
    else:
        message = message + "Bypassed file size check\n"

    # Check height of the image
    if config.bypass_height_check == False:
        is_file_height_valid = file_size_check.check_height(imgPath,config)
        if is_file_height_valid:
            message = message + "File Height check: Passed (height within limits)\n"
        else:
            message = message + "File Height check: Failed (height outside limits)\n"
        logging.debug(message)
    else:
        message = message + "Bypassed file height check\n"

    # Check width of the image
    if config.bypass_width_check == False:
        is_file_width_valid = file_size_check.check_width(imgPath,config)
        if is_file_width_valid:
            message = message + "File Width check: Passed (width within limits)\n"
        else:
            message = message + "File Width check: Failed (width outside limits)\n"
        logging.debug(message)
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
        logging.debug(message)
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
        logging.debug(message)
    else:
        message = message + "Bypassed greyness check\n"

    # Check image for blurness
    if config.bypass_blurness_check == False:
        is_blur, blur_details = blur_check.check_image_blurness(img, config)
        if is_blur:
            blur_value = blur_details['blur_value']
            blur_threshold = blur_details['blur_threshold']
            message = message + "Blurness check: Failed (sharpness {:.1f}, min required: {:.1f})\n".format(blur_value, blur_threshold)
        else:
            message = message + "Blurness check: Passed\n"
        logging.debug(message)
    else:
        message = message + "Bypassed blurness check\n"

    # Check the background of image
    if config.bypass_background_check == False:
        is_background_ok = background_check.background_check(img, config)
        if is_background_ok:
            message = message + "Background check: Passed\n"
        else:
            message = message + "Background check: Failed\n"
        logging.debug(message)
    else:
        message = message + "Bypassed background check\n"

    # Check image for head position and coverage (use original image for better accuracy)
    if config.bypass_head_check == False:
        is_head_valid, head_percent = head_check.valid_head_check(original_img, config)
        if not is_head_valid:
            if head_percent == 101:
                message = message + "Head check: Failed (Could not detect head)\n"
            elif head_percent == 102:
                message = message + "Head check: Failed (Multiple heads detected)\n"
            else:
                min_pct = getattr(config, 'min_head_percent', 10)
                max_pct = getattr(config, 'max_head_percent', 80)
                message = message + "Head check: Failed ({:.1f}% head coverage, required: {:.0f}-{:.0f}%)\n".format(head_percent, min_pct, max_pct)
        else:
            message = message + "Head check: Passed ({:.1f}% head coverage)\n".format(head_percent)
        logging.debug(message)
    else:
        message = message + "Bypassed head check\n"

    # Check Eye Covered (use original image for better accuracy)
    if config.bypass_eye_check == False:
        # detect_eyes now returns True = eyes visible (good), False = not visible (bad)
        eyes_visible = head_check.detect_eyes(original_img)
        if not eyes_visible:
            message = message + "Eye check: Failed (eyes not visible or covered)\n"
        else:
            message = message + "Eye check: Passed (eyes visible)\n"
        logging.debug(message)
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
            logging.debug(message)
        except Exception as e:
            logging.error(f"Error in symmetry check for {imgPath}: {e}")
            message = message + "Symmetry check error: " + str(e) + "\n"
    else:
        message = message + "Bypassed symmetry check\n"

    # Check for printed photo (photo-of-photo)
    if not getattr(config, 'bypass_printed_photo_check', False):
        try:
            is_printed, print_details = printed_photo_check.check_printed_photo(img, config)
            if is_printed:
                reasons = []
                if print_details.get('has_moire_pattern'):
                    reasons.append('moiré pattern detected')
                if print_details.get('has_border_lines'):
                    reasons.append('border lines detected')
                message = message + "Printed photo check: Failed ({})\n".format(', '.join(reasons))
            else:
                message = message + "Printed photo check: Passed\n"
            logging.debug(message)
        except Exception as e:
            logging.error(f"Error in printed photo check for {imgPath}: {e}")
            message = message + "Printed photo check error: " + str(e) + "\n"
    else:
        message = message + "Bypassed printed photo check\n"

    # Check for dust and noise
    if not getattr(config, 'bypass_dust_noise_check', False):
        try:
            has_issues, dust_details = dust_noise_check.check_dust_and_noise(img, config)
            if has_issues:
                issues = []
                if dust_details.get('has_dust'):
                    issues.append('{} dust spots (max: {})'.format(dust_details['dust_spot_count'], dust_details['dust_spot_threshold']))
                if dust_details.get('is_noisy'):
                    issues.append('noise level {:.1f} (max: {})'.format(dust_details['noise_level'], dust_details['noise_threshold']))
                message = message + "Dust/noise check: Failed ({})\n".format(', '.join(issues))
            else:
                message = message + "Dust/noise check: Passed\n"
            logging.debug(message)
        except Exception as e:
            logging.error(f"Error in dust/noise check for {imgPath}: {e}")
            message = message + "Dust/noise check error: " + str(e) + "\n"
    else:
        message = message + "Bypassed dust/noise check\n"

    # Check for text in image
    if not getattr(config, 'bypass_text_check', False):
        try:
            has_text, text_details = text_detection_check.check_text_in_image(img, config)
            if has_text:
                message = message + "Text check: Failed ({} text regions found, max: {})\n".format(
                    text_details['text_region_count'], text_details['text_region_threshold'])
            else:
                message = message + "Text check: Passed\n"
            logging.debug(message)
        except Exception as e:
            logging.error(f"Error in text check for {imgPath}: {e}")
            message = message + "Text check error: " + str(e) + "\n"
    else:
        message = message + "Bypassed text check\n"

    final = time.time()
    logging.debug("Total time in second = " + str(final - initial))
    return message 
