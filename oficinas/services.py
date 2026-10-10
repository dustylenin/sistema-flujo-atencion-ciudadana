"""Creación/reactivación con autorización actual, bloqueos y evento atómico.

Las primitivas privadas usan la persistencia interna de Django; ninguna vía
pública de los modelos permite invocarlas mediante una opción de omisión.
Retirada, folios y auditoría global siguen fuera del alcance.
"""

from dataclasses import dataclass
from enum import StrEnum

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models, router, transaction

from .models import AsignacionOperadorOficina, EventoAsignacion, Oficina


class EstadoAsignacion(StrEnum):
    CREADA = "CREADA"
    REACTIVADA = "REACTIVADA"
    YA_ACTIVA = "YA_ACTIVA"
    REQUIERE_REACTIVACION = "REQUIERE_REACTIVACION"
    ASIGNACION_INEXISTENTE = "ASIGNACION_INEXISTENTE"


@dataclass(frozen=True)
class ResultadoAsignacion:
    estado: EstadoAsignacion
    asignacion_id: int | None
    evento_id: int | None = None


def _registrar_evento(*, asignacion, actor, operacion, anterior, using):
    evento = EventoAsignacion(
        asignacion=asignacion, actor=actor, operacion=operacion,
        activo_anterior=anterior, activo_nuevo=True,
    )
    models.Model.save(evento, using=using, force_insert=True)
    return evento


def _crear_con_evento(*, operador, oficina, actor, using):
    asignacion = AsignacionOperadorOficina(operador=operador, oficina=oficina, activo=True)
    models.Model.save(asignacion, using=using, force_insert=True)
    evento = _registrar_evento(
        asignacion=asignacion, actor=actor, operacion=EventoAsignacion.Operacion.CREACION,
        anterior=None, using=using,
    )
    return ResultadoAsignacion(EstadoAsignacion.CREADA, asignacion.pk, evento.pk)


def _reactivar_con_evento(*, asignacion, actor, using):
    asignacion.activo = True
    models.Model.save(asignacion, using=using, force_update=True, update_fields=["activo"])
    evento = _registrar_evento(
        asignacion=asignacion, actor=actor, operacion=EventoAsignacion.Operacion.REACTIVACION,
        anterior=False, using=using,
    )
    return ResultadoAsignacion(EstadoAsignacion.REACTIVADA, asignacion.pk, evento.pk)


def _asignar(*, actor, operador_id, oficina_id, reactivar):
    Usuario = get_user_model()
    using = router.db_for_write(AsignacionOperadorOficina)
    if (
        not isinstance(actor, Usuario) or not actor.is_authenticated
        or actor.pk is None or actor._state.adding or actor._state.db != using
    ):
        raise PermissionDenied("Se requiere un administrador funcional autenticado y activo.")
    with transaction.atomic(using=using):
        # Orden compartido: cuentas por PK, oficina, asignación. Incluso cuando
        # no existe la pareja, la fila del operador serializa su creación.
        cuentas = {}
        for pk in sorted({actor.pk, operador_id}):
            cuentas[pk] = Usuario.objects.using(using).select_for_update().filter(pk=pk).first()
        administrador = cuentas[actor.pk]
        if (
            administrador is None or not administrador.is_active
            or administrador.rol != Usuario.Rol.ADMINISTRADOR
        ):
            raise PermissionDenied("Se requiere un administrador funcional autenticado y activo.")
        operador = cuentas[operador_id]
        if operador is None:
            raise ValidationError({"operador": "La cuenta destino no existe."})
        oficina = Oficina.objects.using(using).select_for_update().filter(pk=oficina_id).first()
        if oficina is None:
            raise ValidationError({"oficina": "La oficina no existe."})
        asignacion = (
            AsignacionOperadorOficina.objects.using(using).select_for_update()
            .filter(operador_id=operador_id, oficina_id=oficina_id).first()
        )
        if asignacion is not None and asignacion.activo:
            return ResultadoAsignacion(EstadoAsignacion.YA_ACTIVA, asignacion.pk)
        if asignacion is not None and not reactivar:
            return ResultadoAsignacion(EstadoAsignacion.REQUIERE_REACTIVACION, asignacion.pk)
        if asignacion is None and reactivar:
            return ResultadoAsignacion(EstadoAsignacion.ASIGNACION_INEXISTENTE, None)
        if operador.rol != Usuario.Rol.OPERADOR or not operador.is_active:
            raise ValidationError({"operador": "Se requiere una cuenta OPERADOR activa."})
        if not oficina.activo:
            raise ValidationError({"oficina": "Se requiere una oficina activa."})
        if reactivar:
            return _reactivar_con_evento(asignacion=asignacion, actor=administrador, using=using)
        return _crear_con_evento(operador=operador, oficina=oficina, actor=administrador, using=using)


def crear_asignacion(*, actor, operador_id, oficina_id) -> ResultadoAsignacion:
    return _asignar(actor=actor, operador_id=operador_id, oficina_id=oficina_id, reactivar=False)


def reactivar_asignacion(*, actor, operador_id, oficina_id) -> ResultadoAsignacion:
    return _asignar(actor=actor, operador_id=operador_id, oficina_id=oficina_id, reactivar=True)
