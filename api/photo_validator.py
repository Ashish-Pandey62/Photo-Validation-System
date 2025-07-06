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

logging.basicConfig(level=logging.INFO)


def main(imgPath):
    config = Config.objects.all()[0]
    initial = time.time()
    message = ""

    # Check image file format
    if config.bypass_format_check==False:
      is_file_format_valid = file_format_check.check_image(imgPath)
      message = message + "File format check: " + ('Passed' if is_file_format_valid else 'Failed') + "\n"
      logging.info(message)
    else:
      message = message + "Bypassed file format check\n"


    # Check image file size
    if config.bypass_size_check==False:
      is_file_size_valid = file_size_check.check_image(imgPath)
      message = message + "File size check: " + ('Passed' if is_file_format_valid else 'Failed') + "\n"
      logging.info(message)
    else:
      message = message + "Bypassed file size check\n"

    # if not is_file_size_valid:
    #     return "Not Valid File Size"

    # Check height of the image
    if config.bypass_height_check==False:
      is_file_height_valid = file_size_check.check_height(imgPath)
      message = message + "File Height check: " + ('Passed' if is_file_height_valid else 'Failed') + "\n"
      logging.info(message)
    else:
      message = message + "Bypassed file height check\n"

    # if not is_file_height_valid:
    #     return "Not Valid File Height"

  # Check width of the image
    if config.bypass_width_check==False:
      is_file_width_valid = file_size_check.check_width(imgPath)
      message = message + "File Width check: " + ('Passed' if is_file_width_valid else 'Failed') + "\n"
      logging.info(message)
    else:
      message = message + "Bypassed file width check\n"

    # if not is_file_width_valid:
    #     return "Not Valid File Height"

    # Load the image
    img = cv2.imread(imgPath)

    if config.bypass_corrupted_check == False:
      is_corrupted = file_format_check.is_corrupted_image(img)
      message = message + "File Open Test: " + ('Passed' if not is_corrupted else 'Failed') + "\n"
      logging.info(message)
      if file_format_check.is_corrupted_image(img):
        exit()
    else:
      message = message + "Bypassed corrupted file check\n"


    if config.bypass_greyness_check==False:
      message = message + "Greyscale check: " + ('Passed' if not grey_black_and_white_check.is_grey(img) else 'Failed') + "\n"
      logging.info(message)
    else:
      message = message + "Bypassed greyness check\n"

    # Check image for blurness
    if config.bypass_blurness_check == False:
      is_blur = blur_check.check_image_blurness(img)
      message = message + "Blurness check: " + ('Passed' if not is_blur else 'Failed') + "\n"
      logging.info(message)
    else:
      message = message + "Bypassed blurness check\n"

    # Check the background of image
    if config.bypass_background_check==False:
      is_background_ok = background_check.background_check(img)
      message = message + "Background check: " + ('Passed' if is_background_ok else 'Failed') + "\n"
      logging.info(message)
    else:
      message = message + "Bypassed background check\n"

    # Check image for head position and coverage
    if(config.bypass_head_check==False):
      is_head_valid ,head_percent= head_check.valid_head_check(img)
      if not is_head_valid:
        if(head_percent<10):
          message = message + "Head check: " + ('Head Ratio Small')+ "\n"
        elif(100>head_percent>80):
          message = message + "Head check: " + ('Head Ratio Large')+ "\n"
        elif(head_percent== 101):
          message = message + "Head check: " + ('Couldnot detect head') + "\n"
        else:
          message = message + "Head check: multiple heads detected"+ "\n"
              
      logging.info(message)
    else:
      message = message + "Bypassed head check\n"

    # Check Eye Covered
    if(config.bypass_eye_check==False):
      is_eye_covered = head_check.detect_eyes(img)
      message = message + "Eye check: " + ('Passed' if not is_eye_covered else 'Failed') + "\n"
      logging.info(message)
    else:
      message = message + "Bypassed eye check\n"

    # Check for symmetry
    if config.bypass_symmetry_check==False:
      is_symmetric = symmetry_check.issymmetric(img)
      message = message + "Symmetry check: " + ('Passed' if is_symmetric else 'Failed') + "\n"
      logging.info(message)
    else:
      message = message + "Bypassed symmetry check\n"

    # Display the imported image
    # cv2.imshow('Application Photo', img)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()
    final = time.time()
    logging.info("Total time in second = "+ str(final-initial))
    return message
