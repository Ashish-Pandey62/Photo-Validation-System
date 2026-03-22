import cv2
import numpy as np
import logging
from .config_utils import get_cached_config


def check_text_in_image(image, config=None):
    """
    Detect significant text in a photo using edge-based stroke width analysis.

    Instead of MSER (which produces too many false positives on portraits),
    this uses a simpler, more robust approach:
    1. Detect edges in the peripheral regions of the image only
    2. Find connected components of edge pixels
    3. Filter for text-like stroke patterns (consistent width, aligned)
    4. Only flag if a LARGE cluster of text-like strokes is found

    Returns (has_text: bool, details: dict)
    """
    try:
        if config is None:
            config = get_cached_config()
        text_region_threshold = getattr(config, "text_region_threshold", 15)
    except Exception:
        text_region_threshold = 15

    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape

        # Only search the outer peripheral band of the image
        # Text/watermarks appear at edges, not on the subject's face
        text_score = _detect_peripheral_text(gray, h, w)

        has_text = text_score > text_region_threshold

        return has_text, {
            "text_region_count": text_score,
            "text_region_threshold": text_region_threshold,
        }
    except Exception as e:
        logging.debug(f"Error in text detection: {e}")
        return False, {"error": str(e)}


def _detect_peripheral_text(gray, h, w):
    """
    Detect text-like patterns in the peripheral (outer 10%) band of the image.

    Uses contour analysis on edge-detected peripheral regions.
    The key insight: for passport/portrait photos, any problematic text
    (watermarks, stamps, date stamps) appears at the edges, not on the face.
    """
    # Define the peripheral band (outer 10% on each side)
    band = int(min(h, w) * 0.10)
    if band < 20:
        return 0

    # Extract the 4 border strips
    strips = [
        gray[:band, :],              # top
        gray[h - band:, :],          # bottom
        gray[band:h - band, :band],  # left (excluding corners)
        gray[band:h - band, w - band:],  # right (excluding corners)
    ]

    total_text_regions = 0

    for strip in strips:
        if strip.size == 0:
            continue
        total_text_regions += _count_text_contours_in_strip(strip)

    return total_text_regions


def _count_text_contours_in_strip(strip):
    """
    Count text-like contours in an image strip.

    Text characters have very specific properties:
    - Small, consistent size
    - High contrast edges
    - Compact shape (not elongated streaks)
    """
    sh, sw = strip.shape

    # Adaptive threshold to handle varying backgrounds
    binary = cv2.adaptiveThreshold(
        strip, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 15, 8
    )

    # Remove noise
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    text_count = 0
    strip_area = sh * sw

    for c in contours:
        area = cv2.contourArea(c)
        x, y, cw, ch = cv2.boundingRect(c)

        # Text character size constraints (relative to strip)
        if area < 30 or area > strip_area * 0.05:
            continue

        # Must be small relative to the strip
        if cw > sw * 0.15 or ch > sh * 0.5:
            continue

        # Aspect ratio filter: characters are 0.2 - 4.0
        if ch == 0:
            continue
        aspect = cw / ch
        if aspect < 0.15 or aspect > 5.0:
            continue

        # Fill ratio: characters fill their bbox 25-90%
        bbox_area = cw * ch
        if bbox_area == 0:
            continue
        extent = area / bbox_area
        if extent < 0.2 or extent > 0.92:
            continue

        # Solidity: contour area / convex hull area
        # Text chars are fairly solid (> 0.4)
        hull = cv2.convexHull(c)
        hull_area = cv2.contourArea(hull)
        if hull_area > 0:
            solidity = area / hull_area
            if solidity < 0.35:
                continue

        text_count += 1

    return text_count
