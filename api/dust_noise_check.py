import cv2
import numpy as np
import logging
from .config_utils import get_cached_config


def check_dust_and_noise(image, config=None):
    """
    Detect dust spots and excessive noise in a photo.

    1. Dust/scratch detection — isolated bright/dark spots found via
       median-blur subtraction.
    2. Noise estimation — high-frequency energy measured via Laplacian MAD
       on a smooth region of the image.

    Returns (has_issues: bool, details: dict)
    """
    try:
        if config is None:
            config = get_cached_config()
        noise_threshold = getattr(config, "noise_threshold", 40)
        dust_spot_threshold = getattr(config, "dust_spot_threshold", 50)
    except Exception:
        noise_threshold = 40
        dust_spot_threshold = 50

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    dust_count = _detect_dust_spots(gray)
    noise_level = _estimate_noise(gray)

    has_dust = dust_count > dust_spot_threshold
    is_noisy = noise_level > noise_threshold

    return (has_dust or is_noisy), {
        "dust_spot_count": dust_count,
        "dust_spot_threshold": dust_spot_threshold,
        "noise_level": round(float(noise_level), 2),
        "noise_threshold": noise_threshold,
        "has_dust": has_dust,
        "is_noisy": is_noisy,
    }


def _detect_dust_spots(gray):
    """
    Detect isolated bright/dark spots (dust, scratches, sensor defects)
    using median-blur subtraction.

    Tuned to avoid false positives from JPEG compression artifacts,
    skin texture, hair detail, and fabric patterns.
    """
    # Larger kernel (9px) to only catch genuinely isolated spots
    median = cv2.medianBlur(gray, 9)

    # Absolute difference — real dust spots produce large differences
    diff = cv2.absdiff(gray, median)

    # Higher threshold (50) to ignore JPEG artifacts and texture
    _, binary = cv2.threshold(diff, 50, 255, cv2.THRESH_BINARY)

    # Larger morphological open (5x5) to remove small noise clusters
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

    # Find contours (each = one spot)
    contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filter: keep spots with reasonable size
    h, w = gray.shape
    image_area = h * w
    min_spot = 15                     # at least 15 pixels (real dust spots are visible)
    max_spot = image_area * 0.003     # at most 0.3% of image

    dust_count = 0
    for c in contours:
        area = cv2.contourArea(c)
        if min_spot <= area <= max_spot:
            # Additional filter: real dust spots are roughly circular
            perimeter = cv2.arcLength(c, True)
            if perimeter > 0:
                circularity = 4 * np.pi * area / (perimeter * perimeter)
                # Only count spots with reasonable circularity (> 0.3)
                # This filters out edge artifacts, text fragments, etc.
                if circularity > 0.3:
                    dust_count += 1

    return dust_count


def _estimate_noise(gray):
    """
    Estimate overall image noise level.

    Uses the Laplacian-based method on a smooth region of the image
    (avoids textured areas like hair/fabric that inflate noise estimates).

    Based on: J. Immerkær, "Fast Noise Variance Estimation", CVIU 1996.
    """
    h, w = gray.shape

    # Use the center region, but first apply Gaussian blur to reduce
    # the impact of fine texture (hair, fabric) on noise estimation
    margin_h = int(0.15 * h)
    margin_w = int(0.15 * w)
    patch = gray[margin_h:h - margin_h, margin_w:w - margin_w]

    if patch.size == 0:
        return 0.0

    # Light pre-blur to dampen texture signal (not noise)
    # This prevents sharp textured photos from being flagged
    smoothed = cv2.GaussianBlur(patch, (3, 3), 0)

    # Laplacian of the smoothed patch
    laplacian = cv2.Laplacian(smoothed, cv2.CV_64F)

    # MAD-based noise estimate (σ ≈ MAD / 0.6745)
    abs_vals = np.abs(laplacian)
    mad = np.median(abs_vals[abs_vals > 0])  # ignore zero values
    noise_sigma = mad / 0.6745 if mad > 0 else 0.0

    return float(noise_sigma)
