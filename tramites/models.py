from django.core.exceptions import ValidationError
from django.db import DatabaseError, models, router, transaction
from django.db.models.functions import Lower, Trim

from oficinas.base import CatalogoBase


class Tramite(CatalogoBase):
    oficina = models.ForeignKey(
        "oficinas.Oficina", on_delete=models.PROTECT, related_name="tramites"
    )

    class Meta(CatalogoBase.Meta):
        abstract = False
        constraints = [
            *CatalogoBase.Meta.constraints,
            models.UniqueConstraint(
                Lower(Trim("nombre")), "oficina", name="tramites_tramite_nombre_por_oficina_unico"
            ),
        ]

    def save(self, *args, **kwargs):
        if args:
            # Mantiene una única resolución del alias para validar y guardar.
            raise TypeError("Tramite.save() requiere argumentos por nombre.")
        if self.oficina_id is None:
            raise ValidationError({"oficina": "La oficina es obligatoria."})
        self._meta.get_field("nombre").clean(self.nombre, self)
        self._meta.get_field("activo").clean(self.activo, self)
        force_insert = kwargs.get("force_insert", False)
        force_update = kwargs.get("force_update", False)
        update_fields = kwargs.get("update_fields")
        if force_insert and (force_update or update_fields):
            raise ValueError("Cannot force both insert and updating in model saving.")
        if update_fields is not None:
            update_fields = frozenset(update_fields)
            kwargs["update_fields"] = update_fields
            # Un conjunto vacío conserva el guardado sin escritura de Django.
            if not update_fields:
                return super().save(**kwargs)
            valid_fields = {
                name
                for field in self._meta.concrete_fields if not field.primary_key
                for name in (field.name, field.attname)
            }
            if update_fields - valid_fields:
                # Django informa los campos inválidos sin ejecutar escrituras.
                return super().save(**kwargs)
        using = kwargs.get("using") or router.db_for_write(type(self), instance=self)
        kwargs["using"] = using
        with transaction.atomic(using=using):
            if self.pk is not None:
                original = (
                    type(self).objects.using(using)
                    .select_for_update()
                    .filter(pk=self.pk)
                    .values_list("oficina_id", flat=True)
                    .first()
                )
                # Consulta también si la instancia fue reconstruida con una PK existente.
                if original is not None and original != self.oficina_id:
                    raise ValidationError({"oficina": "La oficina queda fija desde la creación."})
                if original is None:
                    if force_update:
                        raise DatabaseError("Forced update did not affect any rows.")
                    if update_fields:
                        raise DatabaseError("Save with update_fields did not affect any rows.")
                    # SELECT FOR UPDATE no bloquea una PK ausente. INSERT impide
                    # sobrescribir una fila que aparezca después de la consulta.
                    if not force_insert:
                        kwargs["force_insert"] = True
            return super().save(**kwargs)
