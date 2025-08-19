import numpy as np
from .models import Config

import numpy as np
import cv2
from .models import Config

def background_check(image, config=None):
    # --- thresholds still fully dynamic ---
    try:
        if config is None:
            config = Config.objects.first()
        min_brightness = getattr(config, "bgcolor_threshold", 30)           # 0..255 scale
        uniformity_std = getattr(config, "bg_uniformity_threshold", 40)     # std on 0..255
    except Exception:
        min_brightness, uniformity_std = 30, 40

    h, w, _ = image.shape

    # === sample ONLY true-background borders ===
    # 1) TOP: thin strip (avoid being too thin to hit JPEG ringing)
    top_h = max(2, int(0.06 * h))
    top = image[:top_h, :, :]

    # 2) LEFT / RIGHT: thin vertical strips, skipping bottom 20% to avoid clothes
    #    and skipping the very top 3% where hair can intrude in some crops.
    y0 = int(0.03 * h)         # skip very top
    y1 = int(0.80 * h)         # skip bottom 20%
    side_w = max(2, int(0.06 * w))
    left  = image[y0:y1, :side_w, :]
    right = image[y0:y1, w - side_w:, :]

    # Stack and (optionally) subsample for speed without changing behavior
    background_pixels = np.vstack([
        top.reshape(-1, 3),
        left.reshape(-1, 3),
        right.reshape(-1, 3)
    ])
    if background_pixels.size == 0:
        return True

    # Convert to luminance (perceptual brightness), still O(N)
    # Keeps your semantics; just more accurate than plain mean of channels
    y = (0.114 * background_pixels[:, 0] +
         0.587 * background_pixels[:, 1] +
         0.299 * background_pixels[:, 2])

    # Robustify uniformity: drop extreme 5% tails to resist hair/clothes contamination
    # This is cheap and vectorized; no big processing cost.
    if y.size > 2000:                          # only do trimming when we actually have many samples
        lo, hi = np.percentile(y, [5, 95])
        y = y[(y >= lo) & (y <= hi)]

    avg_brightness = float(np.mean(y))
    std_brightness = float(np.std(y))

    # Pass if background is bright enough (not dark) AND reasonably uniform.
    return (avg_brightness >= min_brightness) and (std_brightness < uniformity_std)

