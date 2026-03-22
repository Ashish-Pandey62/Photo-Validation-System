import dlib
import cv2
import logging
from .config_utils import get_cached_config


def detect_faces(image):
    """Detect faces using dlib's HOG frontal face detector with upsampling."""
    face_detector = dlib.get_frontal_face_detector()
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Upsample once for better detection of smaller / slightly angled faces
    faces = face_detector(gray_image, 1)
    return faces


def calculate_head_percentage(face, image):
    """Calculate the percentage of the image area occupied by the face."""
    face_area = face.width() * face.height()
    image_area = image.shape[0] * image.shape[1]
    if image_area == 0:
        return 0
    return (face_area / image_area) * 100


def valid_head_check(image, config=None):
    """
    Validate that exactly one face is detected and its size is within the
    configured acceptable range.

    Returns (is_valid: bool, head_percent: float).
    Special sentinel values:
        101 → no face detected
        102 → multiple faces detected
    """
    try:
        if config is None:
            config = get_cached_config()
        min_pct = getattr(config, "min_head_percent", 10)
        max_pct = getattr(config, "max_head_percent", 80)
    except Exception:
        min_pct, max_pct = 10, 80

    faces = detect_faces(image)
    num_faces = len(faces)

    if num_faces == 0:
        return False, 101
    if num_faces > 1:
        return False, 102

    face = faces[0]
    head_percentage = calculate_head_percentage(face, image)

    if min_pct < head_percentage < max_pct:
        return True, head_percentage
    return False, head_percentage


def detect_eyes(image, config=None):
    """
    Check whether eyes are visible in the image.

    Returns True if eyes ARE visible (good), False if NOT visible (bad).

    Strategy:
    1. Detect the face first.
    2. Search for eyes ONLY within the face ROI (upper half of face box)
       using haarcascade — this dramatically reduces false positives from
       buttons, patterns, etc. elsewhere in the image.

    The old implementation ran haarcascade on the entire image and returned
    an inverted boolean, causing widespread misclassification.
    """
    try:
        faces = detect_faces(image)
        if len(faces) == 0:
            # No face → can't check eyes; let head_check handle this
            return True  # Don't double-penalise

        face = faces[0]
        x, y, w, h = face.left(), face.top(), face.width(), face.height()

        # Clamp to image bounds
        img_h, img_w = image.shape[:2]
        x = max(0, x)
        y = max(0, y)
        x2 = min(img_w, x + w)
        y2 = min(img_h, y + h)

        # Use the upper 60 % of the face box — eyes are in the top portion
        eye_region_bottom = y + int(0.6 * (y2 - y))
        face_roi = image[y:eye_region_bottom, x:x2]

        if face_roi.size == 0:
            return True

        gray_roi = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)

        eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_eye.xml"
        )
        eyes = eye_cascade.detectMultiScale(
            gray_roi,
            scaleFactor=1.1,
            minNeighbors=3,
            minSize=(int(w * 0.08), int(w * 0.08)),
        )

        # At least one eye detected → eyes are visible
        return len(eyes) >= 1

    except Exception as e:
        logging.debug(f"Error in detect_eyes: {e}")
        # On error, don't penalise — return True
        return True
