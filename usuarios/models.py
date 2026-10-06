from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import UsuarioManager


class Usuario(AbstractUser):
    class Rol(models.TextChoices):
        ADMINISTRADOR = "ADMINISTRADOR", "Administrador"
        RECEPCION = "RECEPCION", "Recepción"
        OPERADOR = "OPERADOR", "Operador"

    rol = models.CharField("rol", max_length=13, choices=Rol.choices)

    objects = UsuarioManager()

    # Conserva los campos solicitados por AbstractUser y añade el rol sin default.
    REQUIRED_FIELDS = [*AbstractUser.REQUIRED_FIELDS, "rol"]

    class Meta(AbstractUser.Meta):
        constraints = [
            models.CheckConstraint(
                condition=models.Q(rol__in=["ADMINISTRADOR", "RECEPCION", "OPERADOR"]),
                name="usuarios_usuario_rol_valido",
            ),
        ]

    def save(self, *args, **kwargs):
        # save() no ejecuta full_clean(); valida solo el rol sin consultar la BD.
        self._meta.get_field("rol").clean(self.rol, self)
        return super().save(*args, **kwargs)
