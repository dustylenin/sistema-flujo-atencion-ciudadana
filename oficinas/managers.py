"""Las asignaciones y sus eventos se escriben exclusivamente desde servicios.

SQL directo, deserializadores y APIs internas quedan fuera de esta barrera.
Las variantes asíncronas de Django delegan en estos mismos métodos.
"""

from django.db import models, NotSupportedError


class EscrituraServiciosQuerySet(models.QuerySet):
    def _rechazar(self, *args, **kwargs):
        raise NotSupportedError("Use los servicios de creación o reactivación de asignaciones.")

    _rechazar.alters_data = True
    create = _rechazar
    update = _rechazar
    get_or_create = _rechazar
    update_or_create = _rechazar
    bulk_create = _rechazar
    bulk_update = _rechazar
    delete = _rechazar


EscrituraServiciosManager = models.Manager.from_queryset(EscrituraServiciosQuerySet)
