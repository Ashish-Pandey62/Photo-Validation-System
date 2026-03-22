import cv2
import numpy as np
import logging
from .config_utils import get_cached_config


def check_text_in_image(image, config=None):
    """
    Detect text, watermarks, or stamps in a photo using OpenCV's MSER
    (Maximally Stable Extremal Regions) detector — no external OCR needed.

    The face region is excluded from the search to avoid false positives
    from facial features.

    Returns (has_text: bool, details: dict)
    """
    try:
        if config is None:
            config = get_cached_config()
        text_region_threshold = getattr(config, "text_region_threshold", 8)
    except Exception:
        text_region_threshold = 8

    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape

        # Create a mask excluding the face region (avoid false positives)
        exclude_mask = _get_face_exclusion_mask(image, h, w)

        text_region_count = _detect_text_regions(gray, exclude_mask, h, w)

        has_text = text_region_count > text_region_threshold

        return has_text, {
            "text_region_count": text_region_count,
            "text_region_threshold": text_region_threshold,
        }
    except Exception as e:
        logging.debug(f"Error in text detection: {e}")
        return False, {"error": str(e)}


def _get_face_exclusion_mask(image, h, w):
    """
    Create a binary mask where face regions are blocked out (0 = exclude).
    This prevents MSER from picking up facial features as "text".
    """
    mask = np.ones((h, w), dtype=np.uint8) * 255

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)

    for (fx, fy, fw, fh) in faces:
        # Expand face region by 20% to cover hair/neck
        expand = int(0.2 * max(fw, fh))
        x1 = max(0, fx - expand)
        y1 = max(0, fy - expand)
        x2 = min(w, fx + fw + expand)
        y2 = min(h, fy + fh + expand)
        mask[y1:y2, x1:x2] = 0

    return mask


def _detect_text_regions(gray, exclude_mask, h, w):
    """
    Detect text-like regions using MSER + geometric filtering.

    MSER finds stable connected regions; text characters have specific
    aspect ratios, sizes, and are typically not too large or too small.
    """
    mser = cv2.MSER_create()

    # Tune MSER parameters for text detection
    mser.setMinArea(60)
    mser.setMaxArea(int(h * w * 0.01))  # max 1% of image per region
    mser.setDelta(5)

    # Detect regions
    regions, _ = mser.detectRegions(gray)

    image_area = h * w
    text_like_count = 0

    for region in regions:
        # Bounding box of the region
        x, y, rw, rh = cv2.boundingRect(region)

        # Skip if the region center is in the excluded (face) area
        cx, cy = x + rw // 2, y + rh // 2
        if 0 <= cy < h and 0 <= cx < w and exclude_mask[cy, cx] == 0:
            continue

        area = cv2.contourArea(region) if len(region) >= 5 else rw * rh

        # --- Geometric filters for text-like regions ---

        # 1. Size: not too small (noise) or too large (background blob)
        if area < 80 or area > image_area * 0.005:
            continue

        # 2. Aspect ratio: text characters are typically 0.2 to 5.0
        if rh == 0:
            continue
        aspect = rw / rh
        if aspect < 0.15 or aspect > 6.0:
            continue

        # 3. Extent (fill ratio): text chars fill their bounding box ~30-90%
        bbox_area = rw * rh
        if bbox_area == 0:
            continue
        extent = area / bbox_area
        if extent < 0.2 or extent > 0.95:
            continue

        # 4. Size relative to image: single chars are small
        if rw > w * 0.15 or rh > h * 0.15:
            continue

        text_like_count += 1

    return text_like_count
