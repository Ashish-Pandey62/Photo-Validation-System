from threading import Lock
from .models import Config

_config_cache = None
_lock = Lock()


def get_config():
    global _config_cache

    if _config_cache is None:
        with _lock:
            if _config_cache is None:  # double-check
                config = Config.objects.first()
                if config is None:
                    raise RuntimeError("Config table is empty.")
                _config_cache = config

    return _config_cache