import os


ENVIRONMENT = os.environ.get("ENVIRONMENT", "dev")

if ENVIRONMENT == "prod":
    from .prod import *
else:
    from .dev import *
