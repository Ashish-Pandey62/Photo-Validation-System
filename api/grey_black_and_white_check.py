from .models import Config

def is_grey(img):
    config = Config.objects.all()[0]
    greyness_threshold = config.greyness_threshold
    w, h, channel = img.shape
    for i in range(w):
        for j in range(h):
            r, g, b = img[i][j]

            if abs(int(r)-int(g)) > greyness_threshold or abs(int(r)-int(g)) > greyness_threshold or abs(int(r)-int(g)) > greyness_threshold:
                return False
    return True