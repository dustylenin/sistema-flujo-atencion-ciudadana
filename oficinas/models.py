from django.db import models
from django.db.models.functions import Lower, Trim

from .base import CatalogoBase


class Oficina(CatalogoBase):
    class Meta(CatalogoBase.Meta):
        abstract = False
        constraints = [
            *CatalogoBase.Meta.constraints,
            models.UniqueConstraint(
                Lower(Trim("nombre")), name="oficinas_oficina_nombre_unico"
            ),
        ]
