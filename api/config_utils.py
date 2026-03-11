from functools import lru_cache

from .models import Config

DEFAULT_CONFIG = {
    "min_height": 100,
    "max_height": 2000,
    "min_width": 100,
    "max_width": 2000,
    "min_size": 10,
    "max_size": 5000,
    "is_jpg": True,
    "is_png": True,
    "is_jpeg": True,
    "bgcolor_threshold": 40,
    "bg_uniformity_threshold": 25,
    "blurness_threshold": 30,
    "pixelated_threshold": 100,
    "greyness_threshold": 5,
    "symmetry_threshold": 35,
}


def get_or_create_config():
    config = Config.objects.first()
    if config:
        return config
    return Config.objects.create(**DEFAULT_CONFIG)


@lru_cache(maxsize=1)
def get_cached_config():
    return get_or_create_config()


def warm_config_cache():
    return get_cached_config()


def clear_config_cache():
    get_cached_config.cache_clear()
