from django.contrib.auth.models import UserManager
from django.db import models, NotSupportedError


class UsuarioQuerySet(models.QuerySet):
    def update(self, **kwargs):
        if "rol" in kwargs:
            raise NotSupportedError("El rol se guarda por instancia; salir de OPERADOR sigue bloqueado.")
        return super().update(**kwargs)

    update.alters_data = True

    def bulk_update(self, objs, fields, batch_size=None):
        fields = tuple(fields)
        if "rol" in fields:
            raise NotSupportedError("bulk_update() del rol no está admitido.")
        return super().bulk_update(objs, fields, batch_size=batch_size)

    bulk_update.alters_data = True

    def bulk_create(self, objs, batch_size=None, ignore_conflicts=False,
                    update_conflicts=False, update_fields=None, unique_fields=None):
        if update_conflicts:
            raise NotSupportedError("bulk_create() con sobrescritura no está admitido para usuarios.")
        objs = list(objs)
        for obj in objs:
            obj._meta.get_field("rol").clean(obj.rol, obj)
        return super().bulk_create(
            objs, batch_size=batch_size, ignore_conflicts=ignore_conflicts,
            update_conflicts=False, update_fields=update_fields, unique_fields=unique_fields,
        )

    bulk_create.alters_data = True


class UsuarioManager(UserManager.from_queryset(UsuarioQuerySet)):
    """Exige un rol funcional explícito sin inferirlo de permisos técnicos."""

    def create_user(self, username, email=None, password=None, *, rol, **extra_fields):
        self.model._meta.get_field("rol").clean(rol, None)
        return super().create_user(
            username, email=email, password=password, rol=rol, **extra_fields
        )

    create_user.alters_data = True

    def create_superuser(
        self, username, email=None, password=None, *, rol, **extra_fields
    ):
        self.model._meta.get_field("rol").clean(rol, None)
        return super().create_superuser(
            username, email=email, password=password, rol=rol, **extra_fields
        )

    create_superuser.alters_data = True

    async def acreate_user(self, username, email=None, password=None, *, rol, **extra_fields):
        self.model._meta.get_field("rol").clean(rol, None)
        return await super().acreate_user(username, email=email, password=password, rol=rol, **extra_fields)

    acreate_user.alters_data = True

    async def acreate_superuser(self, username, email=None, password=None, *, rol, **extra_fields):
        self.model._meta.get_field("rol").clean(rol, None)
        return await super().acreate_superuser(
            username, email=email, password=password, rol=rol, **extra_fields
        )

    acreate_superuser.alters_data = True
