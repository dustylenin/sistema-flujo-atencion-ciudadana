from django.urls import path

from . import views

app_name = "oficinas"

urlpatterns = [
    path("", views.gestion_oficinas, name="gestion_oficinas"),
]
