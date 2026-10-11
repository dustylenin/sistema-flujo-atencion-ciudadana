"""Registro por Recepción: estado actual, bloqueos y persistencia conjunta."""

from dataclasses import dataclass
from uuid import UUID

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models, router, transaction
from django.utils import timezone

from oficinas.models import Oficina
from tramites.models import Tramite

from .models import EventoFolio, Folio


@dataclass(frozen=True)
class ResultadoRegistroFolio:
    folio_id: UUID
    evento_id: int


def _crear_evento(*, folio, actor, using):
    # Copia de valores ya validados por el servicio, sin payload del cliente.
    evento = EventoFolio(
        folio=folio, actor=actor, fecha=folio.llegada_original,
        operacion=EventoFolio.Operacion.CREACION,
        estado_anterior=None, estado_nuevo=Folio.Estado.EN_ESPERA,
        datos_iniciales={
            "nombre_completo": folio.nombre_completo,
            "correo": folio.correo,
            "telefono": folio.telefono,
            "oficina_id": folio.oficina_id,
            "tramite_id": folio.tramite_id,
            "llegada_original": folio.llegada_original.isoformat(),
        },
    )
    models.Model.save(evento, using=using, force_insert=True)
    return evento


def _crear_folio_con_evento(*, actor, oficina, tramite, datos, using):
    folio = Folio(
        **datos, oficina=oficina, tramite=tramite, registrado_por=actor,
        llegada_original=timezone.now(), estado=Folio.Estado.EN_ESPERA,
        operador_responsable=None,
    )
    models.Model.save(folio, using=using, force_insert=True)
    evento = _crear_evento(folio=folio, actor=actor, using=using)
    return ResultadoRegistroFolio(folio.pk, evento.pk)


def registrar_folio(
    *, actor, nombre_completo, oficina_id, tramite_id, correo="", telefono="",
) -> ResultadoRegistroFolio:
    Usuario = get_user_model()
    using = router.db_for_write(Folio)
    if (
        not isinstance(actor, Usuario) or not actor.is_authenticated
        or actor.pk is None or actor._state.adding or actor._state.db != using
    ):
        raise PermissionDenied("Se requiere una cuenta de Recepción autenticada y activa.")

    with transaction.atomic(using=using):
        # Compatible con asignaciones: cuentas antes de oficina; después trámite.
        recepcion = Usuario.objects.using(using).select_for_update().filter(pk=actor.pk).first()
        if recepcion is None or not recepcion.is_active or recepcion.rol != Usuario.Rol.RECEPCION:
            raise PermissionDenied("Se requiere una cuenta de Recepción autenticada y activa.")

        datos = {}
        for nombre, valor in (
            ("nombre_completo", nombre_completo), ("correo", correo), ("telefono", telefono),
        ):
            if not isinstance(valor, str):
                raise ValidationError({nombre: "Se requiere texto; los opcionales pueden ser vacíos."})
            try:
                datos[nombre] = Folio._meta.get_field(nombre).clean(valor, None)
            except ValidationError as error:
                raise ValidationError({nombre: error.messages}) from error

        oficina = Oficina.objects.using(using).select_for_update().filter(pk=oficina_id).first()
        if oficina is None or not oficina.activo:
            raise ValidationError({"oficina": "Se requiere una oficina existente y activa."})
        tramite = Tramite.objects.using(using).select_for_update().filter(pk=tramite_id).first()
        if tramite is None or not tramite.activo or tramite.oficina_id != oficina.pk:
            raise ValidationError({"tramite": "Se requiere un trámite activo de la oficina seleccionada."})
        return _crear_folio_con_evento(
            actor=recepcion, oficina=oficina, tramite=tramite, datos=datos, using=using,
        )
