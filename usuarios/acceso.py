"""Autorización de pantallas por cuenta activa y rol funcional vigente."""

from functools import wraps

from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.views.decorators.cache import never_cache

from .models import Usuario


DESTINOS = {
    Usuario.Rol.RECEPCION: "usuarios:recepcion",
    Usuario.Rol.OPERADOR: "usuarios:operacion",
    Usuario.Rol.ADMINISTRADOR: "usuarios:administracion",
}


def destino_por_rol(usuario):
    if not usuario.is_authenticated or not usuario.is_active:
        raise PermissionDenied
    try:
        return DESTINOS[usuario.rol]
    except KeyError:
        raise PermissionDenied from None


def requiere_rol(*roles):
    """No obtiene permisos desde flags técnicos ni desde valores de sesión."""
    def decorator(view):
        @never_cache
        @login_required(redirect_field_name=None)
        @wraps(view)
        def protected(request, *args, **kwargs):
            if not request.user.is_active:
                logout(request)
                return redirect("usuarios:login")
            if request.user.rol not in roles:
                raise PermissionDenied
            return view(request, *args, **kwargs)

        return protected

    return decorator
