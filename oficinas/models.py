from django.conf import settings
from django.db import models, NotSupportedError
from django.db.models.functions import Lower, Trim
from django.utils import timezone

from .base import CatalogoBase
from .managers import EscrituraServiciosManager


class Oficina(CatalogoBase):
    class Meta(CatalogoBase.Meta):
        abstract = False
        constraints = [
            *CatalogoBase.Meta.constraints,
            models.UniqueConstraint(
                Lower(Trim("nombre")), name="oficinas_oficina_nombre_unico"
            ),
        ]


class RegistroServicio(models.Model):
    """Barrera de escritura pública; no ofrece opciones para omitirla."""

    objects = EscrituraServiciosManager()

    class Meta:
        abstract = True
        base_manager_name = "objects"
        default_manager_name = "objects"

    def save(self, *args, **kwargs):
        raise NotSupportedError("La persistencia de este registro requiere el servicio autorizado.")

    save.alters_data = True

    def delete(self, *args, **kwargs):
        raise NotSupportedError("Las asignaciones y sus eventos se conservan; no se eliminan.")

    delete.alters_data = True


class AsignacionOperadorOficina(RegistroServicio):
    operador = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="asignaciones_oficinas"
    )
    oficina = models.ForeignKey(
        Oficina, on_delete=models.PROTECT, related_name="asignaciones_operadores"
    )
    activo = models.BooleanField(default=True)

    class Meta(RegistroServicio.Meta):
        abstract = False
        constraints = [
            models.UniqueConstraint(
                fields=["operador", "oficina"], name="oficinas_asignacion_operador_oficina_unica"
            ),
        ]


class EventoAsignacion(RegistroServicio):
    """Historial durable de creación/reactivación, no auditoría global."""

    class Operacion(models.TextChoices):
        CREACION = "CREACION", "Creación"
        REACTIVACION = "REACTIVACION", "Reactivación"

    asignacion = models.ForeignKey(
        AsignacionOperadorOficina, on_delete=models.PROTECT, related_name="eventos"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="eventos_asignaciones"
    )
    fecha = models.DateTimeField(default=timezone.now, editable=False)
    operacion = models.CharField(max_length=12, choices=Operacion.choices)
    activo_anterior = models.BooleanField(null=True)
    activo_nuevo = models.BooleanField()

    class Meta(RegistroServicio.Meta):
        abstract = False
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(operacion="CREACION", activo_anterior__isnull=True, activo_nuevo=True)
                    | models.Q(
                        operacion="REACTIVACION", activo_anterior=False,
                        activo_anterior__isnull=False, activo_nuevo=True,
                    )
                ),
                name="oficinas_eventoasignacion_estados_coherentes",
            ),
        ]
