"""Acceso común y destinos mínimos por rol funcional."""

from django.urls import include, path

urlpatterns = [
    path("administracion/oficinas/", include("oficinas.urls")),
    path("", include("usuarios.urls")),
]
