from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, router, transaction
from django.shortcuts import redirect, render

from usuarios.acceso import requiere_rol
from usuarios.models import Usuario

from .forms import FormularioOficina
from .models import Oficina


@requiere_rol(Usuario.Rol.ADMINISTRADOR)
def gestion_oficinas(request):
    if request.method == "POST":
        form = FormularioOficina(request.POST)
        if form.is_valid():
            nombre = form.cleaned_data["nombre"]
            activo = form.cleaned_data["activo"]
            using = router.db_for_write(Oficina)
            try:
                with transaction.atomic(using=using):
                    oficina = Oficina.objects.using(using).create(nombre=nombre, activo=activo)
                messages.success(request, f"Oficina «{oficina.nombre}» creada correctamente.")
                return redirect("oficinas:gestion_oficinas")
            except (IntegrityError, ValidationError):
                form.add_error("nombre", "Ya existe una oficina con este nombre o los datos son inválidos.")
        else:
            messages.error(request, "Revisa los campos del formulario.")

        return render(
            request,
            "administracion/oficinas.html",
            {
                "oficinas": Oficina.objects.all(),
                "form": form,
                "seccion": "oficinas",
                "pagina": "oficinas",
            },
        )

    form = FormularioOficina()
    return render(
        request,
        "administracion/oficinas.html",
        {
            "oficinas": Oficina.objects.all(),
            "form": form,
            "seccion": "oficinas",
            "pagina": "oficinas",
        },
    )
