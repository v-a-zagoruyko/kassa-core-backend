import threading
import pytest
from django.test.utils import setup_databases, teardown_databases


SQLITE_DB = {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": ":memory:",
    "ATOMIC_REQUESTS": False,
    "AUTOCOMMIT": True,
    "CONN_MAX_AGE": 0,
    "CONN_HEALTH_CHECKS": False,
    "OPTIONS": {},
    "TIME_ZONE": None,
    "USER": "",
    "PASSWORD": "",
    "HOST": "",
    "PORT": "",
    "TEST": {
        "CHARSET": None,
        "COLLATION": None,
        "MIGRATE": True,
        "MIRROR": None,
        "NAME": ":memory:",
    },
}


@pytest.fixture(scope="session")
def django_db_setup(django_test_environment, django_db_blocker):
    """Override DB to SQLite in-memory for orders tests (no Postgres in this env)."""
    from django.conf import settings
    from django.db import connections

    settings.DATABASES["default"] = SQLITE_DB.copy()
    # Clear internal thread-local cache so Django creates fresh SQLite wrappers.
    connections._connections = threading.local()

    with django_db_blocker.unblock():
        old_config = setup_databases(verbosity=0, interactive=False)
    yield
    with django_db_blocker.unblock():
        teardown_databases(old_config, verbosity=0)
