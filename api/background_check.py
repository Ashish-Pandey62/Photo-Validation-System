import numpy as np
from .config_utils import get_cached_config


def background_check(image, config=None):
    """
    Validate that the image has a reasonably uniform background.

    The check samples thin border strips (top, left, right) — regions that
    should contain only background — and measures how uniform those pixels
    are via standard deviation of luminance.

    KEY CHANGE: the old brightness-floor requirement (`avg_brightness >=
    min_brightness`) has been removed.  A dark-grey or blue background is
    perfectly valid; what matters is *uniformity*, not absolute brightness.
    """
    try:
        if config is None:
            config = get_cached_config()
        uniformity_std = getattr(config, "bg_uniformity_threshold", 35)
    except Exception:
        uniformity_std = 35

    h, w = image.shape[:2]
    if h < 10 or w < 10:
        # Image too small to meaningfully sample
        return True

    # === Sample ONLY true-background borders ===

    # 1) TOP strip — thin horizontal band
    top_h = max(2, int(0.06 * h))
    top = image[:top_h, :]

    # 2) LEFT / RIGHT vertical strips
    #    Skip top 3 % (hair) and bottom 25 % (clothing) for cleaner samples.
    y0 = int(0.03 * h)
    y1 = int(0.75 * h)
    side_w = max(2, int(0.06 * w))
    left  = image[y0:y1, :side_w]
    right = image[y0:y1, w - side_w:]

    # Stack all sampled pixels into (N, 3)
    background_pixels = np.vstack([
        top.reshape(-1, 3),
        left.reshape(-1, 3),
        right.reshape(-1, 3),
    ])

    if background_pixels.size == 0:
        return True

    # Convert to perceptual luminance (BT.601 weights, OpenCV uses BGR order)
    y = (0.114 * background_pixels[:, 0]
       + 0.587 * background_pixels[:, 1]
       + 0.299 * background_pixels[:, 2])

    # Trim extreme 5 % tails to resist hair / clothing contamination
    if y.size > 500:
        lo, hi = np.percentile(y, [5, 95])
        y = y[(y >= lo) & (y <= hi)]

    if y.size == 0:
        return True

    std_brightness = float(np.std(y))

    # Pass if the background is reasonably uniform (low std deviation).
    return std_brightness < uniformity_std
