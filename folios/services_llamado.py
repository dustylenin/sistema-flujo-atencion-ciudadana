"""Selección y reserva atómicas con comprobantes históricos del propio operador."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import models, router, transaction
from django.utils import timezone

from oficinas.models import AsignacionOperadorOficina, Oficina

from .models import EventoFolio, Folio, PausaOperador, SolicitudOperador
from .services_disponibilidad import _folios_actuales, _identidad_actor, _operador_bloqueado
from .solicitudes import buscar_solicitud, clave_solicitud


class EstadoLlamado(StrEnum):
    EN_PAUSA = "EN_PAUSA"
    OCUPADO = "OCUPADO"
    SIN_ASIGNACIONES = "SIN_ASIGNACIONES"
    SIN_PENDIENTES = "SIN_PENDIENTES"
    LLAMADO = "LLAMADO"


@dataclass(frozen=True)
class ResultadoLlamado:
    solicitud_id: UUID
    operacion: str
    resultado: EstadoLlamado
    folio_id: UUID | None
    evento_id: int | None
    confirmada_en: datetime
    repetida: bool


def _resultado(solicitud, *, repetida):
    return ResultadoLlamado(
        solicitud.solicitud_id, solicitud.operacion, EstadoLlamado(solicitud.resultado),
        solicitud.folio_resultado_id, solicitud.evento_folio_resultado_id,
        solicitud.confirmada_en, repetida,
    )


def _confirmar_solicitud_llamado(*, operador, clave, resultado, instante, using, folio=None, evento=None):
    solicitud = SolicitudOperador(
        operador=operador, solicitud_id=clave, operacion=SolicitudOperador.Operacion.LLAMAR,
        motivo_solicitado=None, pausa_objetivo=None, pausa_resultado=None, evento_resultado=None,
        resultado=resultado, folio_resultado=folio, evento_folio_resultado=evento,
        confirmada_en=instante,
    )
    models.Model.save(solicitud, using=using, force_insert=True)
    return _resultado(solicitud, repetida=False)


def _asignaciones_bloqueadas(operador, using):
    # Usuario mantiene estable el conjunto frente a los servicios de asignación.
    referencias = list(AsignacionOperadorOficina.objects.using(using).filter(
        operador=operador, activo=True,
    ).order_by("pk").values_list("pk", "oficina_id"))
    for oficina_id in sorted({oficina_id for _, oficina_id in referencias}):
        Oficina.objects.using(using).select_for_update().get(pk=oficina_id)
    asignaciones = {}
    for pk, oficina_id in referencias:
        asignacion = AsignacionOperadorOficina.objects.using(using).select_for_update().get(pk=pk)
        if (
            not asignacion.activo or asignacion.operador_id != operador.pk
            or asignacion.oficina_id != oficina_id
        ):
            raise ValidationError("La asignación cambió fuera del protocolo del operador.")
        asignaciones[oficina_id] = asignacion
    return asignaciones


def _reservar_folio(*, folio, operador, using):
    folio.estado = Folio.Estado.LLAMADO
    folio.operador_responsable = operador
    models.Model.save(
        folio, using=using, force_update=True, update_fields=["estado", "operador_responsable"],
    )


def _crear_evento_llamado(*, folio, operador, asignacion, instante, using):
    evento = EventoFolio(
        folio=folio, actor=operador, fecha=instante, operacion=EventoFolio.Operacion.LLAMADO,
        estado_anterior=Folio.Estado.EN_ESPERA, estado_nuevo=Folio.Estado.LLAMADO,
        datos_iniciales=None, operador_responsable=operador, asignacion_autorizante=asignacion,
    )
    models.Model.save(evento, using=using, force_insert=True)
    return evento


def llamar_siguiente(*, actor, solicitud_id) -> ResultadoLlamado:
    using = router.db_for_write(Folio)
    _identidad_actor(actor, using)
    with transaction.atomic(using=using):
        operador = _operador_bloqueado(actor, using)
        clave = clave_solicitud(solicitud_id)
        repetida = buscar_solicitud(
            operador=operador, clave=clave, operacion=SolicitudOperador.Operacion.LLAMAR,
            motivo=None, pausa_id=None, using=using,
        )
        if repetida is not None:
            return _resultado(repetida, repetida=True)

        if PausaOperador.objects.using(using).filter(operador=operador, fin__isnull=True).exists():
            estado = EstadoLlamado.EN_PAUSA
        elif _folios_actuales(using, operador.pk).exists():
            estado = EstadoLlamado.OCUPADO
        else:
            asignaciones = _asignaciones_bloqueadas(operador, using)
            if not asignaciones:
                estado = EstadoLlamado.SIN_ASIGNACIONES
            else:
                # Consulta nueva después de bloquear TODAS las oficinas.
                # No filtra actividad de oficina/trámite ni salta filas bloqueadas.
                folio = Folio.objects.using(using).filter(
                    oficina_id__in=asignaciones, estado=Folio.Estado.EN_ESPERA,
                ).order_by("llegada_original", "id").select_for_update(of=("self",)).first()
                if folio is not None:
                    asignacion = asignaciones.get(folio.oficina_id)
                    if (
                        folio.estado != Folio.Estado.EN_ESPERA or folio.operador_responsable_id is not None
                        or asignacion is None or not asignacion.activo
                        or asignacion.operador_id != operador.pk or asignacion.oficina_id != folio.oficina_id
                    ):
                        raise ValidationError("El folio o su asignación cambió fuera del protocolo.")
                    instante = timezone.now()
                    _reservar_folio(folio=folio, operador=operador, using=using)
                    evento = _crear_evento_llamado(
                        folio=folio, operador=operador, asignacion=asignacion, instante=instante, using=using,
                    )
                    return _confirmar_solicitud_llamado(
                        operador=operador, clave=clave, resultado=EstadoLlamado.LLAMADO,
                        instante=instante, using=using, folio=folio, evento=evento,
                    )
                estado = EstadoLlamado.SIN_PENDIENTES
        return _confirmar_solicitud_llamado(
            operador=operador, clave=clave, resultado=estado, instante=timezone.now(), using=using,
        )
