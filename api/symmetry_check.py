import cv2
import numpy as np
from .models import Config

def check_symmetry_with_head(image):
    try:
        config = Config.objects.first()
        if not config:
            threshold = 20  # default symmetry threshold
        else:
            threshold = config.symmetry_threshold
    except Exception:
        threshold = 20

    # Perform symmetry check
    height, width, _ = image.shape
    half_width = width // 2

    left_half = image[:, :half_width]
    right_half = image[:, half_width - 1::-1]

    # Check if the sizes of left_half and right_half are the same
    if left_half.shape != right_half.shape:
        raise ValueError("Size mismatch between left_half and right_half")

    flipped_right_half = cv2.flip(right_half, 1)

    # Calculate the absolute difference between the left and flipped right halves
    diff = cv2.absdiff(left_half, flipped_right_half)

    # Convert the difference image to grayscale
    diff_gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)

    # Calculate the average pixel intensity difference as a symmetry score
    symmetry_score = np.mean(diff_gray)

    # Compare the symmetry score with the threshold
    is_symmetric = symmetry_score < threshold

    return is_symmetric

def issymmetric(image):
    try:
        is_symmetric = check_symmetry_with_head(image)
        return is_symmetric
    except ValueError as e:
        print("Error:", str(e))
        return False
    except Exception as e:
        print(f"Error in issymmetric: {e}")
        return False