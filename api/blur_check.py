import cv2
import numpy as np
from .models import Config
#import logging
from api.grey_black_and_white_check import is_grey

def check_image_blurness(image):
    grey = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return (check_if_pixaleted(grey) or check_if_blur(grey))

def check_if_blur(gray):
    try:
        config = Config.objects.first()
        if not config:
            blurness_threshold = 35  # default value
        else:
            blurness_threshold = config.blurness_threshold
        
        # compute the Laplacian of the image and then return the focus
        # measure, which is simply the variance of the Laplacian
        laplacianVar = cv2.Laplacian(gray, cv2.CV_64F).var()
        #logging.info(" variance = "+ str(laplacianVar))
        return laplacianVar < blurness_threshold
    except Exception as e:
        print(f"Error in check_if_blur: {e}")
        return False


def check_if_pixaleted(gray):
    try:
        config = Config.objects.first()
        if not config:
            pixelated_threshold = 50  # default value
        else:
            pixelated_threshold = config.pixelated_threshold
    except Exception:
        pixelated_threshold = 50
    #edge detection using canny
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    minLineLength = 200
    maxLineGap = 10

    #number of lines detection using hough

    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 100, minLineLength, maxLineGap)

    if(lines is None):
        lines =[]
    # else:
    #     logging.info(" lines = "+ str(len(lines)))
        
    return len(lines) > pixelated_threshold

