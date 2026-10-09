"""Protecciones compartidas de los catálogos en las vías públicas del ORM.

No interceptan SQL directo, deserializadores ni APIs internas de Django.
Los estados no producen cambios automáticos en otros registros ni auditoría.
"""

from django.core.exceptions import ValidationError
from django.db import NotSupportedError, models


def validar_nombre(value):
    if not value.strip():
        raise ValidationError("El nombre debe tener contenido.", code="nombre_vacio")


class CatalogoQuerySet(models.QuerySet):
    def delete(self):
        raise ValidationError("Los registros del catálogo se desactivan, no se eliminan.")

    delete.alters_data = True
    delete.queryset_only = True

    def update(self, **kwargs):
        # Las expresiones y otras columnas omitirían las validaciones de save().
        if set(kwargs) != {"activo"} or type(kwargs["activo"]) is not bool:
            raise NotSupportedError("update() solo admite activo=True o activo=False.")
        return super().update(**kwargs)

    update.alters_data = True

    def bulk_create(self, *args, **kwargs):
        raise NotSupportedError("bulk_create() no está admitido; utilice create() o save().")

    bulk_create.alters_data = True

    def bulk_update(self, *args, **kwargs):
        raise NotSupportedError("bulk_update() no está admitido; utilice save() o update(activo=...).")

    bulk_update.alters_data = True


class CatalogoBase(models.Model):
    nombre = models.CharField(max_length=150, validators=[validar_nombre])
    activo = models.BooleanField(default=True)

    objects = CatalogoQuerySet.as_manager()

    class Meta:
        abstract = True
        base_manager_name = "objects"
        default_manager_name = "objects"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(nombre__regex=r"\S"),
                name="%(app_label)s_%(class)s_nombre_con_contenido",
            ),
        ]

    def save(self, *args, **kwargs):
        # Valida contenido y longitud sin alterar la grafía almacenada.
        self._meta.get_field("nombre").clean(self.nombre, self)
        self._meta.get_field("activo").clean(self.activo, self)
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Los registros del catálogo se desactivan, no se eliminan.")

    delete.alters_data = True
