"""Pruebas del registro inicial, exclusivamente en PostgreSQL aislado."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
from threading import Event
from time import monotonic, sleep
from unittest.mock import patch
from uuid import UUID

from asgiref.sync import async_to_sync
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection, connections, IntegrityError, models, NotSupportedError, transaction
from django.db.models.deletion import ProtectedError
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from oficinas.models import Oficina
from oficinas.testing import CatalogosPostgreSQLTestCase, CatalogosPostgreSQLTransactionTestCase
from tramites.models import Tramite
from usuarios.models import Usuario

from .models import EventoFolio, Folio
from .services import registrar_folio


class FolioFixturesMixin:
    def preparar(self):
        self.actor = Usuario.objects.create_user(username="recepcion", rol=Usuario.Rol.RECEPCION)
        self.oficina = Oficina.objects.create(nombre="Norte")
        self.tramite = Tramite.objects.create(nombre="Solicitud", oficina=self.oficina)

    def registrar(self, **overrides):
        kwargs = dict(
            actor=self.actor, nombre_completo="  María Pérez  ",
            oficina_id=self.oficina.pk, tramite_id=self.tramite.pk,
        )
        kwargs.update(overrides)
        return registrar_folio(**kwargs)

    def assert_sin_registros(self):
        self.assertEqual((Folio.objects.count(), EventoFolio.objects.count()), (0, 0))


class RegistroFolioTests(FolioFixturesMixin, CatalogosPostgreSQLTestCase):
    def setUp(self):
        self.preparar()

    def test_valores_iniciales_y_copia_construida_por_servidor(self):
        instant = timezone.now()
        with patch("folios.services.timezone.now", return_value=instant):
            result = self.registrar(correo="persona@example.test", telefono="extensión A / sin formato")
        folio = Folio.objects.get(pk=result.folio_id)
        evento = EventoFolio.objects.get(pk=result.evento_id)
        self.assertIsInstance(folio.pk, UUID)
        self.assertEqual((folio.estado, folio.operador_responsable_id), ("EN_ESPERA", None))
        self.assertEqual(folio.get_estado_display(), "En espera")
        self.assertEqual((folio.registrado_por_id, evento.actor_id), (self.actor.pk, self.actor.pk))
        self.assertEqual((folio.llegada_original, evento.fecha), (instant, instant))
        self.assertEqual((evento.operacion, evento.estado_anterior, evento.estado_nuevo),
                         ("CREACION", None, "EN_ESPERA"))
        self.assertEqual(evento.folio_id, folio.pk)
        self.assertEqual(evento.datos_iniciales, {
            "nombre_completo": "  María Pérez  ", "correo": "persona@example.test",
            "telefono": "extensión A / sin formato", "oficina_id": self.oficina.pk,
            "tramite_id": self.tramite.pk, "llegada_original": instant.isoformat(),
        })
        folio.nombre_completo = "Cambio solo en memoria"
        evento.refresh_from_db()
        self.assertEqual(evento.datos_iniciales["nombre_completo"], "  María Pérez  ")
        with self.assertRaises(FrozenInstanceError):
            result.evento_id = 0

    def test_opcionales_ausentes_y_registros_independientes(self):
        first, second = self.registrar(), self.registrar()
        self.assertNotEqual(first.folio_id, second.folio_id)
        self.assertEqual((Folio.objects.count(), EventoFolio.objects.count()), (2, 2))
        for folio in Folio.objects.all():
            self.assertEqual((folio.correo, folio.telefono), ("", ""))

    def test_datos_invalidos_no_escriben(self):
        for kwargs in (
            {"nombre_completo": ""}, {"nombre_completo": " \t\n "},
            {"nombre_completo": None}, {"nombre_completo": 123},
            {"correo": "no-es-correo"}, {"correo": "a" * 255 + "@example.test"},
            {"correo": None}, {"telefono": None}, {"telefono": 123},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValidationError):
                self.registrar(**kwargs)
            self.assert_sin_registros()

    def test_campos_del_servidor_no_se_admiten_como_argumentos(self):
        for field in ("id", "llegada_original", "registrado_por", "estado",
                      "operador_responsable", "datos_iniciales", "using", "omitir_validaciones"):
            with self.subTest(field=field), self.assertRaises(TypeError):
                self.registrar(**{field: "valor del cliente"})
        self.assert_sin_registros()

    def test_autorizacion_independiente_de_staff_y_superuser(self):
        self.assertFalse(self.actor.is_staff)
        self.assertFalse(self.actor.is_superuser)
        self.registrar()
        for role in (Usuario.Rol.ADMINISTRADOR, Usuario.Rol.OPERADOR):
            actor = Usuario.objects.create_superuser(username=role, rol=role)
            with self.subTest(role=role), self.assertRaises(PermissionDenied):
                self.registrar(actor=actor)
        self.actor.is_staff = self.actor.is_superuser = True
        self.actor.save(update_fields=["is_staff", "is_superuser"])
        self.registrar()
        self.assertEqual(EventoFolio.objects.count(), 2)

    def test_actor_autenticado_y_persistido_en_misma_base(self):
        for actor in (AnonymousUser(), None, Usuario(), Usuario(pk=self.actor.pk)):
            with self.subTest(actor=type(actor)), self.assertRaises(PermissionDenied):
                self.registrar(actor=actor)
        other = Usuario.objects.get(pk=self.actor.pk)
        other._state.db = "otra"
        with self.assertRaises(PermissionDenied):
            self.registrar(actor=other)
        self.assert_sin_registros()

    def test_actor_inactivo_se_relee_en_base(self):
        self.actor.is_active = False
        self.actor.save(update_fields=["is_active"])
        self.actor.is_active = True  # Instancia obsoleta intencional.
        with self.assertRaises(PermissionDenied):
            self.registrar()
        self.assert_sin_registros()

    def test_rol_actual_se_relee_en_base(self):
        self.actor.rol = Usuario.Rol.ADMINISTRADOR
        self.actor.save(update_fields=["rol"])
        self.actor.rol = Usuario.Rol.RECEPCION
        with self.assertRaises(PermissionDenied):
            self.registrar()
        self.assert_sin_registros()

    def test_actor_eliminado_no_autoriza(self):
        stale = Usuario.objects.get(pk=self.actor.pk)
        self.actor.delete()
        with self.assertRaises(PermissionDenied):
            self.registrar(actor=stale)
        self.assert_sin_registros()

    def test_referencias_inexistentes_o_incompatibles(self):
        other = Oficina.objects.create(nombre="Sur")
        other_procedure = Tramite.objects.create(nombre="Solicitud", oficina=other)
        for kwargs in ({"oficina_id": -1}, {"tramite_id": -1},
                       {"tramite_id": other_procedure.pk}, {"oficina_id": other.pk}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValidationError):
                self.registrar(**kwargs)
        self.assert_sin_registros()

    def test_oficina_y_tramite_deben_estar_activos(self):
        for obj in (self.oficina, self.tramite):
            obj.activo = False
            obj.save(update_fields=["activo"])
            with self.assertRaises(ValidationError):
                self.registrar()
            obj.activo = True
            obj.save(update_fields=["activo"])
        self.assert_sin_registros()

    def test_orden_de_bloqueos_y_dos_inserciones(self):
        with CaptureQueriesContext(connection) as queries:
            self.registrar()
        locks = [q["sql"] for q in queries if "FOR UPDATE" in q["sql"]]
        self.assertEqual(len(locks), 3)
        for sql, table in zip(locks, ("usuarios_usuario", "oficinas_oficina", "tramites_tramite")):
            self.assertIn(table, sql)
        inserts = [q["sql"] for q in queries if q["sql"].startswith("INSERT")]
        self.assertEqual(len(inserts), 2)
        self.assertIn('"folios_folio"', inserts[0])
        self.assertIn('"folios_eventofolio"', inserts[1])

    def test_check_de_nombre_en_postgresql(self):
        folio = Folio.objects.get(pk=self.registrar().folio_id)
        for value in ("", " \t\n "):
            self.assert_rechazo_postgresql(
                lambda: self.actualizar_sql("folios_folio", "nombre_completo", value, folio.pk),
                "23514", "folios_folio_nombre_con_contenido",
            )

    def actualizar_sql(self, table, field, value, pk):
        # Tabla/campo son constantes de estas pruebas; no entrada del usuario.
        with connection.cursor() as cursor:
            cursor.execute(f'UPDATE "{table}" SET "{field}" = %s WHERE id = %s', [value, pk])
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")

    def test_check_de_estado_y_operador_vacio(self):
        folio = Folio.objects.get(pk=self.registrar().folio_id)
        for field, value in (("estado", "LLAMADO"), ("estado", ""),
                             ("operador_responsable_id", self.actor.pk)):
            self.assert_rechazo_postgresql(
                lambda: self.actualizar_sql("folios_folio", field, value, folio.pk),
                "23514", "folios_folio_estado_inicial",
            )

    def test_not_null_y_referencias_de_folio(self):
        folio = Folio.objects.get(pk=self.registrar().folio_id)
        for field in ("nombre_completo", "correo", "telefono", "oficina_id", "tramite_id",
                      "registrado_por_id", "llegada_original", "estado"):
            with self.subTest(field=field):
                self.assert_rechazo_postgresql(
                    lambda: self.actualizar_sql("folios_folio", field, None, folio.pk), "23502",
                )
        for field in ("oficina_id", "tramite_id", "registrado_por_id"):
            self.assert_rechazo_postgresql(
                lambda: self.actualizar_sql("folios_folio", field, -1, folio.pk), "23503",
            )

    def test_estados_y_null_del_evento(self):
        evento = EventoFolio.objects.get(pk=self.registrar().evento_id)
        for field, value, state in (
            ("operacion", "OTRA", "23514"), ("operacion", None, "23502"),
            ("estado_anterior", "EN_ESPERA", "23514"), ("estado_anterior", "", "23514"),
            ("estado_nuevo", "LLAMADO", "23514"), ("estado_nuevo", "", "23514"),
            ("estado_nuevo", None, "23502"), ("fecha", None, "23502"),
            ("datos_iniciales", None, "23502"), ("folio_id", None, "23502"),
            ("actor_id", None, "23502"), ("actor_id", -1, "23503"),
        ):
            with self.subTest(field=field, value=value):
                self.assert_rechazo_postgresql(
                    lambda: self.actualizar_sql("folios_eventofolio", field, value, evento.pk), state,
                )

    def test_evento_creacion_unico_por_folio(self):
        evento = EventoFolio.objects.get(pk=self.registrar().evento_id)
        duplicate = EventoFolio(
            folio=evento.folio, actor=evento.actor, fecha=evento.fecha,
            operacion="CREACION", estado_anterior=None, estado_nuevo="EN_ESPERA",
            datos_iniciales=evento.datos_iniciales,
        )
        self.assert_rechazo_postgresql(
            lambda: models.Model.save(duplicate, force_insert=True), "23505",
            "folios_evento_creacion_unica",
        )

    def test_fallo_real_del_evento_revierte_folio(self):
        def invalid_event(execute, sql, params, many, context):
            if sql.startswith('INSERT INTO "folios_eventofolio"'):
                self.assertEqual(Folio.objects.count(), 1)  # Ya insertado, aún sin commit.
                params = list(params)
                columns = sql.split("(", 1)[1].split(")", 1)[0]
                columns = [col.strip().strip('"') for col in columns.split(",")]
                params[columns.index("estado_nuevo")] = "INVALIDO"
            return execute(sql, params, many, context)
        with connection.execute_wrapper(invalid_event), self.assertRaises(IntegrityError):
            self.registrar()
        self.assert_sin_registros()

    def test_fallo_folio_no_genera_evento(self):
        def invalid_folio(execute, sql, params, many, context):
            if sql.startswith('INSERT INTO "folios_folio"'):
                params = list(params)
                columns = sql.split("(", 1)[1].split(")", 1)[0]
                columns = [col.strip().strip('"') for col in columns.split(",")]
                params[columns.index("nombre_completo")] = None
            return execute(sql, params, many, context)
        with patch("folios.services._crear_evento") as event_writer:
            with connection.execute_wrapper(invalid_folio), self.assertRaises(IntegrityError):
                self.registrar()
            event_writer.assert_not_called()
        self.assert_sin_registros()

    def test_transaccion_exterior_revierte_ambos(self):
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                self.registrar()
                raise RuntimeError("Revertir ambas inserciones")
        self.assert_sin_registros()

    def test_referencias_protegidas_y_sin_efectos_automaticos(self):
        result = self.registrar()
        folio = Folio.objects.get(pk=result.folio_id)
        for obj in (self.actor, self.oficina, self.tramite, folio):
            with self.assertRaises(ProtectedError):
                models.Model.delete(obj)
        before = EventoFolio.objects.get(pk=result.evento_id).datos_iniciales
        for obj, field in ((self.actor, "is_active"), (self.oficina, "activo"), (self.tramite, "activo")):
            setattr(obj, field, False)
            obj.save(update_fields=[field])
        folio.refresh_from_db()
        self.assertEqual((folio.estado, folio.operador_responsable_id), ("EN_ESPERA", None))
        self.assertEqual(EventoFolio.objects.get(pk=result.evento_id).datos_iniciales, before)

    def test_barreras_modelos_y_managers_sync_async(self):
        result = self.registrar()
        for model, pk in ((Folio, result.folio_id), (EventoFolio, result.evento_id)):
            obj = model.objects.get(pk=pk)
            for op in (obj.save, obj.delete, lambda: obj.save(update_fields=[]),
                       lambda: model(pk=pk).save(force_update=True)):
                with self.assertRaises(NotSupportedError):
                    op()
            for name in ("asave", "adelete"):
                with self.assertRaises(NotSupportedError):
                    async_to_sync(getattr(obj, name))()
            for manager in (model.objects, model._base_manager, model._default_manager):
                for name, args, kwargs in (
                    ("create", (), {}), ("update", (), {"estado": "EN_ESPERA"}),
                    ("get_or_create", (), {"pk": pk}), ("update_or_create", (), {"pk": pk}),
                    ("bulk_create", ([obj],), {}), ("bulk_update", ([obj], ["id"]), {}),
                    ("delete", (), {}),
                ):
                    for asynchronous in (False, True):
                        method = getattr(manager.all(), ("a" if asynchronous else "") + name)
                        with self.subTest(model=model.__name__, name=name, asynchronous=asynchronous):
                            with self.assertRaises(NotSupportedError):
                                if asynchronous:
                                    async_to_sync(method)(*args, **kwargs)
                                else:
                                    method(*args, **kwargs)
        self.assertEqual((Folio.objects.count(), EventoFolio.objects.count()), (1, 1))

    def test_barreras_de_managers_relacionados(self):
        result = self.registrar()
        folio = Folio.objects.get(pk=result.folio_id)
        evento = EventoFolio.objects.get(pk=result.evento_id)
        for manager in (self.oficina.folios, self.tramite.folios, self.actor.folios_registrados,
                        self.actor.folios_responsables, self.actor.eventos_folios, folio.eventos):
            obj = folio if manager.model is Folio else evento
            for name, args, kwargs in (
                ("create", (), {}), ("get_or_create", (), {"pk": obj.pk}),
                ("update_or_create", (), {"pk": obj.pk}),
                ("add", (obj,), {"bulk": True}), ("add", (obj,), {"bulk": False}),
            ):
                for asynchronous in (False, True):
                    method = getattr(manager, ("a" if asynchronous else "") + name)
                    with self.subTest(manager=manager, name=name, asynchronous=asynchronous):
                        with self.assertRaises(NotSupportedError):
                            with transaction.atomic():
                                if asynchronous:
                                    async_to_sync(method)(*args, **kwargs)
                                else:
                                    method(*args, **kwargs)
            with self.assertRaises(NotSupportedError):
                manager.all().delete()
        # NULL habilita clear/set en el manager inverso: tampoco deben escribir.
        manager = self.actor.folios_responsables
        for name, args in (("clear", ()), ("set", ([],))):
            for bulk in (False, True):
                for asynchronous in (False, True):
                    with self.assertRaises(NotSupportedError):
                        method = getattr(manager, ("a" if asynchronous else "") + name)
                        if asynchronous:
                            async_to_sync(method)(*args, bulk=bulk)
                        else:
                            method(*args, bulk=bulk)
        folio.refresh_from_db()
        self.assertIsNone(folio.operador_responsable_id)

    def test_seleccion_de_manager_inverso_conserva_lecturas_y_barreras(self):
        result = self.registrar()
        folio = Folio.objects.get(pk=result.folio_id)
        for original in (self.oficina.folios, self.tramite.folios, self.actor.folios_registrados,
                         self.actor.folios_responsables, self.actor.eventos_folios, folio.eventos):
            expected = list(original.order_by("pk").values_list("pk", flat=True))
            selected = original(manager="objects")
            # La selección puede repetirse; ninguna debe perder la barrera.
            for manager in (selected, selected(manager="objects"), selected.db_manager("default")):
                self.assertEqual(list(manager.order_by("pk").values_list("pk", flat=True)), expected)
                operations = [("add", ()), ("set", ([],))]
                if manager.field.null:
                    operations.extend([("remove", ()), ("clear", ())])
                for name, args in operations:
                    for bulk in (False, True):
                        for asynchronous in (False, True):
                            with self.subTest(relation=original.field.name, name=name,
                                              bulk=bulk, asynchronous=asynchronous):
                                with self.assertRaises(NotSupportedError):
                                    with transaction.atomic():
                                        method = getattr(manager, ("a" if asynchronous else "") + name)
                                        if asynchronous:
                                            async_to_sync(method)(*args, bulk=bulk)
                                        else:
                                            method(*args, bulk=bulk)
        self.assertEqual((Folio.objects.count(), EventoFolio.objects.count()), (1, 1))


class RegistroFolioConcurrenciaTests(FolioFixturesMixin, CatalogosPostgreSQLTransactionTestCase):
    def setUp(self):
        self.preparar()

    def assert_bloqueado_por(self, blocked_pid, blocker_pid):
        self.assertNotEqual(blocked_pid, blocker_pid)
        deadline = monotonic() + 4
        while monotonic() < deadline:
            with connection.cursor() as cursor:
                cursor.execute("SELECT %s = ANY(pg_blocking_pids(%s))", [blocker_pid, blocked_pid])
                if cursor.fetchone()[0]:
                    return
            sleep(0.01)
        self.fail("La conexión debe esperar el bloqueo real de la otra conexión.")

    def registrar_tras_cambio(self, target, field, value):
        attempted = Event()
        backend = {}
        table = target._meta.db_table

        def worker():
            db = connections["default"]
            try:
                actor = Usuario.objects.get(pk=self.actor.pk)  # Estado anterior intencional.
                with db.cursor() as cursor:
                    cursor.execute("SET lock_timeout = '8s'")
                    cursor.execute("SELECT pg_backend_pid()")
                    backend["pid"] = cursor.fetchone()[0]

                def coordinate(execute, sql, params, many, context):
                    if "FOR UPDATE" in sql.upper() and f'"{table}"' in sql:
                        attempted.set()
                    return execute(sql, params, many, context)

                with db.execute_wrapper(coordinate):
                    try:
                        self.registrar(actor=actor)
                    except (PermissionDenied, ValidationError) as error:
                        return type(error)
                    return None
            finally:
                db.close()

        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_backend_pid()")
            blocker_pid = cursor.fetchone()[0]
        with ThreadPoolExecutor(max_workers=1) as pool:
            with transaction.atomic():
                setattr(target, field, value)
                target.save(update_fields=[field])
                future = pool.submit(worker)
                self.assertTrue(attempted.wait(timeout=5))
                self.assert_bloqueado_por(backend["pid"], blocker_pid)
            self.assertIs(future.result(timeout=12), PermissionDenied if isinstance(target, Usuario) else ValidationError)
        self.assert_sin_registros()

    def test_desactivacion_cuenta_se_relee_tras_esperar(self):
        self.registrar_tras_cambio(self.actor, "is_active", False)

    def test_cambio_rol_se_relee_tras_esperar(self):
        self.registrar_tras_cambio(self.actor, "rol", Usuario.Rol.ADMINISTRADOR)

    def test_desactivacion_oficina_se_relee_tras_esperar(self):
        self.registrar_tras_cambio(self.oficina, "activo", False)

    def test_desactivacion_tramite_se_relee_tras_esperar(self):
        self.registrar_tras_cambio(self.tramite, "activo", False)

    def test_desactivacion_espera_registro_que_ya_tiene_bloqueo(self):
        for target, field in ((self.actor, "is_active"), (self.oficina, "activo"), (self.tramite, "activo")):
            with self.subTest(table=target._meta.db_table):
                held, attempted, release = Event(), Event(), Event()
                backends = {}
                model, pk, table = type(target), target.pk, target._meta.db_table

                def register():
                    db = connections["default"]
                    try:
                        actor = Usuario.objects.get(pk=self.actor.pk)
                        with db.cursor() as cursor:
                            cursor.execute("SET lock_timeout = '8s'")
                            cursor.execute("SELECT pg_backend_pid()")
                            backends["register"] = cursor.fetchone()[0]

                        def coordinate(execute, sql, params, many, context):
                            result = execute(sql, params, many, context)
                            if "FOR UPDATE" in sql.upper() and f'"{table}"' in sql:
                                held.set()
                                if not release.wait(timeout=10):
                                    raise TimeoutError("El registro no recibió la liberación del bloqueo.")
                            return result

                        with db.execute_wrapper(coordinate):
                            return self.registrar(actor=actor)
                    finally:
                        db.close()

                def deactivate():
                    db = connections["default"]
                    try:
                        with db.cursor() as cursor:
                            cursor.execute("SET lock_timeout = '8s'")
                            cursor.execute("SELECT pg_backend_pid()")
                            backends["deactivate"] = cursor.fetchone()[0]

                        def coordinate(execute, sql, params, many, context):
                            # UPDATE del catálogo o SELECT FOR UPDATE de Usuario.save.
                            if f'"{table}"' in sql and ("FOR UPDATE" in sql.upper() or sql.startswith("UPDATE")):
                                attempted.set()
                            return execute(sql, params, many, context)

                        with db.execute_wrapper(coordinate):
                            obj = model.objects.get(pk=pk)
                            setattr(obj, field, False)
                            obj.save(update_fields=[field])
                    finally:
                        db.close()

                with ThreadPoolExecutor(max_workers=2) as pool:
                    registration = pool.submit(register)
                    try:
                        self.assertTrue(held.wait(timeout=5))
                        deactivation = pool.submit(deactivate)
                        self.assertTrue(attempted.wait(timeout=5))
                        self.assert_bloqueado_por(backends["deactivate"], backends["register"])
                    finally:
                        release.set()
                    result = registration.result(timeout=12)
                    deactivation.result(timeout=12)
                self.assertTrue(Folio.objects.filter(pk=result.folio_id).exists())
                self.assertEqual(EventoFolio.objects.filter(folio_id=result.folio_id).count(), 1)
                target.refresh_from_db()
                self.assertFalse(getattr(target, field))
                setattr(target, field, True)
                target.save(update_fields=[field])
