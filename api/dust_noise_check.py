import cv2
import numpy as np
import logging
from .config_utils import get_cached_config


def check_dust_and_noise(image, config=None):
    """
    Detect dust spots and excessive noise in a photo.

    1. Dust/scratch detection — isolated bright/dark spots found via
       median-blur subtraction.
    2. Noise estimation — high-frequency energy measured as the difference
       between the original and a Gaussian-blurred version.

    Returns (has_issues: bool, details: dict)
    """
    try:
        if config is None:
            config = get_cached_config()
        noise_threshold = getattr(config, "noise_threshold", 25)
        dust_spot_threshold = getattr(config, "dust_spot_threshold", 15)
    except Exception:
        noise_threshold = 25
        dust_spot_threshold = 15

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    dust_count = _detect_dust_spots(gray)
    noise_level = _estimate_noise(gray)

    has_dust = dust_count > dust_spot_threshold
    is_noisy = noise_level > noise_threshold

    return (has_dust or is_noisy), {
        "dust_spot_count": dust_count,
        "dust_spot_threshold": dust_spot_threshold,
        "noise_level": round(noise_level, 2),
        "noise_threshold": noise_threshold,
        "has_dust": has_dust,
        "is_noisy": is_noisy,
    }


def _detect_dust_spots(gray):
    """
    Detect isolated bright/dark spots (dust, scratches, sensor defects)
    using median-blur subtraction.

    Median blur preserves edges but removes isolated spots; subtracting
    the blurred version from the original leaves only the spots.
    """
    # Median blur with a kernel large enough to swallow dust spots
    median = cv2.medianBlur(gray, 7)

    # Absolute difference — spots appear as bright pixels
    diff = cv2.absdiff(gray, median)

    # Threshold to find significant spots
    _, binary = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)

    # Morphological open to remove tiny noise (keep only real spots)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

    # Find contours (each = one spot)
    contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filter: keep spots with reasonable size (not huge blobs, not sub-pixel)
    h, w = gray.shape
    image_area = h * w
    min_spot = 4                      # at least 4 pixels
    max_spot = image_area * 0.005     # at most 0.5% of image

    dust_count = 0
    for c in contours:
        area = cv2.contourArea(c)
        if min_spot <= area <= max_spot:
            dust_count += 1

    return dust_count


def _estimate_noise(gray):
    """
    Estimate overall image noise level.

    Uses the Laplacian-based method: apply a Laplacian filter, then compute
    the robust MAD (median absolute deviation) of the result. This gives a
    noise estimate that is insensitive to image content.

    Based on: J. Immerkær, "Fast Noise Variance Estimation", CVIU 1996.
    """
    h, w = gray.shape
    # Use a small, consistent patch from the center to avoid edge effects
    # from objects near borders
    margin_h = int(0.1 * h)
    margin_w = int(0.1 * w)
    patch = gray[margin_h:h - margin_h, margin_w:w - margin_w]

    if patch.size == 0:
        return 0.0

    # Laplacian of the patch
    laplacian = cv2.Laplacian(patch, cv2.CV_64F)

    # MAD-based noise estimate (σ ≈ MAD / 0.6745)
    mad = np.median(np.abs(laplacian - np.median(laplacian)))
    noise_sigma = mad / 0.6745 if mad > 0 else 0.0

    return float(noise_sigma)
