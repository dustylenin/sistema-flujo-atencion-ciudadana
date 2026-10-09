from concurrent.futures import ThreadPoolExecutor

from django.core.exceptions import ValidationError
from django.db import connection, connections, DatabaseError, models, NotSupportedError, transaction

from oficinas.models import Oficina
from oficinas.testing import CatalogosPostgreSQLTestCase, CatalogosPostgreSQLTransactionTestCase
from .models import Tramite


class TramitePostgreSQLTests(CatalogosPostgreSQLTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.norte = Oficina.objects.create(nombre="Norte")
        cls.sur = Oficina.objects.create(nombre="Sur")

    def test_nombre_por_oficina_incluye_inactivos_y_variantes(self):
        Tramite.objects.create(nombre="Solicitud", oficina=self.norte, activo=False)
        for name in ("Solicitud", "solicitud", " SOLICITUD "):
            with self.subTest(name=name):
                self.assert_rechazo_postgresql(
                    lambda: Tramite.objects.create(nombre=name, oficina=self.norte),
                    "23505", "tramites_tramite_nombre_por_oficina_unico",
                )
        other = Tramite.objects.create(nombre=" solicitud ", oficina=self.sur)
        self.assertEqual(other.oficina_id, self.sur.pk)
        self.assertEqual(Tramite.objects.count(), 2)

    def test_oficina_no_puede_cambiar_por_instancia_ni_instancia_reconstruida(self):
        procedure = Tramite.objects.create(nombre="Solicitud", oficina=self.norte)
        procedure.oficina = self.sur
        with self.assertRaises(ValidationError):
            procedure.save()
        with self.assertRaises(ValidationError):
            procedure.save(update_fields=["oficina"])
        with self.assertRaises(ValidationError):
            Tramite(pk=procedure.pk, nombre="Solicitud", oficina=self.sur).save()
        procedure.refresh_from_db()
        self.assertEqual(procedure.oficina_id, self.norte.pk)

    def test_instancia_diferida_tambien_conserva_oficina(self):
        procedure = Tramite.objects.create(nombre="Solicitud", oficina=self.norte)
        deferred = Tramite.objects.only("id", "nombre").get(pk=procedure.pk)
        deferred.oficina_id = self.sur.pk
        with self.assertRaises(ValidationError):
            deferred.save()
        procedure.refresh_from_db()
        self.assertEqual(procedure.oficina_id, self.norte.pk)

    def test_oficina_id_con_update_fields_conserva_oficina_y_estado(self):
        procedure = Tramite.objects.create(nombre="Solicitud", oficina=self.norte)
        procedure.oficina_id = self.sur.pk
        procedure.activo = False
        for fields in (["oficina_id"], ["oficina_id", "activo"], ["activo"]):
            with self.subTest(fields=fields), self.assertRaises(ValidationError):
                procedure.save(update_fields=fields)
        procedure.refresh_from_db()
        self.assertEqual(procedure.oficina_id, self.norte.pk)
        self.assertTrue(procedure.activo)
        procedure.save(update_fields=["oficina_id"])
        procedure.refresh_from_db()
        self.assertEqual(procedure.oficina_id, self.norte.pk)
        self.assertTrue(procedure.activo)

    def test_force_insert_y_force_update_respetan_la_operacion_solicitada(self):
        procedure = Tramite(pk=100001, nombre="Solicitud", oficina=self.norte)
        procedure.save(force_insert=True)
        procedure.refresh_from_db()
        self.assertEqual(procedure.oficina_id, self.norte.pk)
        procedure.activo = False
        procedure.save(force_update=True)
        procedure.refresh_from_db()
        self.assertFalse(procedure.activo)
        procedure.activo = True
        procedure.save(force_update=True, update_fields=["activo"])
        procedure.refresh_from_db()
        self.assertTrue(procedure.activo)
        self.assert_rechazo_postgresql(
            lambda: procedure.save(force_insert=True), "23505", "tramites_tramite_pkey"
        )
        procedure.refresh_from_db()
        self.assertTrue(procedure.activo)
        self.assertEqual(procedure.oficina_id, self.norte.pk)
        self.assertEqual(Tramite.objects.count(), 1)

    def test_actualizaciones_explicitas_de_pk_ausente_no_insertan(self):
        for options in ({"force_update": True}, {"update_fields": ["activo"]}):
            with self.subTest(options=options):
                procedure = Tramite(pk=100002, nombre="Ausente", oficina=self.norte)
                with self.assertRaises(DatabaseError):
                    with transaction.atomic():
                        procedure.save(**options)
                self.assertFalse(Tramite.objects.filter(pk=procedure.pk).exists())
        procedure.save()
        procedure.refresh_from_db()
        self.assertEqual(procedure.oficina_id, self.norte.pk)
        self.assertTrue(procedure.activo)
        self.assertEqual(Tramite.objects.count(), 1)

    def test_update_or_create_no_omite_oficina_fija(self):
        procedure = Tramite.objects.create(nombre="Solicitud", oficina=self.norte)
        with self.assertRaises(ValidationError):
            Tramite.objects.update_or_create(pk=procedure.pk, defaults={"oficina": self.sur})
        procedure.refresh_from_db()
        self.assertEqual(procedure.oficina_id, self.norte.pk)

    def test_vias_masivas_no_cambian_oficina(self):
        procedure = Tramite.objects.create(nombre="Solicitud", oficina=self.norte)
        procedure.oficina = self.sur
        for operation in (
            lambda: Tramite.objects.filter(pk=procedure.pk).update(oficina=self.sur),
            lambda: Tramite.objects.bulk_update([procedure], ["oficina"]),
            lambda: Tramite.objects.bulk_create(
                [procedure], update_conflicts=True, update_fields=["oficina"], unique_fields=["pk"]
            ),
        ):
            with self.assertRaises(NotSupportedError):
                operation()
        procedure.refresh_from_db()
        self.assertEqual(procedure.oficina_id, self.norte.pk)

    def test_estados_conservados_sin_modificar_oficina(self):
        procedure = Tramite.objects.create(nombre="Solicitud", oficina=self.norte)
        other = Tramite.objects.create(nombre="Otro", oficina=self.norte)
        procedure.activo = False
        procedure.save(update_fields=["activo"])
        procedure.refresh_from_db()
        self.assertFalse(procedure.activo)
        self.assertEqual(procedure.oficina_id, self.norte.pk)
        self.norte.refresh_from_db()
        self.assertTrue(self.norte.activo)
        Tramite.objects.filter(pk=procedure.pk).update(activo=True)
        procedure.refresh_from_db()
        self.assertTrue(procedure.activo)
        self.assertEqual(procedure.oficina_id, self.norte.pk)
        procedure.activo = False
        procedure.save()
        procedure.refresh_from_db()
        self.assertFalse(procedure.activo)
        procedure.activo = True
        procedure.save(update_fields=["activo"])
        procedure.refresh_from_db()
        self.assertTrue(procedure.activo)
        self.assertEqual(procedure.oficina_id, self.norte.pk)
        self.norte.refresh_from_db()
        other.refresh_from_db()
        self.assertTrue(self.norte.activo)
        self.assertTrue(other.activo)
        self.assertEqual(other.oficina_id, self.norte.pk)
        self.assertEqual(Tramite.objects.count(), 2)

    def test_borrado_individual_y_queryset_conservan_registro(self):
        procedure = Tramite.objects.create(nombre="Solicitud", oficina=self.norte)
        for operation in (procedure.delete, lambda: self.norte.tramites.all().delete()):
            with self.assertRaises(ValidationError):
                operation()
        self.assertTrue(Tramite.objects.filter(pk=procedure.pk).exists())
        self.assertEqual(Tramite._meta.get_field("oficina").remote_field.on_delete, models.PROTECT)

    def test_base_rechaza_nombre_sin_contenido_y_oficina_inexistente(self):
        procedure = Tramite.objects.create(nombre="Solicitud", oficina=self.norte)
        def empty_name():
            with connection.cursor() as cursor:
                cursor.execute("UPDATE tramites_tramite SET nombre = %s WHERE id = %s", ["  ", procedure.pk])
        self.assert_rechazo_postgresql(empty_name, "23514", "tramites_tramite_nombre_con_contenido")
        with self.assertRaises(ValidationError):
            Tramite(nombre="Solicitud").save()
        def missing_office():
            # PostgreSQL crea la FK diferida; se fuerza su evaluación dentro del savepoint.
            with connection.cursor() as cursor:
                cursor.execute("UPDATE tramites_tramite SET oficina_id = %s WHERE id = %s", [-1, procedure.pk])
                cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
        self.assert_rechazo_postgresql(missing_office, "23503")

    def test_limite_sql_directo_no_garantiza_oficina_inmutable(self):
        # Solo en la base exclusiva de pruebas: documenta el límite sin fingir protección.
        procedure = Tramite.objects.create(nombre="Solicitud", oficina=self.norte)
        with connection.cursor() as cursor:
            cursor.execute("UPDATE tramites_tramite SET oficina_id = %s WHERE id = %s", [self.sur.pk, procedure.pk])
        procedure.refresh_from_db()
        self.assertEqual(procedure.oficina_id, self.sur.pk)


class TramiteConcurrenciaPostgreSQLTests(CatalogosPostgreSQLTransactionTestCase):
    def test_pk_creada_tras_consulta_ausente_no_se_sobrescribe(self):
        # TransactionTestCase permite que las oficinas sean visibles desde otra
        # conexión. No se simulan consultas ni resultados: ambas escrituras son reales.
        north = Oficina.objects.create(nombre="Norte")
        south = Oficina.objects.create(nombre="Sur")
        target_pk = 100003
        candidate = Tramite(pk=target_pk, nombre="Candidato", oficina=south)
        self.assertFalse(Tramite.objects.filter(pk=target_pk).exists())
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_backend_pid()")
            main_pid = cursor.fetchone()[0]

        def insert_on_other_connection():
            try:
                Tramite.objects.create(
                    pk=target_pk, nombre="Original", oficina_id=north.pk, activo=False
                )
                with connections["default"].cursor() as cursor:
                    cursor.execute("SELECT pg_backend_pid()")
                    return cursor.fetchone()[0]
            finally:
                connections["default"].close()

        interleaved = False
        with ThreadPoolExecutor(max_workers=1) as executor:
            def insert_after_lookup(execute, sql, params, many, context):
                nonlocal interleaved
                result = execute(sql, params, many, context)
                if (
                    not interleaved and "FOR UPDATE" in sql.upper()
                    and '"tramites_tramite"' in sql and target_pk in (params or ())
                ):
                    interleaved = True
                    other_pid = executor.submit(insert_on_other_connection).result(timeout=10)
                    self.assertNotEqual(main_pid, other_pid)
                return result

            with connection.execute_wrapper(insert_after_lookup):
                self.assert_rechazo_postgresql(
                    candidate.save, "23505", "tramites_tramite_pkey"
                )

        self.assertTrue(interleaved)
        original = Tramite.objects.get(pk=target_pk)
        original.refresh_from_db()
        self.assertEqual(original.nombre, "Original")
        self.assertEqual(original.oficina_id, north.pk)
        self.assertFalse(original.activo)
        self.assertEqual(Tramite.objects.count(), 1)
        self.assertEqual(Oficina.objects.count(), 2)
