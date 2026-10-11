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


def validar_motivo(value):
    if not value.strip():
        raise ValidationError("El motivo debe tener contenido.", code="motivo_vacio")


class PausaOperador(RegistroFolioServicio):
    operador = FoliosForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="pausas_operador"
    )
    motivo = models.TextField(validators=[validar_motivo])
    inicio = models.DateTimeField(editable=False)
    fin = models.DateTimeField(null=True, blank=True, editable=False)
    folio_contexto = FoliosForeignKey(
        Folio, on_delete=models.PROTECT, null=True, blank=True, related_name="pausas_contexto"
    )
    oficina_contexto = FoliosForeignKey(
        "oficinas.Oficina", on_delete=models.PROTECT, null=True, blank=True,
        related_name="pausas_contexto",
    )

    class Meta(RegistroFolioServicio.Meta):
        abstract = False
        constraints = [
            models.UniqueConstraint(
                fields=["operador"], condition=models.Q(fin__isnull=True),
                name="folios_pausa_abierta_unica",
            ),
            models.CheckConstraint(
                condition=models.Q(motivo__regex=r"\S"), name="folios_pausa_motivo_contenido",
            ),
            models.CheckConstraint(
                condition=models.Q(fin__isnull=True) | models.Q(fin__gte=models.F("inicio")),
                name="folios_pausa_tiempos_coherentes",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(folio_contexto__isnull=True, oficina_contexto__isnull=True)
                    | models.Q(folio_contexto__isnull=False, oficina_contexto__isnull=False)
                ),
                name="folios_pausa_contexto_coherente",
            ),
        ]


class EventoDisponibilidad(RegistroFolioServicio):
    class Operacion(models.TextChoices):
        PAUSA = "PAUSA", "Pausa"
        REANUDACION = "REANUDACION", "Reanudación"

    pausa = FoliosForeignKey(PausaOperador, on_delete=models.PROTECT, related_name="eventos")
    actor = FoliosForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="eventos_disponibilidad"
    )
    fecha = models.DateTimeField(editable=False)
    operacion = models.CharField(max_length=11, choices=Operacion.choices)

    class Meta(RegistroFolioServicio.Meta):
        abstract = False
        constraints = [
            models.CheckConstraint(
                condition=models.Q(operacion__in=["PAUSA", "REANUDACION"]),
                name="folios_disponibilidad_operacion",
            ),
            models.UniqueConstraint(
                fields=["pausa", "operacion"], name="folios_disponibilidad_evento_unico",
            ),
        ]


class SolicitudOperador(RegistroFolioServicio):
    class Operacion(models.TextChoices):
        PAUSAR = "PAUSAR", "Pausar"
        REANUDAR = "REANUDAR", "Reanudar"

    class Resultado(models.TextChoices):
        PAUSADA = "PAUSADA", "Pausada"
        YA_EN_PAUSA = "YA_EN_PAUSA", "Ya en pausa"
        REANUDADA = "REANUDADA", "Reanudada"
        YA_REANUDADA = "YA_REANUDADA", "Ya reanudada"

    operador = FoliosForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="solicitudes_operador"
    )
    solicitud_id = models.UUIDField()
    operacion = models.CharField(max_length=8, choices=Operacion.choices)
    motivo_solicitado = models.TextField(null=True, blank=True)
    pausa_objetivo = FoliosForeignKey(
        PausaOperador, on_delete=models.PROTECT, null=True, blank=True,
        related_name="solicitudes_reanudacion",
    )
    resultado = models.CharField(max_length=16, choices=Resultado.choices)
    pausa_resultado = FoliosForeignKey(
        PausaOperador, on_delete=models.PROTECT, related_name="solicitudes_resultado"
    )
    evento_resultado = FoliosForeignKey(
        EventoDisponibilidad, on_delete=models.PROTECT, null=True, blank=True,
        related_name="solicitudes_resultado",
    )
    confirmada_en = models.DateTimeField(editable=False)

    class Meta(RegistroFolioServicio.Meta):
        abstract = False
        constraints = [
            models.UniqueConstraint(
                fields=["operador", "solicitud_id"], name="folios_solicitud_operador_unica",
            ),
            models.CheckConstraint(
                condition=(
                    (
                        models.Q(
                            operacion="PAUSAR", motivo_solicitado__isnull=False,
                            motivo_solicitado__regex=r"\S", pausa_objetivo__isnull=True,
                            resultado__in=["PAUSADA", "YA_EN_PAUSA"],
                        )
                        | models.Q(
                            operacion="REANUDAR", motivo_solicitado__isnull=True,
                            pausa_objetivo__isnull=False,
                            pausa_objetivo=models.F("pausa_resultado"),
                            resultado__in=["REANUDADA", "YA_REANUDADA"],
                        )
                    )
                    & (
                        models.Q(resultado__in=["PAUSADA", "REANUDADA"], evento_resultado__isnull=False)
                        | models.Q(
                            resultado__in=["YA_EN_PAUSA", "YA_REANUDADA"], evento_resultado__isnull=True,
                        )
                    )
                ),
                name="folios_solicitud_campos_coherentes",
            ),
        ]
