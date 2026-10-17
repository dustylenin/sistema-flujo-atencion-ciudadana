from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render
from django.urls import reverse

from .acceso import DESTINOS, destino_por_rol, requiere_rol
from .forms import FormularioAcceso
from .models import Usuario


class AccesoView(LoginView):
    template_name = "usuarios/login.html"
    authentication_form = FormularioAcceso
    redirect_authenticated_user = True

    def get_success_url(self):
        # No se consulta next, ni siquiera si apunta a una URL de este sitio.
        return reverse(destino_por_rol(self.request.user))


class SalirView(LogoutView):
    http_method_names = ["post"]

    def get_success_url(self):
        return reverse("usuarios:login")


@requiere_rol(*DESTINOS)
def inicio(request):
    return redirect(destino_por_rol(request.user))


def _destino(request, titulo):
    return render(request, "usuarios/destino.html", {"titulo": titulo})


@requiere_rol(Usuario.Rol.ADMINISTRADOR)
def administracion(request):
    return render(
        request,
        "administracion/resumen.html",
        {"seccion": "resumen", "pagina": "resumen"},
    )
