"""Registro inicial e historial de creación; no auditoría global."""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, NotSupportedError

from .managers import FoliosForeignKey, FoliosManager


def validar_nombre_completo(value):
    if not value.strip():
        raise ValidationError("El nombre completo debe tener contenido.", code="nombre_vacio")


class RegistroFolioServicio(models.Model):
    objects = FoliosManager()

    class Meta:
        abstract = True
        base_manager_name = "objects"
        default_manager_name = "objects"

    def save(self, *args, **kwargs):
        raise NotSupportedError("La escritura requiere el servicio autorizado de registro.")

    save.alters_data = True

    def delete(self, *args, **kwargs):
        raise NotSupportedError("Los folios y sus eventos se conservan; no se eliminan.")

    delete.alters_data = True


class Folio(RegistroFolioServicio):
    class Estado(models.TextChoices):
        EN_ESPERA = "EN_ESPERA", "En espera"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre_completo = models.TextField(validators=[validar_nombre_completo])
    correo = models.EmailField(max_length=254, blank=True, default="")
    telefono = models.TextField(blank=True, default="")
    oficina = FoliosForeignKey(
        "oficinas.Oficina", on_delete=models.PROTECT, related_name="folios"
    )
    tramite = FoliosForeignKey(
        "tramites.Tramite", on_delete=models.PROTECT, related_name="folios"
    )
    registrado_por = FoliosForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="folios_registrados"
    )
    llegada_original = models.DateTimeField(editable=False)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.EN_ESPERA)
    operador_responsable = FoliosForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="folios_responsables", null=True, blank=True, default=None,
    )

    class Meta(RegistroFolioServicio.Meta):
        abstract = False
        constraints = [
            models.CheckConstraint(
                condition=models.Q(nombre_completo__regex=r"\S"),
                name="folios_folio_nombre_con_contenido",
            ),
            # Solo esta entrega: el llamado requerirá una nueva migración.
            models.CheckConstraint(
                condition=models.Q(estado="EN_ESPERA", operador_responsable__isnull=True),
                name="folios_folio_estado_inicial",
            ),
        ]


class EventoFolio(RegistroFolioServicio):
    class Operacion(models.TextChoices):
        CREACION = "CREACION", "Creación"

    folio = FoliosForeignKey(Folio, on_delete=models.PROTECT, related_name="eventos")
    actor = FoliosForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="eventos_folios"
    )
    fecha = models.DateTimeField(editable=False)
    operacion = models.CharField(max_length=12, choices=Operacion.choices)
    estado_anterior = models.CharField(max_length=12, null=True)
    estado_nuevo = models.CharField(max_length=12)
    datos_iniciales = models.JSONField()

    class Meta(RegistroFolioServicio.Meta):
        abstract = False
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    operacion="CREACION", estado_anterior__isnull=True, estado_nuevo="EN_ESPERA"
                ),
                name="folios_evento_estados_creacion",
            ),
            models.UniqueConstraint(
                fields=["folio"], condition=models.Q(operacion="CREACION"),
                name="folios_evento_creacion_unica",
            ),
        ]
