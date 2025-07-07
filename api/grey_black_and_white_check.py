from .models import Config

def is_grey(img):
    try:
        config = Config.objects.first()
        if not config:
            greyness_threshold = 0  # default value
        else:
            greyness_threshold = config.greyness_threshold
        
        w, h, channel = img.shape
        for i in range(w):
            for j in range(h):
                r, g, b = img[i][j]

                if abs(int(r)-int(g)) > greyness_threshold or abs(int(r)-int(b)) > greyness_threshold or abs(int(g)-int(b)) > greyness_threshold:
                    return False
        return True
    except Exception as e:
        print(f"Error in is_grey: {e}")
        return False