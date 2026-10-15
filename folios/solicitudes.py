"""Clave, búsqueda y comparación de comprobantes; no ofrece persistencia."""

from uuid import UUID

from django.core.exceptions import ValidationError

from .models import SolicitudOperador


def clave_solicitud(value):
    if not isinstance(value, (str, UUID)):
        raise ValidationError({"solicitud_id": "Se requiere un UUID válido."})
    try:
        return UUID(value) if isinstance(value, str) else value
    except ValueError as error:
        raise ValidationError({"solicitud_id": "Se requiere un UUID válido."}) from error


def buscar_solicitud(*, operador, clave, operacion, motivo, pausa_id, using, folio_id=None):
    # El servicio llamante ya autorizó y mantiene el bloqueo de Usuario.
    solicitud = SolicitudOperador.objects.using(using).filter(
        operador=operador, solicitud_id=clave,
    ).first()
    if solicitud is not None and (
        solicitud.operacion, solicitud.motivo_solicitado, solicitud.pausa_objetivo_id,
        solicitud.folio_objetivo_id,
    ) != (operacion, motivo, pausa_id, folio_id):
        raise ValidationError({"solicitud_id": "Esta clave ya confirmó argumentos diferentes."})
    return solicitud
