from asgiref.sync import async_to_sync
from django.core.exceptions import ValidationError
from django.db import connection, models, NotSupportedError
from django.test import SimpleTestCase

from tramites.models import Tramite
from .models import Oficina
from .testing import CatalogosPostgreSQLTestCase


class CatalogosSinBaseTests(SimpleTestCase):
    def test_nombre_obligatorio_y_con_contenido_antes_de_guardar(self):
        for model, kwargs in ((Oficina, {}), (Tramite, {"oficina_id": 1})):
            for name in (None, "", "   ", "\t\n", "n" * 151):
                with self.subTest(model=model.__name__, name=name):
                    with self.assertRaises(ValidationError):
                        model(nombre=name, **kwargs).save()

    def test_tramite_requiere_oficina(self):
        with self.assertRaises(ValidationError):
            Tramite(nombre="Solicitud").save()

    def test_opciones_de_guardado_sin_escritura_conservan_semantica_django(self):
        procedure = Tramite(pk=1, nombre="Solicitud", oficina_id=1)
        for options in (
            {"force_insert": True, "force_update": True},
            {"force_insert": True, "update_fields": ["activo"]},
            {"update_fields": ["inexistente"]},
            {"update_fields": ["id"]},
        ):
            with self.subTest(options=options), self.assertRaises(ValueError):
                procedure.save(**options)
        for options in ({}, {"force_insert": True}, {"force_update": True}):
            with self.subTest(options=options):
                self.assertIsNone(procedure.save(update_fields=[], **options))

    def test_borrado_individual_y_queryset_rechazados_sin_consultas(self):
        for model in (Oficina, Tramite):
            with self.subTest(model=model.__name__):
                with self.assertRaises(ValidationError):
                    model(pk=1).delete()
                for manager in (model.objects, model._base_manager, model._default_manager):
                    with self.assertRaises(ValidationError):
                        manager.all().delete()

    def test_operaciones_masivas_omitidas_se_rechazan_sin_consultas(self):
        for model in (Oficina, Tramite):
            for operation in (
                lambda: model.objects.bulk_create([model(nombre="Nuevo")]),
                lambda: model.objects.bulk_update([model(pk=1)], ["activo"]),
                lambda: model.objects.all().update(nombre="Nuevo"),
                lambda: model.objects.all().update(activo=models.F("activo")),
                lambda: model.objects.all().update(activo=None),
                lambda: model.objects.all().update(activo=False, nombre="Nuevo"),
            ):
                with self.subTest(model=model.__name__), self.assertRaises(NotSupportedError):
                    operation()
        for field in ("oficina", "oficina_id"):
            with self.assertRaises(NotSupportedError):
                Tramite.objects.all().update(**{field: 2})

    def test_variantes_asincronas_conservan_los_bloqueos(self):
        for model in (Oficina, Tramite):
            with self.subTest(model=model.__name__):
                with self.assertRaises(ValidationError):
                    async_to_sync(model(pk=1).adelete)()
                with self.assertRaises(ValidationError):
                    async_to_sync(model.objects.all().adelete)()
                with self.assertRaises(NotSupportedError):
                    async_to_sync(model.objects.all().aupdate)(nombre="Nuevo")
                with self.assertRaises(NotSupportedError):
                    async_to_sync(model.objects.all().abulk_create)([])
                with self.assertRaises(NotSupportedError):
                    async_to_sync(model.objects.all().abulk_update)([], ["activo"])


class OficinaPostgreSQLTests(CatalogosPostgreSQLTestCase):
    def test_creacion_y_recuperacion_sin_alterar_nombre(self):
        office = Oficina.objects.create(nombre="  Ventanilla Norte  ", activo=False)
        saved = Oficina.objects.get(pk=office.pk)
        self.assertEqual(saved.nombre, "  Ventanilla Norte  ")
        self.assertFalse(saved.activo)

    def test_unicidad_global_incluye_inactivas_y_variantes(self):
        Oficina.objects.create(nombre="Ventanilla Norte", activo=False)
        for name in ("Ventanilla Norte", "ventanilla norte", "  VENTANILLA NORTE  "):
            with self.subTest(name=name):
                self.assert_rechazo_postgresql(
                    lambda: Oficina.objects.create(nombre=name),
                    "23505", "oficinas_oficina_nombre_unico",
                )
        self.assertEqual(Oficina.objects.count(), 1)

    def test_full_clean_detecta_unicidad(self):
        Oficina.objects.create(nombre="Norte")
        with self.assertRaises(ValidationError):
            Oficina(nombre=" norte ").full_clean()

    def test_restricciones_nombre_incluso_por_sql_en_base_de_pruebas(self):
        office = Oficina.objects.create(nombre="Norte")
        for name, state, constraint in (
            (None, "23502", None),
            ("", "23514", "oficinas_oficina_nombre_con_contenido"),
            ("   ", "23514", "oficinas_oficina_nombre_con_contenido"),
        ):
            def write():
                with connection.cursor() as cursor:
                    cursor.execute("UPDATE oficinas_oficina SET nombre = %s WHERE id = %s", [name, office.pk])
            with self.subTest(name=name):
                self.assert_rechazo_postgresql(write, state, constraint)

    def test_desactivacion_y_reactivacion_conservan_registros_sin_cascada(self):
        office = Oficina.objects.create(nombre="Norte")
        procedure = Tramite.objects.create(nombre="Solicitud", oficina=office)
        office.activo = False
        office.save(update_fields=["activo"])
        procedure.refresh_from_db()
        self.assertTrue(procedure.activo)
        self.assertEqual(procedure.oficina_id, office.pk)
        Oficina.objects.filter(pk=office.pk).update(activo=True)
        office.refresh_from_db()
        self.assertTrue(office.activo)
        self.assertEqual(Oficina.objects.count(), 1)
        self.assertEqual(Tramite.objects.count(), 1)

    def test_borrado_no_elimina_oficina_ni_referencias(self):
        for with_procedure in (False, True):
            office = Oficina.objects.create(nombre=str(with_procedure))
            if with_procedure:
                Tramite.objects.create(nombre="Solicitud", oficina=office)
            for operation in (office.delete, lambda: Oficina.objects.filter(pk=office.pk).delete()):
                with self.assertRaises(ValidationError):
                    operation()
            self.assertTrue(Oficina.objects.filter(pk=office.pk).exists())
        self.assertEqual(Tramite.objects.count(), 1)
