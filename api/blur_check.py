import cv2
import numpy as np
from .models import Config
#import logging
from api.grey_black_and_white_check import is_grey

def check_image_blurness(image, config=None):
    grey = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return (check_if_pixaleted(grey, config) or check_if_blur(grey, config))

def check_if_blur(gray, config=None):
    try:
        if config is None:
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


def check_if_pixaleted(gray, config=None):
    try:
        if config is None:
            config = Config.objects.first()
        if not config:
            pixelated_threshold = 50  # default value
        else:
            pixelated_threshold = config.pixelated_threshold
    except Exception:
        pixelated_threshold = 50
    
    # Adaptive parameters based on image size
    height, width = gray.shape
    image_area = height * width
    
    # Scale parameters based on image size
    scale_factor = min(1.0, image_area / (1920 * 1080))  # Normalize to 1080p
    
    # Adaptive Canny parameters
    low_threshold = max(30, int(50 * scale_factor))
    high_threshold = max(100, int(150 * scale_factor))
    
    #edge detection using canny with adaptive parameters
    edges = cv2.Canny(gray, low_threshold, high_threshold, apertureSize=3)
    
    # Adaptive line detection parameters
    minLineLength = max(50, int(200 * scale_factor))
    maxLineGap = max(5, int(10 * scale_factor))
    threshold = max(50, int(100 * scale_factor))

    #number of lines detection using hough
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold, minLineLength, maxLineGap)

    if(lines is None):
        lines = []
    # else:
    #     logging.info(" lines = "+ str(len(lines)))
        
    return len(lines) > pixelated_threshold

