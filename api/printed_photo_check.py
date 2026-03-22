import cv2
import numpy as np
import logging
from .config_utils import get_cached_config


def check_printed_photo(image, config=None):
    """
    Detect if a photo is a re-photograph of a printed original.

    Combines two signals:
    1. Moiré pattern detection via FFT spectral analysis
    2. Border line detection via Hough transform (edges of paper/card visible)

    Returns (is_printed: bool, details: dict)
    """
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape

        is_moire = _detect_moire(gray)
        has_border_lines = _detect_border_lines(gray, h, w)

        # Image is flagged if EITHER signal is strong
        is_printed = is_moire or has_border_lines

        return is_printed, {
            "has_moire_pattern": is_moire,
            "has_border_lines": has_border_lines,
        }
    except Exception as e:
        logging.debug(f"Error in printed photo check: {e}")
        return False, {"error": str(e)}


def _detect_moire(gray):
    """
    Detect moiré patterns using 2D FFT.

    Moiré patterns from re-photographing a printed halftone image show up
    as distinct spectral peaks at mid-to-high frequencies in the frequency
    domain. Normal photos have most energy concentrated in the low
    frequencies with a smooth roll-off.
    """
    # Resize to consistent size for FFT analysis
    analysis_size = 256
    resized = cv2.resize(gray, (analysis_size, analysis_size))
    img_float = np.float32(resized)

    # Apply windowing to reduce spectral leakage
    window = np.outer(np.hanning(analysis_size), np.hanning(analysis_size))
    img_windowed = img_float * window

    # 2D FFT
    f_transform = np.fft.fft2(img_windowed)
    f_shift = np.fft.fftshift(f_transform)
    magnitude = np.abs(f_shift)

    # Avoid log(0)
    magnitude = np.log1p(magnitude)

    center_y, center_x = analysis_size // 2, analysis_size // 2

    # Create radial masks for different frequency bands
    y_coords, x_coords = np.ogrid[:analysis_size, :analysis_size]
    radius = np.sqrt((x_coords - center_x) ** 2 + (y_coords - center_y) ** 2)

    # Low frequency: inner 15% of spectrum
    # Mid frequency: 15-50% (where moiré peaks appear)
    # High frequency: 50-90%
    max_radius = analysis_size / 2
    low_mask = radius < (0.15 * max_radius)
    mid_mask = (radius >= 0.15 * max_radius) & (radius < 0.50 * max_radius)
    high_mask = (radius >= 0.50 * max_radius) & (radius < 0.90 * max_radius)

    low_energy = np.mean(magnitude[low_mask]) if np.any(low_mask) else 0
    mid_energy = np.mean(magnitude[mid_mask]) if np.any(mid_mask) else 0
    high_energy = np.mean(magnitude[high_mask]) if np.any(high_mask) else 0

    if low_energy == 0:
        return False

    # Moiré shows unusually high mid-frequency energy relative to low
    mid_ratio = mid_energy / low_energy

    # Also check for sharp peaks in the mid-frequency band
    mid_values = magnitude[mid_mask]
    if mid_values.size > 0:
        peak_ratio = np.max(mid_values) / np.mean(mid_values)
    else:
        peak_ratio = 0

    # Moiré typically has mid_ratio > 0.65 AND sharp peaks > 3.5x mean
    return mid_ratio > 0.65 and peak_ratio > 3.5


def _detect_border_lines(gray, h, w):
    """
    Detect strong straight lines near image borders that suggest the edges
    of a paper/card are visible in the photo (photo-of-photo).

    Uses Canny + probabilistic Hough line transform.
    """
    # Only look at the outer 15% border region of the image
    border_h = int(0.15 * h)
    border_w = int(0.15 * w)

    # Create a mask for the border region
    mask = np.zeros((h, w), dtype=np.uint8)
    mask[:border_h, :] = 255       # top
    mask[h - border_h:, :] = 255   # bottom
    mask[:, :border_w] = 255       # left
    mask[:, w - border_w:] = 255   # right

    # Edge detection in the border region
    edges = cv2.Canny(gray, 50, 150)
    edges = cv2.bitwise_and(edges, mask)

    # Hough line detection
    min_line_length = min(h, w) * 0.25  # Lines must be at least 25% of image
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=80,
        minLineLength=int(min_line_length),
        maxLineGap=20
    )

    if lines is None:
        return False

    # Count lines that are roughly horizontal or vertical (within 15°)
    # These are characteristic of paper/card edges
    strong_border_lines = 0
    for line in lines:
        x1, y1, x2, y2 = line[0]
        if x2 == x1:
            angle = 90
        else:
            angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1)))

        # Check if line is approximately horizontal (0° or 180°) or vertical (90°)
        is_horizontal = angle < 15 or angle > 165
        is_vertical = 75 < angle < 105

        if is_horizontal or is_vertical:
            length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            if length > min_line_length:
                strong_border_lines += 1

    # 2 or more strong border lines suggest a visible paper/card edge
    return strong_border_lines >= 2
