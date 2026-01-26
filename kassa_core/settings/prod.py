from .base import *


DEBUG = False

STATIC_ROOT = BASE_DIR / "staticfiles"

LOGGING["handlers"]["file"] = {
    "class": "logging.handlers.RotatingFileHandler",
    "filename": "/app/logs/kassa_core.log",
    "maxBytes": 1024 * 1024 * 10,
    "backupCount": 5,
    "formatter": "json",
}

LOGGING["root"]["handlers"].append("file")
