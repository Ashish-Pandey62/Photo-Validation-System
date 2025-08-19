import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim
from .models import Config

def check_symmetry_with_head(image, config=None):
    try:
        if config is None:
            config = Config.objects.first()
        if not config:
            threshold = 20
        else:
            threshold = config.symmetry_threshold
    except Exception:
        threshold = 20

    height, width, _ = image.shape

    # ---- Step 1: Face detection (lightweight Haar cascade) ----
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)

    if len(faces) > 0:
        # Use the largest detected face
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
        roi = image[y:y+h, x:x+w]
    else:
        # Fallback: use full image
        roi = image

    h, w, _ = roi.shape
    half_w = w // 2

    left_half = roi[:, :half_w]
    right_half = roi[:, w - half_w:]

    # Flip right half
    flipped_right = cv2.flip(right_half, 1)

    # Ensure same size
    min_w = min(left_half.shape[1], flipped_right.shape[1])
    left_half = left_half[:, :min_w]
    flipped_right = flipped_right[:, :min_w]

    # ---- Step 2: Compare halves ----
    # Use SSIM (structural similarity)
    left_gray = cv2.cvtColor(left_half, cv2.COLOR_BGR2GRAY)
    right_gray = cv2.cvtColor(flipped_right, cv2.COLOR_BGR2GRAY)
    symmetry_score, _ = ssim(left_gray, right_gray, full=True)

    # SSIM score is 0–1 (1 = identical)
    symmetry_percentage = symmetry_score * 100
    threshold_percentage = threshold  # now directly percentage

    is_symmetric = symmetry_percentage >= threshold_percentage

    return is_symmetric, symmetry_percentage, threshold_percentage
