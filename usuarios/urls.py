from django.urls import path

from . import views


app_name = "usuarios"
urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("acceso/", views.AccesoView.as_view(), name="login"),
    path("salir/", views.SalirView.as_view(), name="logout"),
    path("recepcion/", views.recepcion, name="recepcion"),
    path("operacion/", views.operacion, name="operacion"),
    path("administracion/", views.administracion, name="administracion"),
]
