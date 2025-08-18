import cv2
import numpy as np
from .models import Config

def check_symmetry_with_head(image, config=None):
    try:
        if config is None:
            config = Config.objects.first()
        if not config:
            threshold = 20  # default symmetry threshold
        else:
            threshold = config.symmetry_threshold
    except Exception:
        threshold = 20

    # Perform symmetry check
    height, width, _ = image.shape
    
    # Handle odd-width images properly
    if width % 2 == 1:  # Odd width
        half_width = width // 2
        left_half = image[:, :half_width]
        right_half = image[:, half_width + 1:]  # Skip middle column
    else:  # Even width
        half_width = width // 2
        left_half = image[:, :half_width]
        right_half = image[:, half_width:]

    # Flip the right half horizontally for comparison
    flipped_right_half = cv2.flip(right_half, 1)
    
    # Ensure both halves have the same dimensions
    min_width = min(left_half.shape[1], flipped_right_half.shape[1])
    left_half = left_half[:, :min_width]
    flipped_right_half = flipped_right_half[:, :min_width]

    # Calculate the absolute difference between the left and flipped right halves
    diff = cv2.absdiff(left_half, flipped_right_half)

    # Convert the difference image to grayscale
    diff_gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)

    # Calculate the average pixel intensity difference as a symmetry score
    symmetry_score = np.mean(diff_gray)

    # Convert symmetry score to percentage (lower score = more symmetric)
    # Invert the score so higher percentage means more symmetric
    max_possible_diff = 255  # Maximum possible pixel difference
    symmetry_percentage = max(0, 100 - (symmetry_score / max_possible_diff * 100))
    
    # Convert threshold to percentage for comparison
    threshold_percentage = max(0, 100 - (threshold / max_possible_diff * 100))

    # Compare the symmetry score with the threshold
    is_symmetric = symmetry_score < threshold

    # Return boolean result, actual percentage, and threshold percentage
    return is_symmetric, symmetry_percentage, threshold_percentage

def issymmetric(image, config=None):
    try:
        is_symmetric, symmetry_percentage, threshold_percentage = check_symmetry_with_head(image, config)
        return is_symmetric, symmetry_percentage, threshold_percentage
    except ValueError as e:
        print("Error:", str(e))
        return False, 0, 0
    except Exception as e:
        print(f"Error in issymmetric: {e}")
        return False, 0, 0