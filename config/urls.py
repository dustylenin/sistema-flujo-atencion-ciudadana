"""Acceso común y destinos mínimos por rol funcional."""

from django.urls import include, path

urlpatterns = [
    path("", include("usuarios.urls")),
    path("", include("oficinas.urls")),
]
