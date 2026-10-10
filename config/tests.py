"""Comprobaciones de aislamiento de la configuración, sin conexión a PostgreSQL."""

import json
import os
from pathlib import Path
import subprocess
import sys

from django.test import SimpleTestCase


class ConfiguracionPruebasMixin:
    def import_settings(self, settings_module="config.settings_test", **overrides):
        env = os.environ.copy()
        # Valores ficticios sustituyen cualquier secreto local; no se imprimen.
        env.update({
            "DJANGO_SECRET_KEY": "clave-ficticia-solo-para-importar-configuracion",
            "DJANGO_DEBUG": "false",
            "POSTGRES_DB": "atencion_ciudadana",
            "POSTGRES_USER": "atencion_app",
            "POSTGRES_PASSWORD": "credencial-ficticia-del-proyecto",
            "TEST_POSTGRES_DB": "test_atencion_catalogos_revision",
            "TEST_POSTGRES_USER": "atencion_test",
            "TEST_POSTGRES_PASSWORD": "credencial-ficticia-exclusiva",
            "TEST_POSTGRES_HOST": "127.0.0.1",
            "TEST_POSTGRES_PORT": "5432",
        })
        env.update(overrides)
        script = """
import json
import importlib
import sys
from django.core.exceptions import ImproperlyConfigured
try:
    settings = importlib.import_module(sys.argv[1])
except ImproperlyConfigured as error:
    print(str(error))
    raise SystemExit(1)
database = settings.DATABASES['default']
assert database['PASSWORD'] == 'credencial-ficticia-exclusiva'
assert getattr(settings, 'MIGRATION_MODULES', {}) == {}
print(json.dumps({key: database[key] for key in ('NAME', 'USER', 'TEST')}))
"""
        return subprocess.run(
            [sys.executable, "-B", "-c", script, settings_module], env=env,
            cwd=Path(__file__).resolve().parent.parent,
            capture_output=True, text=True, timeout=10, check=False,
        )

    def test_rechaza_usuario_distinto_del_exclusivo(self):
        for user in ("atencion_app", "postgres", ""):
            with self.subTest(user=user):
                result = self.import_settings(TEST_POSTGRES_USER=user)
                self.assertEqual(result.returncode, 1)
                self.assertIn("usuario exclusivo", result.stdout)

    def test_password_de_pruebas_obligatorio_sin_alternativa_del_proyecto(self):
        for password in ("", "   "):
            with self.subTest(password=password):
                result = self.import_settings(TEST_POSTGRES_PASSWORD=password)
                self.assertEqual(result.returncode, 1)
                self.assertIn("TEST_POSTGRES_PASSWORD", result.stdout)


class ConfiguracionPruebasTests(ConfiguracionPruebasMixin, SimpleTestCase):
    def test_base_y_usuario_exclusivos_sin_migraciones(self):
        result = self.import_settings()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {
            "NAME": "test_atencion_catalogos_revision",
            "USER": "atencion_test",
            "TEST": {"NAME": "test_atencion_catalogos_revision", "MIGRATE": False},
        })

    def test_rechaza_base_del_proyecto_o_cualquier_otro_nombre(self):
        for name in (
            "atencion_ciudadana", "test_atencion_catalogos_migraciones",
            "test_atencion_catalogos_otro", "", "postgres",
        ):
            with self.subTest(name=name):
                result = self.import_settings(TEST_POSTGRES_DB=name)
                self.assertEqual(result.returncode, 1)
                self.assertIn("base exclusiva", result.stdout)
        result = self.import_settings(POSTGRES_DB="test_atencion_catalogos_revision")
        self.assertEqual(result.returncode, 1)
        self.assertIn("base exclusiva", result.stdout)


class ConfiguracionMigracionesTests(ConfiguracionPruebasMixin, SimpleTestCase):
    def import_settings(self, **overrides):
        return super().import_settings("config.settings_test_migrations", **overrides)

    def test_base_y_usuario_exclusivos_con_migraciones(self):
        result = self.import_settings()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {
            "NAME": "test_atencion_catalogos_migraciones",
            "USER": "atencion_test",
            "TEST": {"NAME": "test_atencion_catalogos_migraciones", "MIGRATE": True},
        })

    def test_rechaza_coincidencia_con_base_del_proyecto(self):
        result = self.import_settings(POSTGRES_DB="test_atencion_catalogos_migraciones")
        self.assertEqual(result.returncode, 1)
        self.assertIn("base exclusiva", result.stdout)

    def test_nombre_fijo_no_admite_redireccion_por_entorno(self):
        # Ningún valor de la variable de la configuración anterior redirige la nueva.
        for name in (
            "test_atencion_catalogos_revision", "atencion_ciudadana",
            "test_atencion_catalogos_otro", "", "postgres",
        ):
            with self.subTest(name=name):
                result = self.import_settings(TEST_POSTGRES_DB=name)
                self.assertEqual(result.returncode, 0, result.stderr)
                database = json.loads(result.stdout)
                self.assertEqual(database["NAME"], "test_atencion_catalogos_migraciones")
                self.assertEqual(database["TEST"]["NAME"], database["NAME"])
