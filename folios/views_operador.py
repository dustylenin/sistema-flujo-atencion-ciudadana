"""Dos pantallas propias y acciones POST que delegan en servicios verificados."""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST

from usuarios.acceso import requiere_rol
from usuarios.models import Usuario

from .forms_operador import FormularioLlamar, FormularioPausa, FormularioReanudar
from .services_disponibilidad import (
    Disponibilidad, consultar_disponibilidad, pausar_operador, reanudar_operador,
)
from .services_llamado import EstadoLlamado, llamar_siguiente
from .services_operador import consultar_folio_actual_operador, consultar_pendientes_operador


_ACCIONES = {
    "LLAMAR": ("Llamar siguiente", "usuarios:operador_llamar"),
    "PAUSAR": ("Confirmar pausa", "usuarios:operador_pausar"),
    "REANUDAR": ("Reanudar atención", "usuarios:operador_reanudar"),
}
_RESULTADOS = {
    "LLAMADO": ("Se realizó el llamado. El folio quedó a tu cargo.", "llamado realizado"),
    "EN_PAUSA": ("Estás en pausa. No se realizó un llamado.", "en pausa; sin llamado"),
    "OCUPADO": ("Ya tienes un folio a tu cargo. No se realizó otro llamado.", "ocupado; sin llamado"),
    "SIN_ASIGNACIONES": ("No tienes oficinas asignadas activamente. No se realizó un llamado.", "sin asignaciones; sin llamado"),
    "SIN_PENDIENTES": ("No hay pendientes en tu cola. No se realizó un llamado.", "sin pendientes; sin llamado"),
    "PAUSADA": ("Se registró la pausa. Conservas tu folio, si lo tienes.", "pausa registrada"),
    "YA_EN_PAUSA": ("La pausa ya estaba abierta. No se creó otra pausa.", "pausa ya abierta"),
    "REANUDADA": ("Se cerró esa pausa. Consulta tu disponibilidad actual.", "pausa cerrada"),
    "YA_REANUDADA": ("Esa pausa ya estaba cerrada. No se cerró otra pausa.", "pausa ya cerrada"),
}


def _pantalla(request, pagina):
    disponibilidad = consultar_disponibilidad(actor=request.user, operador_id=request.user.pk)
    actual = consultar_folio_actual_operador(actor=request.user)
    destino = "usuarios:operacion" if pagina == "cola" else "usuarios:operador_actual"
    referencia = disponibilidad.folio_actual
    # Son lecturas distintas: una discrepancia invita a actualizar, sin atribuir
    # a la pantalla la autorización de la siguiente operación.
    cambio = (
        (referencia.folio_id, referencia.estado, referencia.oficina_id) if referencia else None
    ) != ((actual.folio_id, actual.estado, actual.oficina_id) if actual else None)
    contexto = {
        "pagina": pagina, "disponibilidad": disponibilidad, "actual": actual,
        "cambio_durante_lectura": cambio, "destino": destino,
        "disponibilidad_texto": {
            Disponibilidad.LIBRE: "Libre", Disponibilidad.OCUPADO: "Ocupado",
            Disponibilidad.EN_PAUSA: "En pausa",
        }[disponibilidad.disponibilidad],
    }
    if disponibilidad.disponibilidad == Disponibilidad.LIBRE and actual is None and not cambio:
        contexto["form_llamar"] = FormularioLlamar(actor=request.user, destino=destino)
    if disponibilidad.pausa_abierta_id is not None:
        contexto["form_reanudar"] = FormularioReanudar(
            actor=request.user, destino=destino, pausa_id=disponibilidad.pausa_abierta_id,
        )
    else:
        contexto["form_pausar"] = FormularioPausa(actor=request.user, destino=destino)
    status = 200
    if pagina == "cola":
        contexto["continuacion"] = "cursor" in request.GET
        try:
            contexto["pendientes"] = consultar_pendientes_operador(
                actor=request.user, cursor=request.GET.get("cursor"),
            )
        except ValidationError:
            contexto["error_cursor"] = "No se pudo abrir esa página de la cola. Vuelve al inicio para actualizarla."
            status = 400
    return render(request, f"operador/{pagina}.html", contexto, status=status)


@requiere_rol(Usuario.Rol.OPERADOR)
@require_GET
def cola(request):
    return _pantalla(request, "cola")


@requiere_rol(Usuario.Rol.OPERADOR)
@require_GET
def actual(request):
    return _pantalla(request, "actual")


def _error_accion(request, form, *, status=400):
    # Un POST fallido conserva token, clave y captura; no crea otra intención,
    # no sustituye la pausa y no necesita nuevas lecturas de negocio.
    form.marcar_errores()
    destino = form.intencion.destino if form.intencion else "usuarios:operacion"
    texto, ruta = _ACCIONES[form.operacion]
    return render(request, "operador/accion.html", {
        "form": form, "destino": destino, "accion_texto": texto, "accion_ruta": ruta,
        "pagina": "cola" if destino == "usuarios:operacion" else "actual",
        "messages": [],
    }, status=status)


def _procesar(request, formulario):
    # Un doble POST puede llegar antes de consumir el mensaje del primero.
    # Conservar solo el resultado de esta petición evita presentarlo dos veces;
    # los mensajes de otras funciones se mantienen.
    anteriores = list(messages.get_messages(request))
    for mensaje in anteriores:
        if "operador" not in (mensaje.extra_tags or "").split():
            messages.add_message(request, mensaje.level, mensaje.message, extra_tags=mensaje.extra_tags)
    form = formulario(request.POST, actor=request.user)
    if not form.is_valid():
        return _error_accion(request, form)
    intencion = form.intencion
    try:
        if form.operacion == "LLAMAR":
            resultado = llamar_siguiente(actor=request.user, solicitud_id=intencion.solicitud_id)
        elif form.operacion == "PAUSAR":
            resultado = pausar_operador(
                actor=request.user, solicitud_id=intencion.solicitud_id,
                motivo=form.cleaned_data["motivo"],
            )
        else:
            resultado = reanudar_operador(
                actor=request.user, solicitud_id=intencion.solicitud_id, pausa_id=intencion.pausa_id,
            )
    except ValidationError as error:
        for mensaje in error.messages:
            form.add_error(None, mensaje)
        return _error_accion(request, form)
    except DatabaseError:
        form.add_error(None, "No se pudo confirmar la respuesta. Reintenta este mismo formulario sin cambiar los datos.")
        return _error_accion(request, form, status=503)
    mensaje, historico = _RESULTADOS[resultado.resultado]
    if resultado.repetida:
        messages.info(request, (
            f"Solicitud ya procesada. Resultado original: {historico}. "
            "No se ejecutó otra transición. Consulta el estado actual."
        ), extra_tags="operador")
    else:
        messages.info(request, mensaje, extra_tags="operador")
    destino = (
        "usuarios:operador_actual"
        if form.operacion == "LLAMAR" and resultado.resultado == EstadoLlamado.LLAMADO
        else intencion.destino
    )
    return redirect(destino)


@requiere_rol(Usuario.Rol.OPERADOR)
@require_POST
def llamar(request):
    return _procesar(request, FormularioLlamar)


@requiere_rol(Usuario.Rol.OPERADOR)
@require_POST
def pausar(request):
    return _procesar(request, FormularioPausa)


@requiere_rol(Usuario.Rol.OPERADOR)
@require_POST
def reanudar(request):
    return _procesar(request, FormularioReanudar)
