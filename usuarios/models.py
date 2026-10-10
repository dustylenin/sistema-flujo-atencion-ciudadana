from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import DatabaseError, models, router, transaction

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
        base_manager_name = "objects"
        default_manager_name = "objects"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(rol__in=["ADMINISTRADOR", "RECEPCION", "OPERADOR"]),
                name="usuarios_usuario_rol_valido",
            ),
        ]

    def save(self, *args, force_insert=False, force_update=False, using=None, update_fields=None):
        if args:
            force_insert, force_update, using, update_fields = self._parse_save_params(
                *args, method_name="save", force_insert=force_insert,
                force_update=force_update, using=using, update_fields=update_fields,
            )
        using = using or router.db_for_write(type(self), instance=self)
        if force_insert and (force_update or update_fields):
            raise ValueError("Cannot force both insert and updating in model saving.")
        if update_fields is not None:
            update_fields = frozenset(update_fields)
            if not update_fields:
                return
            if update_fields - self._meta._non_pk_concrete_field_names:
                raise ValueError("update_fields contiene campos no actualizables de Usuario.")
        elif not force_insert and using == self._state.db:
            # Conserva el guardado parcial automático de instancias diferidas.
            deferred = self.get_deferred_fields()
            if deferred:
                loaded = self._meta._non_pk_concrete_field_names - deferred
                if loaded:
                    update_fields = frozenset(loaded)
        writes_role = update_fields is None or "rol" in update_fields
        if writes_role:
            self._meta.get_field("rol").clean(self.rol, self)
        options = dict(force_insert=force_insert, force_update=force_update,
                       using=using, update_fields=update_fields)
        if self.pk is None:
            return super().save(**options)
        with transaction.atomic(using=using):
            original = (
                type(self).objects.using(using).select_for_update().filter(pk=self.pk)
                .values_list("rol", flat=True).first()
            )
            if original == self.Rol.OPERADOR and not force_insert and writes_role and self.rol != original:
                raise ValidationError({"rol": "Salir de OPERADOR está bloqueado hasta verificar folios reales."})
            if original is None:
                if force_update:
                    raise DatabaseError("Forced update did not affect any rows.")
                if update_fields:
                    raise DatabaseError("Save with update_fields did not affect any rows.")
                # Una PK ausente no queda bloqueada por SELECT FOR UPDATE.
                # INSERT evita sobrescribir una cuenta creada entre lectura y escritura.
                if not force_insert:
                    options["force_insert"] = True
            elif not force_insert:
                # Evita insertar si la fila desaparece; la operación es una actualización.
                options["force_update"] = True
            return super().save(**options)

    save.alters_data = True
