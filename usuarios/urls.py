from django.urls import path

from folios import views as recepcion_views

from . import views


app_name = "usuarios"
urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("acceso/", views.AccesoView.as_view(), name="login"),
    path("salir/", views.SalirView.as_view(), name="logout"),
    path("recepcion/", recepcion_views.nueva_atencion, name="recepcion"),
    path("recepcion/tramites/", recepcion_views.tramites, name="recepcion_tramites"),
    path("recepcion/confirmacion/<uuid:folio_id>/", recepcion_views.confirmacion, name="recepcion_confirmacion"),
    path("operacion/", views.operacion, name="operacion"),
    path("administracion/", views.administracion, name="administracion"),
]
