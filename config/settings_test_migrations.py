"""Pruebas con migraciones reales sobre una base exclusiva; usar --keepdb.

El nombre es fijo: TEST_POSTGRES_DB sigue reservado a settings_test.py.
Las credenciales TEST_POSTGRES_* son las de pruebas, nunca las de la app.
"""

import os

from django.core.exceptions import ImproperlyConfigured

from .settings import *  # noqa: F403
from .settings import required_env

test_database = "test_atencion_catalogos_migraciones"
test_user = os.environ.get("TEST_POSTGRES_USER", "atencion_test")
if test_database == DATABASES["default"]["NAME"]:  # noqa: F405
    raise ImproperlyConfigured(
        "Las pruebas requieren la base exclusiva test_atencion_catalogos_migraciones."
    )
if test_user != "atencion_test":
    raise ImproperlyConfigured("Las pruebas requieren el usuario exclusivo atencion_test.")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": test_database,
        "USER": test_user,
        "PASSWORD": required_env("TEST_POSTGRES_PASSWORD"),
        "HOST": os.environ.get("TEST_POSTGRES_HOST", "127.0.0.1"),
        "PORT": os.environ.get("TEST_POSTGRES_PORT", "5432"),
        "TEST": {"NAME": test_database, "MIGRATE": True},
    },
}

# Django descubre y ejecuta los archivos de migración de todas las aplicaciones.
MIGRATION_MODULES = {}
