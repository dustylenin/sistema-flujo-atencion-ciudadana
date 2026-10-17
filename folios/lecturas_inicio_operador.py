"""Fecha propia para la interfaz; conserva los contratos de los lectores previos."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from django.db.models import Subquery
from django.db.models.functions import JSONObject

from .services_disponibilidad import _folios_actuales
from .services_operador import _alias_lectura, _leer_como_operador


@dataclass(frozen=True)
class InicioActualPropio:
    folio_id: UUID
    estado: str
    inicio_atencion: datetime | None


def consultar_inicio_actual_operador(*, actor) -> InicioActualPropio | None:
    using = _alias_lectura(actor)
    proyeccion = _folios_actuales(using, actor.pk).annotate(
        datos=JSONObject(folio_id="id", estado="estado", inicio_atencion="inicio_atencion"),
    ).values("datos")[:1]
    # Autorización y fecha pertenecen a la misma sentencia/instantánea SQL.
    datos = _leer_como_operador(actor=actor, using=using, proyeccion=Subquery(proyeccion))
    if datos is None:
        return None
    return InicioActualPropio(
        UUID(datos["folio_id"]), datos["estado"],
        datetime.fromisoformat(datos["inicio_atencion"]) if datos["inicio_atencion"] is not None else None,
    )
