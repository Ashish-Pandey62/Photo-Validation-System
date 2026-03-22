import cv2
import numpy as np
import logging
from .config_utils import get_cached_config


def check_text_in_image(image, config=None):
    """
    Detect text, watermarks, or stamps in a photo using OpenCV's MSER
    with strict geometric filtering and spatial clustering.

    Only flags the image if text-like regions appear in clusters (actual
    text forms lines/groups; scattered blobs from faces/texture do not).

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

        # Create a mask excluding the face region (avoid false positives)
        exclude_mask = _get_face_exclusion_mask(image, h, w)

        text_cluster_count = _detect_text_clusters(gray, exclude_mask, h, w)

        has_text = text_cluster_count > text_region_threshold

        return has_text, {
            "text_region_count": text_cluster_count,
            "text_region_threshold": text_region_threshold,
        }
    except Exception as e:
        logging.debug(f"Error in text detection: {e}")
        return False, {"error": str(e)}


def _get_face_exclusion_mask(image, h, w):
    """
    Create a binary mask where face regions AND the center of the image
    are blocked out (0 = exclude). For portrait photos, the subject
    occupies the middle, so we exclude a generous center region too.
    """
    mask = np.ones((h, w), dtype=np.uint8) * 255

    # Exclude the center 60% of the image (where the subject/face is)
    # This dramatically reduces false positives from skin, hair, clothing
    center_margin_h = int(0.2 * h)
    center_margin_w = int(0.2 * w)
    mask[center_margin_h:h - center_margin_h, center_margin_w:w - center_margin_w] = 0

    # Also detect and exclude face regions with generous padding
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)

    for (fx, fy, fw, fh) in faces:
        # Expand face region by 40% to cover hair, neck, shoulders
        expand = int(0.4 * max(fw, fh))
        x1 = max(0, fx - expand)
        y1 = max(0, fy - expand)
        x2 = min(w, fx + fw + expand)
        y2 = min(h, fy + fh + expand)
        mask[y1:y2, x1:x2] = 0

    return mask


def _detect_text_clusters(gray, exclude_mask, h, w):
    """
    Detect text-like regions using MSER + strict geometric filtering +
    spatial clustering.

    Real text has specific properties:
    - Characters have consistent size within a line
    - Characters are roughly aligned horizontally or vertically
    - Characters appear in groups, not scattered randomly

    We count regions that pass ALL filters AND appear in spatial clusters.
    """
    mser = cv2.MSER_create()

    # Conservative MSER parameters
    mser.setMinArea(100)                      # ignore tiny blobs
    mser.setMaxArea(int(h * w * 0.005))       # max 0.5% of image
    mser.setDelta(8)                          # higher delta = more stable regions only

    # Detect regions
    regions, _ = mser.detectRegions(gray)

    image_area = h * w
    candidate_centers = []

    for region in regions:
        # Bounding box of the region
        x, y, rw, rh = cv2.boundingRect(region)

        # Skip if the region center is in the excluded area
        cx, cy = x + rw // 2, y + rh // 2
        if 0 <= cy < h and 0 <= cx < w and exclude_mask[cy, cx] == 0:
            continue

        area = cv2.contourArea(region) if len(region) >= 5 else rw * rh

        # --- Strict geometric filters ---

        # 1. Size: text characters are typically 100-2000 pixels in a photo
        if area < 100 or area > min(image_area * 0.003, 3000):
            continue

        # 2. Aspect ratio: text characters are between 0.2 and 3.0
        #    (stricter than before to reject elongated blobs)
        if rh == 0:
            continue
        aspect = rw / rh
        if aspect < 0.2 or aspect > 3.0:
            continue

        # 3. Bounding box not too big (single char is small)
        if rw > w * 0.08 or rh > h * 0.08:
            continue

        # 4. Fill ratio: text chars fill their bounding box 30-85%
        bbox_area = rw * rh
        if bbox_area == 0:
            continue
        extent = area / bbox_area
        if extent < 0.25 or extent > 0.85:
            continue

        # 5. Compactness: text chars are compact, not fractal shapes
        perimeter = cv2.arcLength(region, True) if len(region) >= 5 else 2 * (rw + rh)
        if perimeter > 0:
            compactness = area / (perimeter * perimeter)
            if compactness < 0.01:  # very non-compact = not text
                continue

        candidate_centers.append((cx, cy))

    if len(candidate_centers) < 3:
        return 0

    # --- Spatial clustering ---
    # Real text forms lines. Check if candidates cluster into horizontal/vertical groups.
    # A cluster = 3+ regions within a narrow horizontal or vertical band.
    clustered_count = _count_clustered_regions(candidate_centers, h, w)

    return clustered_count


def _count_clustered_regions(centers, h, w):
    """
    Count how many candidate text regions appear in spatial clusters
    (horizontal bands), which is characteristic of actual text lines.

    Scattered random blobs (from texture/edges) won't form clusters.
    """
    if len(centers) < 3:
        return 0

    centers = np.array(centers)
    band_height = max(h * 0.03, 15)  # cluster band = 3% of image height

    # Sort by y-coordinate
    sorted_by_y = centers[centers[:, 1].argsort()]

    clustered = 0
    i = 0
    while i < len(sorted_by_y):
        # Find all points within band_height of current y
        cy = sorted_by_y[i, 1]
        band_members = []
        j = i
        while j < len(sorted_by_y) and sorted_by_y[j, 1] - cy <= band_height:
            band_members.append(sorted_by_y[j])
            j += 1

        if len(band_members) >= 3:
            # This band has 3+ candidates — likely a text line
            clustered += len(band_members)

        i = j if j > i else i + 1

    return clustered
