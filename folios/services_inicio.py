"""Inicio propio atómico; la responsabilidad vigente autoriza la transición."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models, router, transaction
from django.utils import timezone

from oficinas.models import Oficina

from .models import EventoFolio, Folio, PausaOperador, SolicitudOperador
from .services_disponibilidad import _identidad_actor, _operador_bloqueado
from .solicitudes import buscar_solicitud, clave_solicitud


class EstadoInicio(StrEnum):
    INICIADA = "INICIADA"
    YA_EN_ATENCION = "YA_EN_ATENCION"
    EN_PAUSA = "EN_PAUSA"


@dataclass(frozen=True)
class ResultadoInicio:
    solicitud_id: UUID
    operacion: str
    resultado: EstadoInicio
    folio_id: UUID
    evento_id: int | None
    confirmada_en: datetime
    repetida: bool


def _resultado(solicitud, *, repetida):
    return ResultadoInicio(
        solicitud.solicitud_id, solicitud.operacion, EstadoInicio(solicitud.resultado),
        solicitud.folio_resultado_id, solicitud.evento_folio_resultado_id,
        solicitud.confirmada_en, repetida,
    )


def _propiedad_y_estado(folio, operador):
    if folio.operador_responsable_id != operador.pk:
        raise PermissionDenied("Solo puede iniciar su folio actual propio.")
    if folio.estado not in {Folio.Estado.LLAMADO, Folio.Estado.EN_ATENCION}:
        raise ValidationError("El folio no está Llamado ni En atención.")


def _iniciar_con_evento(*, folio, operador, instante, using):
    # No exige una asignación ni un evento previo para autorizar. Si hay
    # evidencia temporal, no permite contradecirla ni ajustar fechas a escondidas.
    if instante < folio.llegada_original or EventoFolio.objects.using(using).filter(
        folio=folio, fecha__gt=instante,
    ).exists():
        raise ValidationError("La fecha de inicio es anterior a la evidencia del folio.")
    folio.estado = Folio.Estado.EN_ATENCION
    folio.inicio_atencion = instante
    models.Model.save(
        folio, using=using, force_update=True, update_fields=["estado", "inicio_atencion"],
    )
    evento = EventoFolio(
        folio=folio, actor=operador, fecha=instante, operacion=EventoFolio.Operacion.INICIO,
        estado_anterior=Folio.Estado.LLAMADO, estado_nuevo=Folio.Estado.EN_ATENCION,
        operador_responsable=operador, oficina_contexto_id=folio.oficina_id,
        datos_iniciales=None, asignacion_autorizante=None,
    )
    models.Model.save(evento, using=using, force_insert=True)
    return evento


def _confirmar_inicio(*, operador, clave, folio, estado, evento, instante, using):
    solicitud = SolicitudOperador(
        operador=operador, solicitud_id=clave, operacion=SolicitudOperador.Operacion.INICIAR,
        folio_objetivo=folio, folio_resultado=folio, evento_folio_resultado=evento,
        motivo_solicitado=None, pausa_objetivo=None, pausa_resultado=None, evento_resultado=None,
        resultado=estado, confirmada_en=instante,
    )
    models.Model.save(solicitud, using=using, force_insert=True)
    return _resultado(solicitud, repetida=False)


def iniciar_atencion(*, actor, folio_id, solicitud_id) -> ResultadoInicio:
    using = router.db_for_write(Folio)
    with transaction.atomic(using=using):
        _identidad_actor(actor, using)
        operador = _operador_bloqueado(actor, using)
        clave = clave_solicitud(solicitud_id)
        try:
            objetivo = clave_solicitud(folio_id)
        except ValidationError as error:
            raise ValidationError({"folio_id": "Se requiere un UUID válido."}) from error
        repetida = buscar_solicitud(
            operador=operador, clave=clave, operacion=SolicitudOperador.Operacion.INICIAR,
            motivo=None, pausa_id=None, folio_id=objetivo, using=using,
        )
        if repetida is not None:
            return _resultado(repetida, repetida=True)

        contexto = Folio.objects.using(using).filter(pk=objetivo).first()
        if contexto is None:
            raise ValidationError({"folio_id": "El folio no existe."})
        _propiedad_y_estado(contexto, operador)
        # Compatible con llamado y disponibilidad: Usuario → oficina → folio.
        # La oficina solo se bloquea para estabilizar el contexto, sin exigir actividad.
        Oficina.objects.using(using).select_for_update().get(pk=contexto.oficina_id)
        folio = Folio.objects.using(using).select_for_update(of=("self",)).filter(pk=objetivo).first()
        if folio is None or folio.oficina_id != contexto.oficina_id:
            raise ValidationError("El folio cambió fuera del protocolo del operador.")
        _propiedad_y_estado(folio, operador)
        instante = timezone.now()
        evento = None
        if folio.estado == Folio.Estado.EN_ATENCION:
            estado = EstadoInicio.YA_EN_ATENCION
        elif PausaOperador.objects.using(using).filter(operador=operador, fin__isnull=True).exists():
            # Usuario serializa apertura/cierre incluso sin una fila de pausa.
            estado = EstadoInicio.EN_PAUSA
        else:
            estado = EstadoInicio.INICIADA
            evento = _iniciar_con_evento(folio=folio, operador=operador, instante=instante, using=using)
        return _confirmar_inicio(
            operador=operador, clave=clave, folio=folio, estado=estado,
            evento=evento, instante=instante, using=using,
        )
