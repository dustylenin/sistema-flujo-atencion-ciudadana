"""Acceso común y destinos mínimos por rol funcional."""

from django.urls import include, path

urlpatterns = [
    path("administracion/oficinas/", include("oficinas.urls")),
    path("administracion/tramites/", include("tramites.urls")),
    path("", include("usuarios.urls")),
]
