from django.urls import path

from . import views

app_name = "oficinas"

urlpatterns = [
    path("administracion/oficinas/", views.gestion_oficinas, name="gestion_oficinas"),
]
