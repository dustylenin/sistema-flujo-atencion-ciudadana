from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.management.commands.createsuperuser import Command
from django.core.exceptions import ValidationError
from django.db import models
from django.test import SimpleTestCase

from .models import Usuario


class UsuarioTests(SimpleTestCase):
    """Pruebas sin BD: los guardados válidos se interceptan y no crean cuentas."""

    def test_modelo_configurado_y_username_heredado(self):
        self.assertIs(get_user_model(), Usuario)
        self.assertEqual(Usuario.USERNAME_FIELD, "username")
        self.assertTrue(Usuario._meta.get_field("username").unique)
        self.assertFalse(Usuario._meta.get_field("rol").has_default())
        self.assertFalse(Usuario._meta.get_field("rol").blank)
        self.assertFalse(Usuario._meta.get_field("rol").null)

    def test_rol_invalido_se_rechaza_antes_de_guardar(self):
        for rol in (None, "", " ", "ADMIN", "administrador"):
            with self.subTest(rol=rol), patch.object(models.Model, "save") as save:
                with self.assertRaises(ValidationError):
                    Usuario(username="prueba", rol=rol).save()
                save.assert_not_called()

    def test_guardado_directo_sin_rol_se_rechaza(self):
        with patch.object(models.Model, "save") as save:
            with self.assertRaises(ValidationError):
                Usuario(username="prueba").save()
            save.assert_not_called()

    def test_manager_exige_rol_explicito(self):
        for method in (Usuario.objects.create_user, Usuario.objects.create_superuser):
            with self.subTest(method=method.__name__):
                with self.assertRaises(TypeError):
                    method(username="prueba")
                for rol in (None, "", " ", "OTRO"):
                    with self.subTest(rol=rol), self.assertRaises(ValidationError):
                        method(username="prueba", rol=rol)

    def test_roles_no_determinan_indicadores_y_password_se_hashea(self):
        for rol in Usuario.Rol:
            with self.subTest(rol=rol), patch.object(models.Model, "save"):
                user = Usuario.objects.create_user(
                    username="prueba", password="clave-de-prueba", rol=rol
                )
                self.assertEqual(user.rol, rol)
                self.assertTrue(user.is_active)
                self.assertFalse(user.is_staff)
                self.assertFalse(user.is_superuser)
                self.assertNotEqual(user.password, "clave-de-prueba")
                self.assertTrue(user.check_password("clave-de-prueba"))
                self.assertEqual(user.email, "")

    def test_superusuario_tecnico_conserva_el_rol_indicado(self):
        for rol in Usuario.Rol:
            with self.subTest(rol=rol), patch.object(models.Model, "save"):
                user = Usuario.objects.create_superuser(username="prueba", rol=rol)
                self.assertEqual(user.rol, rol)
                self.assertTrue(user.is_staff)
                self.assertTrue(user.is_superuser)

    def test_cambiar_indicadores_no_cambia_rol(self):
        user = Usuario(username="prueba", rol=Usuario.Rol.RECEPCION)
        with patch.object(models.Model, "save"):
            user.is_active = False
            user.is_staff = True
            user.is_superuser = True
            user.save()
        self.assertEqual(user.rol, Usuario.Rol.RECEPCION)
        self.assertFalse(user.is_active)

    def test_createsuperuser_incluye_opcion_rol(self):
        # Solo se construye el parser: no se ejecuta el comando ni su consulta.
        parser = Command().create_parser("manage.py", "createsuperuser")
        options = parser.parse_args(["--username", "prueba", "--rol", "OPERADOR"])
        self.assertEqual(options.rol, "OPERADOR")
        self.assertIn("rol", Usuario.REQUIRED_FIELDS)
