"""Resolución propia atómica; finalización y denegación de la atención."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models, router, transaction
from django.utils import timezone

from oficinas.models import Oficina

from .models import EventoFolio, Folio, SolicitudOperador, validar_notas_resolucion
from .services_disponibilidad import _identidad_actor, _operador_bloqueado
from .solicitudes import buscar_solicitud, clave_solicitud


class EstadoResolucion(StrEnum):
    FINALIZADO = "FINALIZADO"
    DENEGADO = "DENEGADO"


@dataclass(frozen=True)
class ResultadoResolucion:
    solicitud_id: UUID
    operacion: str
    resultado: EstadoResolucion
    folio_id: UUID
    evento_id: int | None
    confirmada_en: datetime
    repetida: bool


def _resultado(solicitud, *, repetida):
    return ResultadoResolucion(
        solicitud.solicitud_id, solicitud.operacion, EstadoResolucion(solicitud.resultado),
        solicitud.folio_resultado_id, solicitud.evento_folio_resultado_id,
        solicitud.confirmada_en, repetida,
    )


def _propiedad_y_estado(folio, operador):
    if folio.operador_responsable_id != operador.pk:
        raise PermissionDenied("Solo puede finalizar su folio actual propio.")
    if folio.estado != Folio.Estado.EN_ATENCION:
        raise ValidationError("El folio no está En atención.")


def _resolver_con_evento(*, folio, operador, resultado, notas_resolucion, instante, using):
    if (
        (folio.inicio_atencion is not None and instante < folio.inicio_atencion)
        or instante < folio.llegada_original
        or EventoFolio.objects.using(using).filter(folio=folio, fecha__gt=instante).exists()
    ):
        raise ValidationError("La fecha de resolución es anterior a la evidencia del folio.")
    folio.estado = resultado
    folio.operador_responsable = None
    models.Model.save(
        folio, using=using, force_update=True, update_fields=["estado", "operador_responsable"],
    )
    evento = EventoFolio(
        folio=folio, actor=operador, fecha=instante, operacion=EventoFolio.Operacion.RESOLUCION,
        estado_anterior=Folio.Estado.EN_ATENCION, estado_nuevo=resultado,
        operador_responsable=operador, oficina_contexto_id=folio.oficina_id,
        datos_iniciales={"notas_resolucion": notas_resolucion}, asignacion_autorizante=None,
    )
    models.Model.save(evento, using=using, force_insert=True)
    return evento


def _confirmar_resolucion(*, operador, clave, folio, resultado, notas_resolucion, evento, instante, using):
    solicitud = SolicitudOperador(
        operador=operador, solicitud_id=clave, operacion=SolicitudOperador.Operacion.FINALIZAR,
        folio_objetivo=folio, folio_resultado=folio, evento_folio_resultado=evento,
        motivo_solicitado=notas_resolucion, pausa_objetivo=None, pausa_resultado=None,
        evento_resultado=None, resultado=resultado, confirmada_en=instante,
    )
    models.Model.save(solicitud, using=using, force_insert=True)
    return _resultado(solicitud, repetida=False)


def finalizar_atencion(
    *, actor, folio_id, solicitud_id, resultado, notas_resolucion,
) -> ResultadoResolucion:
    using = router.db_for_write(Folio)
    with transaction.atomic(using=using):
        _identidad_actor(actor, using)
        operador = _operador_bloqueado(actor, using)
        clave = clave_solicitud(solicitud_id)
        try:
            objetivo = clave_solicitud(folio_id)
        except ValidationError as error:
            raise ValidationError({"folio_id": "Se requiere un UUID válido."}) from error

        if resultado not in {Folio.Estado.FINALIZADO, Folio.Estado.DENEGADO}:
            raise ValidationError({"resultado": "El resultado debe ser Finalizado o Denegado."})

        validar_notas_resolucion(notas_resolucion)

        repetida = buscar_solicitud(
            operador=operador, clave=clave, operacion=SolicitudOperador.Operacion.FINALIZAR,
            motivo=notas_resolucion, pausa_id=None, folio_id=objetivo, using=using,
        )
        if repetida is not None:
            if repetida.resultado != resultado:
                raise ValidationError({"solicitud_id": "Esta clave ya confirmó un resultado diferente."})
            return _resultado(repetida, repetida=True)

        contexto = Folio.objects.using(using).filter(pk=objetivo).first()
        if contexto is None:
            raise ValidationError({"folio_id": "El folio no existe."})
        _propiedad_y_estado(contexto, operador)

        # Compatible con inicio, llamado y disponibilidad: Usuario -> oficina -> folio.
        Oficina.objects.using(using).select_for_update().get(pk=contexto.oficina_id)
        folio = Folio.objects.using(using).select_for_update(of=("self",)).filter(pk=objetivo).first()
        if folio is None or folio.oficina_id != contexto.oficina_id:
            raise ValidationError("El folio cambió fuera del protocolo del operador.")
        _propiedad_y_estado(folio, operador)

        instante = timezone.now()
        evento = _resolver_con_evento(
            folio=folio, operador=operador, resultado=resultado,
            notas_resolucion=notas_resolucion, instante=instante, using=using,
        )
        return _confirmar_resolucion(
            operador=operador, clave=clave, folio=folio, resultado=resultado,
            notas_resolucion=notas_resolucion, evento=evento, instante=instante, using=using,
        )
