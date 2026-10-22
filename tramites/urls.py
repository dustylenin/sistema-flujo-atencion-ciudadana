from django.urls import path

from . import views

app_name = "tramites"

urlpatterns = [
    path("", views.gestion_tramites, name="gestion_tramites"),
]
