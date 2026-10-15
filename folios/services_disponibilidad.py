"""Pausa y reanudación atómicas; consultas con proyecciones por rol.

Las escrituras privadas se limitan a estas transiciones. SQL directo y APIs
internas quedan fuera de las barreras del ORM. No se modifica ningún folio.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models, router, transaction
from django.db.models import Exists, Subquery
from django.utils import timezone

from oficinas.models import Oficina

from .models import EventoDisponibilidad, Folio, PausaOperador, SolicitudOperador
from .solicitudes import buscar_solicitud, clave_solicitud as _clave_solicitud


class Disponibilidad(StrEnum):
    LIBRE = "LIBRE"
    OCUPADO = "OCUPADO"
    EN_PAUSA = "EN_PAUSA"


@dataclass(frozen=True)
class ReferenciaFolioActual:
    folio_id: UUID
    estado: str
    oficina_id: int


@dataclass(frozen=True)
class ResultadoDisponibilidad:
    operador_id: int
    username: str
    disponibilidad: Disponibilidad


@dataclass(frozen=True)
class DisponibilidadPropia(ResultadoDisponibilidad):
    pausa_abierta_id: int | None
    folio_actual: ReferenciaFolioActual | None


@dataclass(frozen=True)
class ResultadoOperacionPausa:
    solicitud_id: UUID
    operacion: str
    resultado: str
    pausa_id: int
    evento_id: int | None
    confirmada_en: datetime
    repetida: bool


@dataclass(frozen=True)
class EventoPausaConsultado:
    evento_id: int
    actor_id: int
    fecha: datetime
    operacion: str


@dataclass(frozen=True)
class PausaConsultada:
    pausa_id: int
    operador_id: int
    username: str
    motivo: str
    inicio: datetime
    fin: datetime | None
    duracion: timedelta
    oficina_id: int | None
    folio_id: UUID | None
    eventos: tuple[EventoPausaConsultado, ...]


def _identidad_actor(actor, using):
    Usuario = get_user_model()
    if (
        not isinstance(actor, Usuario) or not actor.is_authenticated
        or actor.pk is None or actor._state.adding or actor._state.db != using
    ):
        raise PermissionDenied("Se requiere una cuenta autenticada y persistida en esta base.")


def _id_positivo(value, campo):
    if type(value) is not int or value <= 0:
        raise ValidationError({campo: "Se requiere un identificador entero positivo."})
    return value


def _folios_actuales(using, operador_id):
    # Global: no depende de actividad de oficinas, trámites o asignaciones.
    # Ambos estados conservan la capacidad global, también durante una pausa.
    return Folio.objects.using(using).filter(
        operador_responsable_id=operador_id, estado__in=["LLAMADO", "EN_ATENCION"],
    ).order_by("pk")


def consultar_disponibilidad(*, actor, operador_id) -> ResultadoDisponibilidad:
    Usuario = get_user_model()
    using = router.db_for_read(PausaOperador)
    _identidad_actor(actor, using)
    operador_id = _id_positivo(operador_id, "operador_id")
    destino = Usuario.objects.using(using).filter(pk=operador_id)
    pausa = PausaOperador.objects.using(using).filter(operador_id=operador_id, fin__isnull=True)
    folio = _folios_actuales(using, operador_id)
    # Actor, destino, pausa y folio se leen en una sola instantánea SQL.
    fila = Usuario.objects.using(using).filter(pk=actor.pk).annotate(
        destino_rol=Subquery(destino.values("rol")[:1]),
        destino_username=Subquery(destino.values("username")[:1]),
        pausa_actual=Subquery(pausa.values("pk")[:1]),
        folio_actual_id=Subquery(folio.values("pk")[:1]),
        folio_actual_estado=Subquery(folio.values("estado")[:1]),
        folio_actual_oficina=Subquery(folio.values("oficina_id")[:1]),
    ).values(
        "rol", "is_active", "destino_rol", "destino_username", "pausa_actual",
        "folio_actual_id", "folio_actual_estado", "folio_actual_oficina",
    ).first()
    if fila is None or not fila["is_active"] or fila["rol"] not in {
        Usuario.Rol.OPERADOR, Usuario.Rol.RECEPCION,
    }:
        raise PermissionDenied("Disponibilidad solo admite Operador propio o Recepción activos.")
    propia = fila["rol"] == Usuario.Rol.OPERADOR
    if propia and actor.pk != operador_id:
        raise PermissionDenied("El operador solo consulta su disponibilidad.")
    if fila["destino_rol"] != Usuario.Rol.OPERADOR:
        raise ValidationError({"operador_id": "La cuenta destino debe existir y tener rol OPERADOR."})
    disponibilidad = (
        Disponibilidad.EN_PAUSA if fila["pausa_actual"] is not None
        else Disponibilidad.OCUPADO if fila["folio_actual_id"] is not None
        else Disponibilidad.LIBRE
    )
    identidad = dict(operador_id=operador_id, username=fila["destino_username"],
                    disponibilidad=disponibilidad)
    if not propia:
        return ResultadoDisponibilidad(**identidad)
    referencia = None
    if fila["folio_actual_id"] is not None:
        referencia = ReferenciaFolioActual(
            fila["folio_actual_id"], fila["folio_actual_estado"], fila["folio_actual_oficina"],
        )
    return DisponibilidadPropia(**identidad, pausa_abierta_id=fila["pausa_actual"], folio_actual=referencia)


def consultar_pausas(
    *, actor, operador_id, fecha_desde=None, fecha_hasta=None, oficina_id=None, accion=None,
) -> tuple[PausaConsultada, ...]:
    Usuario = get_user_model()
    using = router.db_for_read(PausaOperador)
    _identidad_actor(actor, using)
    autorizados = Usuario.objects.using(using).filter(
        pk=actor.pk, is_active=True, rol=Usuario.Rol.ADMINISTRADOR,
    )
    if not autorizados.exists():
        raise PermissionDenied("La consulta de pausas requiere administrador funcional activo.")
    operador_id = _id_positivo(operador_id, "operador_id")
    for campo, valor in (("fecha_desde", fecha_desde), ("fecha_hasta", fecha_hasta)):
        if valor is not None and (not isinstance(valor, datetime) or timezone.is_naive(valor)):
            raise ValidationError({campo: "Se requiere fecha con zona horaria."})
    if fecha_desde is not None and fecha_hasta is not None and fecha_desde > fecha_hasta:
        raise ValidationError("El rango de fechas está invertido.")
    filtros = {"operador_id": operador_id}
    if oficina_id is not None:
        filtros["oficina_contexto_id"] = _id_positivo(oficina_id, "oficina_id")
    if accion is not None:
        if accion not in EventoDisponibilidad.Operacion.values:
            raise ValidationError({"accion": "Acción de disponibilidad inválida."})
        filtros["eventos__operacion"] = accion
    if fecha_desde is not None:
        filtros["eventos__fecha__gte"] = fecha_desde
    if fecha_hasta is not None:
        filtros["eventos__fecha__lte"] = fecha_hasta
    # Revalida autorización en la misma consulta que expone los datos.
    filas = list(PausaOperador.objects.using(using).annotate(
        autorizado=Exists(autorizados),
    ).filter(autorizado=True, **filtros).order_by("inicio", "pk", "eventos__fecha", "eventos__pk").values(
        "id", "operador_id", "operador__username", "motivo", "inicio", "fin",
        "oficina_contexto_id", "folio_contexto_id", "eventos__id", "eventos__actor_id",
        "eventos__fecha", "eventos__operacion",
    ))
    if not filas and not autorizados.exists():
        raise PermissionDenied("La cuenta administradora ya no está autorizada.")
    instante = timezone.now()
    agrupadas = {}
    for fila in filas:
        agrupadas.setdefault(fila["id"], (fila, []))
        if fila["eventos__id"] is not None:
            agrupadas[fila["id"]][1].append(EventoPausaConsultado(
                fila["eventos__id"], fila["eventos__actor_id"],
                fila["eventos__fecha"], fila["eventos__operacion"],
            ))
    return tuple(PausaConsultada(
        pausa_id=f["id"], operador_id=f["operador_id"], username=f["operador__username"],
        motivo=f["motivo"], inicio=f["inicio"], fin=f["fin"],
        duracion=(f["fin"] or instante) - f["inicio"], oficina_id=f["oficina_contexto_id"],
        folio_id=f["folio_contexto_id"], eventos=tuple(eventos),
    ) for f, eventos in agrupadas.values())


def _operador_bloqueado(actor, using):
    Usuario = get_user_model()
    operador = Usuario.objects.using(using).select_for_update().filter(pk=actor.pk).first()
    if operador is None or not operador.is_active or operador.rol != Usuario.Rol.OPERADOR:
        raise PermissionDenied("Se requiere una cuenta OPERADOR autenticada y activa.")
    return operador


def _resultado(solicitud, *, repetida):
    return ResultadoOperacionPausa(
        solicitud.solicitud_id, solicitud.operacion, solicitud.resultado,
        solicitud.pausa_resultado_id, solicitud.evento_resultado_id,
        solicitud.confirmada_en, repetida,
    )


def _repetida(*, operador, clave, operacion, motivo, pausa_id, using):
    solicitud = buscar_solicitud(
        operador=operador, clave=clave, operacion=operacion,
        motivo=motivo, pausa_id=pausa_id, using=using,
    )
    if solicitud is None:
        return None
    return _resultado(solicitud, repetida=True)


def _bloquear_oficina(oficina_id, using):
    if oficina_id is not None:
        Oficina.objects.using(using).select_for_update().get(pk=oficina_id)


def _abrir_pausa(*, operador, motivo, folio, instante, using):
    pausa = PausaOperador(
        operador=operador, motivo=motivo, inicio=instante, fin=None, folio_contexto=folio,
        oficina_contexto_id=folio.oficina_id if folio else None,
    )
    models.Model.save(pausa, using=using, force_insert=True)
    evento = EventoDisponibilidad(
        pausa=pausa, actor=operador, fecha=instante, operacion=EventoDisponibilidad.Operacion.PAUSA,
    )
    models.Model.save(evento, using=using, force_insert=True)
    return pausa, evento


def _cerrar_pausa(*, pausa, operador, instante, using):
    if pausa.fin is not None:
        raise ValidationError("La pausa ya está cerrada.")
    pausa.fin = instante
    models.Model.save(pausa, using=using, force_update=True, update_fields=["fin"])
    evento = EventoDisponibilidad(
        pausa=pausa, actor=operador, fecha=instante,
        operacion=EventoDisponibilidad.Operacion.REANUDACION,
    )
    models.Model.save(evento, using=using, force_insert=True)
    return evento


def _confirmar_solicitud(*, operador, clave, operacion, motivo, pausa, evento, instante, using):
    if operacion == SolicitudOperador.Operacion.PAUSAR:
        resultado = (SolicitudOperador.Resultado.PAUSADA if evento
                     else SolicitudOperador.Resultado.YA_EN_PAUSA)
        objetivo = None
    elif operacion == SolicitudOperador.Operacion.REANUDAR:
        resultado = (SolicitudOperador.Resultado.REANUDADA if evento
                     else SolicitudOperador.Resultado.YA_REANUDADA)
        objetivo = pausa
    else:
        raise ValidationError("Operación no admitida.")
    solicitud = SolicitudOperador(
        operador=operador, solicitud_id=clave, operacion=operacion, motivo_solicitado=motivo,
        pausa_objetivo=objetivo, resultado=resultado, pausa_resultado=pausa,
        evento_resultado=evento, confirmada_en=instante,
    )
    models.Model.save(solicitud, using=using, force_insert=True)
    return _resultado(solicitud, repetida=False)


def pausar_operador(*, actor, motivo, solicitud_id) -> ResultadoOperacionPausa:
    using = router.db_for_write(PausaOperador)
    _identidad_actor(actor, using)
    with transaction.atomic(using=using):
        operador = _operador_bloqueado(actor, using)
        clave = _clave_solicitud(solicitud_id)
        if not isinstance(motivo, str):
            raise ValidationError({"motivo": "Se requiere texto con contenido."})
        motivo = PausaOperador._meta.get_field("motivo").clean(motivo, None)
        operacion = SolicitudOperador.Operacion.PAUSAR
        repetida = _repetida(
            operador=operador, clave=clave, operacion=operacion, motivo=motivo, pausa_id=None, using=using,
        )
        if repetida:
            return repetida
        abierta = PausaOperador.objects.using(using).filter(operador=operador, fin__isnull=True).first()
        folio = None if abierta else _folios_actuales(using, operador.pk).first()
        _bloquear_oficina(abierta.oficina_contexto_id if abierta else folio.oficina_id if folio else None, using)
        evento = None
        if abierta:
            pausa = PausaOperador.objects.using(using).select_for_update().get(pk=abierta.pk)
        else:
            # Respeta el orden oficinas → pausas → folios. Una búsqueda vacía
            # no bloquea filas; Usuario ya serializa la apertura de la pausa.
            pausa = PausaOperador.objects.using(using).select_for_update().filter(
                operador=operador, fin__isnull=True,
            ).first()
            if pausa is not None:
                raise ValidationError("La pausa cambió fuera del protocolo del operador.")
        if folio:
            oficina_contexto_id = folio.oficina_id
            try:
                folio = _folios_actuales(using, operador.pk).select_for_update().get(pk=folio.pk)
            except Folio.DoesNotExist as error:
                raise ValidationError("El folio cambió fuera del protocolo del operador.") from error
            if folio.oficina_id != oficina_contexto_id:
                raise ValidationError("La oficina del folio cambió fuera del protocolo del operador.")
        instante = timezone.now()
        if pausa is None:
            pausa, evento = _abrir_pausa(
                operador=operador, motivo=motivo, folio=folio, instante=instante, using=using,
            )
        elif pausa.fin is not None:
            raise ValidationError("La pausa cambió fuera del protocolo del operador.")
        return _confirmar_solicitud(
            operador=operador, clave=clave, operacion=operacion, motivo=motivo,
            pausa=pausa, evento=evento, instante=instante, using=using,
        )


def reanudar_operador(*, actor, pausa_id, solicitud_id) -> ResultadoOperacionPausa:
    using = router.db_for_write(PausaOperador)
    _identidad_actor(actor, using)
    with transaction.atomic(using=using):
        operador = _operador_bloqueado(actor, using)
        clave = _clave_solicitud(solicitud_id)
        pausa_id = _id_positivo(pausa_id, "pausa_id")
        operacion = SolicitudOperador.Operacion.REANUDAR
        repetida = _repetida(
            operador=operador, clave=clave, operacion=operacion, motivo=None, pausa_id=pausa_id, using=using,
        )
        if repetida:
            return repetida
        contexto = PausaOperador.objects.using(using).filter(pk=pausa_id).first()
        if contexto is None:
            raise ValidationError({"pausa_id": "La pausa no existe."})
        if contexto.operador_id != operador.pk:
            raise PermissionDenied("Solo puede reanudar una pausa propia.")
        _bloquear_oficina(contexto.oficina_contexto_id, using)
        pausa = PausaOperador.objects.using(using).select_for_update().get(pk=pausa_id)
        if pausa.operador_id != operador.pk:
            raise PermissionDenied("Solo puede reanudar una pausa propia.")
        instante = timezone.now()
        evento = None
        if pausa.fin is None:
            evento = _cerrar_pausa(pausa=pausa, operador=operador, instante=instante, using=using)
        return _confirmar_solicitud(
            operador=operador, clave=clave, operacion=operacion, motivo=None,
            pausa=pausa, evento=evento, instante=instante, using=using,
        )
