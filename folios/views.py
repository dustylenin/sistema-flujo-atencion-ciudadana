"""Nueva atención, catálogos dependientes y confirmación propia de Recepción."""

from django.core.exceptions import ValidationError
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from usuarios.acceso import requiere_rol
from usuarios.models import Usuario

from .forms import FormularioNuevaAtencion, FormularioOficina, tramites_disponibles
from .models import Folio
from .services import registrar_folio


@requiere_rol(Usuario.Rol.RECEPCION)
@require_http_methods(["GET", "POST"])
def nueva_atencion(request):
    carga = None
    if request.method == "GET":
        form = FormularioNuevaAtencion()
    elif request.POST.get("accion") == "cargar_tramites":
        # Solo se valida oficina. La captura, incluso incompleta o inválida,
        # se conserva como initial sin validar contactos ni crear registros.
        carga = FormularioOficina(request.POST)
        carga.is_valid()
        form = FormularioNuevaAtencion(initial={
            name: request.POST.get(name, "") for name in FormularioNuevaAtencion.base_fields
        })
        if carga.errors:
            form.fields["oficina"].widget.attrs.update({
                "aria-invalid": "true", "aria-describedby": "ayuda-oficina error-carga",
            })
    elif request.POST.get("accion") == "registrar":
        form = FormularioNuevaAtencion(request.POST)
        if form.is_valid():
            datos = form.cleaned_data
            try:
                resultado = registrar_folio(
                    actor=request.user, nombre_completo=datos["nombre_completo"],
                    correo=datos["correo"], telefono=datos["telefono"],
                    oficina_id=datos["oficina"].pk, tramite_id=datos["tramite"].pk,
                )
            except ValidationError as error:
                # Rechazos del servicio incluyen cambios de catálogo después
                # de validar el formulario. No se relaja ni sustituye el servicio.
                if hasattr(error, "message_dict"):
                    for name, messages in error.message_dict.items():
                        form.add_error(name if name in form.fields else None, messages)
                else:
                    form.add_error(None, error)
            else:
                return redirect("usuarios:recepcion_confirmacion", folio_id=resultado.folio_id)
        form.marcar_errores()
    else:
        return HttpResponseBadRequest("Selecciona una acción válida.")
    return render(request, "recepcion/nueva_atencion.html", {
        "form": form, "carga": carga,
        "hay_oficinas": form.fields["oficina"].queryset.exists(),
    })


@requiere_rol(Usuario.Rol.RECEPCION)
@require_GET
def tramites(request):
    form = FormularioOficina(request.GET)
    if not form.is_valid():
        return JsonResponse({"error": "Selecciona una oficina activa con trámites disponibles."}, status=400)
    opciones = tramites_disponibles(form.cleaned_data["oficina"].pk).values("id", "nombre")
    return JsonResponse({"tramites": list(opciones)})


@requiere_rol(Usuario.Rol.RECEPCION)
@require_GET
def confirmacion(request, folio_id):
    folio = get_object_or_404(
        Folio.objects.select_related("oficina", "tramite", "registrado_por"),
        pk=folio_id, registrado_por_id=request.user.pk,
    )
    return render(request, "recepcion/confirmacion.html", {"folio": folio})
