from django.urls import path

from folios import views as recepcion_views
from folios import views_operador as operador_views
from oficinas import views as oficinas_views

from . import views


app_name = "usuarios"
urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("acceso/", views.AccesoView.as_view(), name="login"),
    path("salir/", views.SalirView.as_view(), name="logout"),
    path("recepcion/", recepcion_views.nueva_atencion, name="recepcion"),
    path("recepcion/tramites/", recepcion_views.tramites, name="recepcion_tramites"),
    path("recepcion/confirmacion/<uuid:folio_id>/", recepcion_views.confirmacion, name="recepcion_confirmacion"),
    path("operacion/", operador_views.cola, name="operacion"),
    path("operacion/actual/", operador_views.actual, name="operador_actual"),
    path("operacion/llamar/", operador_views.llamar, name="operador_llamar"),
    path("operacion/pausar/", operador_views.pausar, name="operador_pausar"),
    path("operacion/reanudar/", operador_views.reanudar, name="operador_reanudar"),
    path("operacion/iniciar/", operador_views.iniciar, name="operador_iniciar"),
    path("operacion/finalizar/", operador_views.finalizar, name="operador_finalizar"),
    path("administracion/", views.administracion, name="administracion"),
    path("administracion/oficinas/", oficinas_views.gestion_oficinas, name="admin_oficinas"),
]
