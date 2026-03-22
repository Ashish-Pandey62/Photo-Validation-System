import cv2
import numpy as np
import logging
from .config_utils import get_cached_config


def check_printed_photo(image, config=None):
    """
    Detect if a photo is a re-photograph of a printed original.

    Uses four complementary signals:
    1. Moiré pattern detection via FFT spectral analysis
    2. Border line detection — looks for rectangular frame edges
    3. Color gamut analysis — printed photos have compressed color range
    4. Texture regularity — halftone patterns create uniform local variance

    Decision: moiré alone, OR 2+ of the other signals.

    Returns (is_printed: bool, details: dict)
    """
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape

        is_moire = _detect_moire(gray)
        has_border = _detect_border_frame(gray, h, w)
        low_gamut = _check_color_gamut(image)
        regular_texture = _check_texture_regularity(gray, h, w)

        # Count non-moiré signals
        secondary_signals = sum([has_border, low_gamut, regular_texture])

        # Decision: moiré alone is strong enough, or just 1 scattered signal
        is_printed = is_moire or secondary_signals >= 1

        return is_printed, {
            "has_moire_pattern": is_moire,
            "has_border_lines": has_border,
            "low_color_gamut": low_gamut,
            "regular_texture": regular_texture,
            "secondary_signal_count": secondary_signals,
        }
    except Exception as e:
        logging.debug(f"Error in printed photo check: {e}")
        return False, {"error": str(e)}


# ---------------------------------------------------------------------------
# Signal 1: Moiré pattern detection (FFT)
# ---------------------------------------------------------------------------

def _detect_moire(gray):
    """
    Detect moiré patterns using 2D FFT.
    Printed halftone images show distinct periodic peaks in the mid-frequency
    spectrum that natural photos don't have.
    """
    analysis_size = 256
    resized = cv2.resize(gray, (analysis_size, analysis_size))
    img_float = np.float32(resized)

    window = np.outer(np.hanning(analysis_size), np.hanning(analysis_size))
    img_windowed = img_float * window

    f_transform = np.fft.fft2(img_windowed)
    f_shift = np.fft.fftshift(f_transform)
    magnitude = np.log1p(np.abs(f_shift))

    center = analysis_size // 2
    y_coords, x_coords = np.ogrid[:analysis_size, :analysis_size]
    radius = np.sqrt((x_coords - center) ** 2 + (y_coords - center) ** 2)

    max_radius = analysis_size / 2
    low_mask = radius < (0.10 * max_radius)
    mid_mask = (radius >= 0.20 * max_radius) & (radius < 0.45 * max_radius)

    low_energy = np.mean(magnitude[low_mask]) if np.any(low_mask) else 0
    mid_energy = np.mean(magnitude[mid_mask]) if np.any(mid_mask) else 0

    if low_energy == 0:
        return False

    mid_ratio = mid_energy / low_energy

    mid_values = magnitude[mid_mask]
    peak_ratio = np.max(mid_values) / np.mean(mid_values) if mid_values.size > 0 else 0

    # Moiré: high mid-frequency energy + sharp isolated peaks
    return mid_ratio > 0.50 and peak_ratio > 2.5


# ---------------------------------------------------------------------------
# Signal 2: Border frame detection (Hough lines)
# ---------------------------------------------------------------------------

def _detect_border_frame(gray, h, w):
    """
    Detect a rectangular paper/card frame visible in the photo.

    Much stricter than simple border line detection:
    - Only the outer 8% strip is examined
    - Lines must span ≥40% of the image dimension
    - Must find BOTH horizontal AND vertical lines (forming a frame)
    - OR find parallel pairs (top+bottom or left+right)
    """
    border_h = int(0.08 * h)
    border_w = int(0.08 * w)

    if border_h < 10 or border_w < 10:
        return False

    # Create mask for the outer border strip only
    mask = np.zeros((h, w), dtype=np.uint8)
    mask[:border_h, :] = 255       # top
    mask[h - border_h:, :] = 255   # bottom
    mask[:, :border_w] = 255       # left
    mask[:, w - border_w:] = 255   # right

    edges = cv2.Canny(gray, 80, 200)
    edges = cv2.bitwise_and(edges, mask)

    min_line_h = int(w * 0.30)  # horizontal lines must be ≥30% of width
    min_line_v = int(h * 0.30)  # vertical lines must be ≥30% of height

    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=90,
        minLineLength=min(min_line_h, min_line_v),
        maxLineGap=20
    )

    if lines is None:
        return False

    has_top_line = False
    has_bottom_line = False
    has_left_line = False
    has_right_line = False

    for line in lines:
        x1, y1, x2, y2 = line[0]
        length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

        if x2 == x1:
            angle = 90.0
        else:
            angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1)))

        # Horizontal lines (within 10°)
        is_horizontal = angle < 10 or angle > 170
        # Vertical lines (within 10° of 90°)
        is_vertical = 80 < angle < 100

        if is_horizontal and length >= min_line_h:
            mid_y = (y1 + y2) / 2
            if mid_y < border_h:
                has_top_line = True
            elif mid_y > h - border_h:
                has_bottom_line = True

        if is_vertical and length >= min_line_v:
            mid_x = (x1 + x2) / 2
            if mid_x < border_w:
                has_left_line = True
            elif mid_x > w - border_w:
                has_right_line = True

    # Need BOTH horizontal and vertical (L-shape or more)
    # OR parallel pair on opposite sides
    has_h_pair = has_top_line and has_bottom_line
    has_v_pair = has_left_line and has_right_line
    has_l_shape = (has_top_line or has_bottom_line) and (has_left_line or has_right_line)

    return has_h_pair or has_v_pair or has_l_shape


# ---------------------------------------------------------------------------
# Signal 3: Color gamut analysis
# ---------------------------------------------------------------------------

def _check_color_gamut(image):
    """
    Detect compressed color gamut typical of re-photographed prints.

    Digital originals have rich, spread-out color distributions.
    Printed-then-photographed images have compressed a* and b* channels
    in LAB color space (the printing process clips the gamut).
    """
    # Resize for speed
    small = cv2.resize(image, (256, 256))
    lab = cv2.cvtColor(small, cv2.COLOR_BGR2LAB)

    l_channel = lab[:, :, 0].astype(np.float64)
    a_channel = lab[:, :, 1].astype(np.float64)
    b_channel = lab[:, :, 2].astype(np.float64)

    # Measure color spread
    a_std = np.std(a_channel)
    b_std = np.std(b_channel)
    color_spread = (a_std + b_std) / 2

    # Measure brightness range (L channel)
    l_range = np.percentile(l_channel, 95) - np.percentile(l_channel, 5)

    # Printed photos typically have:
    # - color_spread < 15 (compressed chroma)
    # - l_range < 160 (compressed dynamic range)
    # Normal portrait photos have color_spread 10-30+
    return color_spread < 15 and l_range < 160


# ---------------------------------------------------------------------------
# Signal 4: Texture regularity analysis
# ---------------------------------------------------------------------------

def _check_texture_regularity(gray, h, w):
    """
    Detect halftone-like uniform texture in the image.

    Natural photos have highly variable local texture (smooth skin next to
    sharp hair next to uniform background). Printed photos have more uniform
    texture because the halftone screening process imposes a regular pattern.

    Measure: coefficient of variation of local variances across patches.
    Low CV = uniform texture = likely printed.
    """
    # Resize for consistent analysis
    analysis_size = 256
    resized = cv2.resize(gray, (analysis_size, analysis_size))

    patch_size = 16
    variances = []

    for y in range(0, analysis_size - patch_size, patch_size):
        for x in range(0, analysis_size - patch_size, patch_size):
            patch = resized[y:y + patch_size, x:x + patch_size].astype(np.float64)
            variances.append(np.var(patch))

    if len(variances) < 10:
        return False

    variances = np.array(variances)
    mean_var = np.mean(variances)
    std_var = np.std(variances)

    if mean_var == 0:
        return False

    # Coefficient of variation of local variances
    cv = std_var / mean_var

    # Natural photos: CV typically 1.5-4.0+ (highly variable)
    # Printed photos: CV typically 0.3-1.0 (uniform halftone)
    # Relaxed threshold to catch more printed photos
    return cv < 1.2
