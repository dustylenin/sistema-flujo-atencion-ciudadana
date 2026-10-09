"""Pruebas sobre una base exclusiva preparada previamente; usar --keepdb.

MIGRATE=False crea las tablas desde los modelos: no verifica las migraciones.
El usuario de pruebas no necesita CREATEDB. Nunca se usan credenciales de la app.
"""

import os

from django.core.exceptions import ImproperlyConfigured

from .settings import *  # noqa: F403
from .settings import required_env

test_database = os.environ.get("TEST_POSTGRES_DB", "test_atencion_catalogos_revision")
test_user = os.environ.get("TEST_POSTGRES_USER", "atencion_test")
if (
    test_database != "test_atencion_catalogos_revision"
    or test_database == DATABASES["default"]["NAME"]  # noqa: F405
):
    raise ImproperlyConfigured("Las pruebas requieren la base exclusiva test_atencion_catalogos_revision.")
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
        "TEST": {"NAME": test_database, "MIGRATE": False},
    },
}
