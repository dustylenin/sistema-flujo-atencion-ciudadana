from django.contrib.auth.models import UserManager


class UsuarioManager(UserManager):
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
