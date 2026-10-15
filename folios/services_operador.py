"""Lecturas propias de Operador, materializadas en una instantánea por lector.

No reservan folios ni escriben eventos o comprobantes. La cola entre páginas
puede cambiar; el cursor nunca sustituye la autorización ni el llamado.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from django.contrib.auth import get_user_model
from django.contrib.postgres.expressions import ArraySubquery
from django.core import signing
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import router
from django.db.models import Q, Subquery
from django.db.models.functions import JSONObject
from django.utils import timezone

from oficinas.models import AsignacionOperadorOficina

from .models import Folio
from .services_disponibilidad import _folios_actuales, _identidad_actor


_TAMANO_PAGINA = 50
_SALT_CURSOR = "folios.pendientes_operador.v1"
_CAMPOS_FOLIO = {
    "folio_id": "id",
    "nombre_completo": "nombre_completo",
    "estado": "estado",
    "llegada_original": "llegada_original",
    "oficina_id": "oficina_id",
    "oficina_nombre": "oficina__nombre",
    "tramite_id": "tramite_id",
    "tramite_nombre": "tramite__nombre",
}


@dataclass(frozen=True)
class FolioPendiente:
    folio_id: UUID
    nombre_completo: str
    estado: str
    llegada_original: datetime
    oficina_id: int
    oficina_nombre: str
    tramite_id: int
    tramite_nombre: str


@dataclass(frozen=True)
class FolioActualPropio(FolioPendiente):
    operador_responsable_id: int


@dataclass(frozen=True)
class PaginaPendientesOperador:
    pendientes: tuple[FolioPendiente, ...]
    cursor_siguiente: str | None


def _leer_cursor(cursor):
    if cursor is None:
        return None
    try:
        if not isinstance(cursor, str) or not cursor or len(cursor) > 512:
            raise ValueError
        datos = signing.loads(cursor, salt=_SALT_CURSOR)
        if not isinstance(datos, dict) or set(datos) != {"llegada_original", "folio_id"}:
            raise ValueError
        if not all(isinstance(valor, str) for valor in datos.values()):
            raise ValueError
        llegada = datetime.fromisoformat(datos["llegada_original"])
        if timezone.is_naive(llegada):
            raise ValueError
        return llegada, UUID(datos["folio_id"])
    except (signing.BadSignature, ValueError, TypeError) as error:
        raise ValidationError({"cursor": "Se requiere un cursor de pendientes válido."}) from error


def _crear_cursor(folio):
    # Sin caducidad funcional ni permisos embebidos. Cada página reautoriza.
    return signing.dumps({
        "llegada_original": folio.llegada_original.isoformat(),
        "folio_id": str(folio.folio_id),
    }, salt=_SALT_CURSOR)


def _alias_lectura(actor):
    using = router.db_for_read(Folio)
    _identidad_actor(actor, using)
    return using


def _leer_como_operador(*, actor, using, proyeccion):
    Usuario = get_user_model()
    # La raíz autorizada conserva una fila aunque la subconsulta esté vacía.
    # Rol/actividad/asignaciones y datos pertenecen a la misma sentencia SQL.
    fila = Usuario.objects.using(using).filter(
        pk=actor.pk, is_active=True, rol=Usuario.Rol.OPERADOR,
    ).annotate(lectura=proyeccion).values("lectura").first()
    if fila is None:
        raise PermissionDenied("Se requiere una cuenta OPERADOR autenticada y activa.")
    return fila["lectura"]


def _datos_folio(datos):
    # JSON solo se usa dentro de la proyección SQL; no sale como dict mutable.
    return {
        **datos,
        "folio_id": UUID(datos["folio_id"]),
        "llegada_original": datetime.fromisoformat(datos["llegada_original"]),
    }


def consultar_pendientes_operador(*, actor, cursor=None) -> PaginaPendientesOperador:
    using = _alias_lectura(actor)
    posicion = _leer_cursor(cursor)
    oficinas = AsignacionOperadorOficina.objects.using(using).filter(
        operador_id=actor.pk, activo=True,
    ).values("oficina_id")
    pendientes = Folio.objects.using(using).filter(
        estado=Folio.Estado.EN_ESPERA, oficina_id__in=Subquery(oficinas),
    )
    if posicion is not None:
        llegada, folio_id = posicion
        pendientes = pendientes.filter(
            Q(llegada_original__gt=llegada)
            | Q(llegada_original=llegada, id__gt=folio_id),
        )
    proyeccion = pendientes.order_by("llegada_original", "id").annotate(
        datos=JSONObject(**_CAMPOS_FOLIO),
    ).values("datos")[:_TAMANO_PAGINA + 1]
    filas = _leer_como_operador(actor=actor, using=using, proyeccion=ArraySubquery(proyeccion))
    elementos = tuple(FolioPendiente(**_datos_folio(fila)) for fila in filas[:_TAMANO_PAGINA])
    siguiente = _crear_cursor(elementos[-1]) if len(filas) > _TAMANO_PAGINA else None
    return PaginaPendientesOperador(pendientes=elementos, cursor_siguiente=siguiente)


def consultar_folio_actual_operador(*, actor) -> FolioActualPropio | None:
    using = _alias_lectura(actor)
    # Reutiliza el criterio global de disponibilidad sin ampliar su contrato.
    proyeccion = _folios_actuales(using, actor.pk).annotate(
        datos=JSONObject(**_CAMPOS_FOLIO, operador_responsable_id="operador_responsable_id"),
    ).values("datos")[:1]
    datos = _leer_como_operador(actor=actor, using=using, proyeccion=Subquery(proyeccion))
    return FolioActualPropio(**_datos_folio(datos)) if datos is not None else None
