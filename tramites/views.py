from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, router, transaction
from django.shortcuts import redirect, render

from oficinas.models import Oficina
from usuarios.acceso import requiere_rol
from usuarios.models import Usuario

from .forms import FormularioTramite
from .models import Tramite


@requiere_rol(Usuario.Rol.ADMINISTRADOR)
def gestion_tramites(request):
    oficinas_activas = Oficina.objects.filter(activo=True)
    if request.method == "POST":
        form = FormularioTramite(request.POST)
        if form.is_valid():
            nombre = form.cleaned_data["nombre"]
            oficina = form.cleaned_data["oficina_id"]
            activo = form.cleaned_data["activo"]
            using = router.db_for_write(Tramite)
            try:
                with transaction.atomic(using=using):
                    tramite = Tramite.objects.using(using).create(
                        nombre=nombre,
                        oficina=oficina,
                        activo=activo,
                    )
                messages.success(request, f"Trámite «{tramite.nombre}» creado correctamente.")
                return redirect("tramites:gestion_tramites")
            except ValidationError as exc:
                if hasattr(exc, "message_dict"):
                    for field, errs in exc.message_dict.items():
                        form.add_error(field if field in form.fields else None, errs)
                elif hasattr(exc, "messages"):
                    for msg in exc.messages:
                        form.add_error("nombre", msg)
                else:
                    form.add_error("nombre", str(exc))
                messages.error(request, "No se pudo crear el trámite. Revisa los datos ingresados.")
            except IntegrityError:
                form.add_error("nombre", "Ya existe un trámite con este nombre en la oficina seleccionada.")
                messages.error(request, "No se pudo crear el trámite. Ya existe en la oficina seleccionada.")
        else:
            messages.error(request, "Revisa los campos del formulario.")

        return render(
            request,
            "administracion/tramites.html",
            {
                "tramites": Tramite.objects.all(),
                "oficinas": oficinas_activas,
                "oficinas_disponibles": oficinas_activas,
                "form": form,
                "seccion": "tramites",
                "pagina": "tramites",
            },
        )

    form = FormularioTramite()
    return render(
        request,
        "administracion/tramites.html",
        {
            "tramites": Tramite.objects.all(),
            "oficinas": oficinas_activas,
            "oficinas_disponibles": oficinas_activas,
            "form": form,
            "seccion": "tramites",
            "pagina": "tramites",
        },
    )
