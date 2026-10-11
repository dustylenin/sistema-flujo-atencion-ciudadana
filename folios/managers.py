"""Barrera del ORM público; SQL y APIs internas pueden eludirla.

Los métodos asíncronos de Django delegan en estas mismas operaciones.
"""

from django.db import models, NotSupportedError
from django.db.models.fields.related_descriptors import ReverseManyToOneDescriptor
from django.utils.functional import cached_property


class FoliosQuerySet(models.QuerySet):
    def _rechazar(self, *args, **kwargs):
        raise NotSupportedError("Use el servicio autorizado de registro de folios.")

    _rechazar.alters_data = True
    create = _rechazar
    update = _rechazar
    get_or_create = _rechazar
    update_or_create = _rechazar
    bulk_create = _rechazar
    bulk_update = _rechazar
    delete = _rechazar


FoliosManager = models.Manager.from_queryset(FoliosQuerySet)


class RelacionesFoliosProtegidas:
    def __call__(self, *, manager):
        # Django construye otra clase al elegir relacion(manager="objects").
        # Conserva su selección y sus filtros, envolviendo también esa clase.
        seleccionado = super().__call__(manager=manager)
        return _proteger_manager_relacion(type(seleccionado))(self.instance)

    # Incluso sin filas afectadas: bulk=False no siempre llega a save/update.
    def _rechazar_relacion(self, *args, **kwargs):
        raise NotSupportedError("Las relaciones de folios solo cambian mediante servicios.")

    _rechazar_relacion.alters_data = True
    add = _rechazar_relacion
    remove = _rechazar_relacion
    clear = _rechazar_relacion
    set = _rechazar_relacion

    async def _arechazar_relacion(self, *args, **kwargs):
        self._rechazar_relacion()

    _arechazar_relacion.alters_data = True
    aadd = _arechazar_relacion
    aremove = _arechazar_relacion
    aclear = _arechazar_relacion
    aset = _arechazar_relacion


def _proteger_manager_relacion(manager_class):
    class RelatedManager(RelacionesFoliosProtegidas, manager_class):
        pass

    return RelatedManager


class FoliosReverseDescriptor(ReverseManyToOneDescriptor):
    @cached_property
    def related_manager_cls(self):
        return _proteger_manager_relacion(super().related_manager_cls)


class FoliosForeignKey(models.ForeignKey):
    """FK normal en PostgreSQL, con mutación inversa pública rechazada."""

    related_accessor_class = FoliosReverseDescriptor
