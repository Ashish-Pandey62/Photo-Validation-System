import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim
from .config_utils import get_cached_config


def check_symmetry_with_head(image, config=None):
    """
    Evaluate facial symmetry by comparing the left and right halves of the
    detected face region using SSIM.

    Improvements over the old implementation:
    - Applies histogram equalisation to both halves before comparison so
      that directional lighting doesn't tank the score.
    - Applies a small Gaussian blur to reduce noise sensitivity.
    - Uses a sensible default threshold (30 %).
    """
    try:
        if config is None:
            config = get_cached_config()
        if not config:
            threshold = 30
        else:
            threshold = getattr(config, "symmetry_threshold", 30)
    except Exception:
        threshold = 30

    height, width = image.shape[:2]

    # ---- Step 1: Face detection (Haar cascade for speed) ----
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)

    if len(faces) > 0:
        # Use the largest detected face
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
        roi = image[y:y + h, x:x + w]
    else:
        # Fallback: use full image
        roi = image

    h, w = roi.shape[:2]
    if h < 10 or w < 10:
        # Too small to compare meaningfully
        return True, 100.0, threshold

    half_w = w // 2
    left_half = roi[:, :half_w]
    right_half = roi[:, w - half_w:]

    # Flip right half to align with left
    flipped_right = cv2.flip(right_half, 1)

    # Ensure same size
    min_w = min(left_half.shape[1], flipped_right.shape[1])
    left_half = left_half[:, :min_w]
    flipped_right = flipped_right[:, :min_w]

    # ---- Step 2: Pre-process to reduce lighting / noise sensitivity ----
    left_gray = cv2.cvtColor(left_half, cv2.COLOR_BGR2GRAY)
    right_gray = cv2.cvtColor(flipped_right, cv2.COLOR_BGR2GRAY)

    # Histogram equalisation normalises brightness across both halves
    left_gray = cv2.equalizeHist(left_gray)
    right_gray = cv2.equalizeHist(right_gray)

    # Small Gaussian blur to reduce pixel-level noise
    left_gray = cv2.GaussianBlur(left_gray, (5, 5), 0)
    right_gray = cv2.GaussianBlur(right_gray, (5, 5), 0)

    # ---- Step 3: Compare ----
    symmetry_score, _ = ssim(left_gray, right_gray, full=True)
    symmetry_percentage = symmetry_score * 100

    is_symmetric = symmetry_percentage >= threshold
    return is_symmetric, symmetry_percentage, float(threshold)
