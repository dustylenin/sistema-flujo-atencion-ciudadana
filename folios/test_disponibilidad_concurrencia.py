"""Contención real en PostgreSQL, sin habilitar estados futuros de Folio."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event
from time import monotonic, sleep
from uuid import uuid4

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection, connections, transaction

from oficinas.models import Oficina
from oficinas.services import crear_asignacion
from oficinas.testing import CatalogosPostgreSQLTransactionTestCase
from usuarios.models import Usuario

from .models import PausaOperador as Pausa
from .services_disponibilidad import Disponibilidad, consultar_disponibilidad
from .test_disponibilidad import DisponibilidadFixturesMixin


class DisponibilidadConcurrenciaTests(DisponibilidadFixturesMixin, CatalogosPostgreSQLTransactionTestCase):
    def setUp(self):
        self.preparar()

    def assert_bloqueado_por(self, blocked, blocker):
        self.assertNotEqual(blocked, blocker)
        deadline = monotonic() + 4
        while monotonic() < deadline:
            with connection.cursor() as cursor:
                cursor.execute("SELECT %s = ANY(pg_blocking_pids(%s))", [blocker, blocked])
                if cursor.fetchone()[0]:
                    return
            sleep(0.01)
        self.fail("No se comprobó espera real entre conexiones independientes.")

    def simultaneos(self, primera, segunda):
        held, attempted, release = Event(), Event(), Event()
        backends = {}

        def worker(action, first):
            db = connections["default"]
            try:
                actor = Usuario.objects.get(pk=self.operador.pk)
                with db.cursor() as cursor:
                    cursor.execute("SET lock_timeout = '8s'")
                    cursor.execute("SELECT pg_backend_pid()")
                    backends[first] = cursor.fetchone()[0]
                synchronized = False

                def coordinate(execute, sql, params, many, context):
                    nonlocal synchronized
                    locks_user = "FOR UPDATE" in sql.upper() and '"usuarios_usuario"' in sql
                    if locks_user and not first:
                        attempted.set()
                    result = execute(sql, params, many, context)
                    if locks_user and first and not synchronized:
                        synchronized = True
                        held.set()
                        if not release.wait(timeout=10):
                            raise TimeoutError("No se liberó el bloqueo de Usuario.")
                    return result

                with db.execute_wrapper(coordinate):
                    return action(actor)
            finally:
                db.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(worker, primera, True)
            try:
                self.assertTrue(held.wait(timeout=5))
                second = pool.submit(worker, segunda, False)
                self.assertTrue(attempted.wait(timeout=5))
                self.assert_bloqueado_por(backends[False], backends[True])
            finally:
                release.set()
            return first.result(timeout=12), second.result(timeout=12)

    def test_pausas_misma_clave_confirman_una_vez(self):
        key = uuid4()
        call = lambda actor: self.pausar(actor=actor, solicitud_id=key)
        first, second = self.simultaneos(call, call)
        self.assertEqual((first.resultado, second.resultado), ("PAUSADA", "PAUSADA"))
        self.assertFalse(first.repetida)
        self.assertTrue(second.repetida)
        self.assertEqual(first.pausa_id, second.pausa_id)
        self.assertEqual(first.evento_id, second.evento_id)
        self.assertEqual(first.confirmada_en, second.confirmada_en)
        self.assertEqual(self.counts(), (1, 1, 1))

    def test_pausas_distintas_claves_no_crean_segunda_pausa(self):
        first, second = self.simultaneos(
            lambda actor: self.pausar(actor=actor, motivo="Primera"),
            lambda actor: self.pausar(actor=actor, motivo="Segunda"),
        )
        self.assertEqual((first.resultado, second.resultado), ("PAUSADA", "YA_EN_PAUSA"))
        self.assertIsNone(second.evento_id)
        self.assertEqual(Pausa.objects.get().motivo, "Primera")
        self.assertEqual(first.pausa_id, second.pausa_id)
        self.assertEqual(self.counts(), (1, 1, 2))

    def test_misma_clave_con_argumentos_concurrentes_incompatibles(self):
        key = uuid4()

        def incompatible(actor):
            try:
                self.pausar(actor=actor, motivo="Otro motivo", solicitud_id=key)
            except ValidationError:
                return True
            return False

        first, rejected = self.simultaneos(
            lambda actor: self.pausar(actor=actor, solicitud_id=key), incompatible,
        )
        self.assertEqual(first.resultado, "PAUSADA")
        self.assertTrue(rejected)
        self.assertEqual(self.counts(), (1, 1, 1))

    def test_solicitud_que_espera_rollback_no_encuentra_comprobante_parcial(self):
        key = uuid4()

        def rollback(actor):
            try:
                with transaction.atomic():
                    self.pausar(actor=actor, solicitud_id=key)
                    raise RuntimeError("Revertir también la transacción exterior.")
            except RuntimeError:
                return True

        reverted, result = self.simultaneos(
            rollback, lambda actor: self.pausar(actor=actor, solicitud_id=key),
        )
        self.assertTrue(reverted)
        self.assertEqual(result.resultado, "PAUSADA")
        self.assertFalse(result.repetida)
        self.assertEqual(self.counts(), (1, 1, 1))

    def test_reanudaciones_misma_clave_confirman_una_vez(self):
        pause = self.pausar()
        key = uuid4()
        call = lambda actor: self.reanudar(pause.pausa_id, actor=actor, solicitud_id=key)
        first, second = self.simultaneos(call, call)
        self.assertEqual((first.resultado, second.resultado), ("REANUDADA", "REANUDADA"))
        self.assertFalse(first.repetida)
        self.assertTrue(second.repetida)
        self.assertEqual(first.evento_id, second.evento_id)
        self.assertEqual(first.confirmada_en, second.confirmada_en)
        self.assertEqual(self.counts(), (1, 2, 2))

    def test_reanudaciones_distintas_claves_no_cambian_fin(self):
        pause = self.pausar()
        call = lambda actor: self.reanudar(pause.pausa_id, actor=actor)
        first, second = self.simultaneos(call, call)
        self.assertEqual((first.resultado, second.resultado), ("REANUDADA", "YA_REANUDADA"))
        self.assertIsNone(second.evento_id)
        self.assertEqual(Pausa.objects.get().fin, first.confirmada_en)
        self.assertEqual(self.counts(), (1, 2, 3))

    def test_pausar_antes_de_reanudar_no_deja_pausa_pendiente(self):
        pause = self.pausar()
        first, second = self.simultaneos(
            lambda actor: self.pausar(actor=actor),
            lambda actor: self.reanudar(pause.pausa_id, actor=actor),
        )
        self.assertEqual((first.resultado, second.resultado), ("YA_EN_PAUSA", "REANUDADA"))
        self.assertEqual(self.counts(), (1, 2, 3))
        self.assertFalse(Pausa.objects.filter(fin__isnull=True).exists())
        self.assertEqual(consultar_disponibilidad(actor=self.operador, operador_id=self.operador.pk).disponibilidad,
                         Disponibilidad.LIBRE)

    def test_reanudar_antes_de_pausar_abre_otra_pausa(self):
        pause = self.pausar()
        first, second = self.simultaneos(
            lambda actor: self.reanudar(pause.pausa_id, actor=actor),
            lambda actor: self.pausar(actor=actor),
        )
        self.assertEqual((first.resultado, second.resultado), ("REANUDADA", "PAUSADA"))
        self.assertNotEqual(first.pausa_id, second.pausa_id)
        self.assertEqual(Pausa.objects.get(fin__isnull=True).pk, second.pausa_id)
        self.assertEqual(self.counts(), (2, 3, 3))

    def test_reanudacion_antigua_no_cierra_pausa_abierta_concurrente(self):
        old = self.pausar()
        self.reanudar(old.pausa_id)
        first, second = self.simultaneos(
            lambda actor: self.pausar(actor=actor),
            lambda actor: self.reanudar(old.pausa_id, actor=actor),
        )
        self.assertEqual((first.resultado, second.resultado), ("PAUSADA", "YA_REANUDADA"))
        self.assertEqual(Pausa.objects.get(fin__isnull=True).pk, first.pausa_id)
        self.assertEqual(self.counts(), (2, 3, 4))

    def test_desactivacion_antes_de_pausar_o_reanudar_rechaza_actor_obsoleto(self):
        for resume in (False, True):
            with self.subTest(reanudar=resume):
                pause = self.pausar() if resume else None
                before = self.counts()
                attempted = Event()
                backend = {}

                def worker():
                    db = connections["default"]
                    try:
                        actor = Usuario.objects.get(pk=self.operador.pk)
                        with db.cursor() as cursor:
                            cursor.execute("SET lock_timeout = '8s'")
                            cursor.execute("SELECT pg_backend_pid()")
                            backend["pid"] = cursor.fetchone()[0]

                        def coordinate(execute, sql, params, many, context):
                            if "FOR UPDATE" in sql.upper() and '"usuarios_usuario"' in sql:
                                attempted.set()
                            return execute(sql, params, many, context)

                        with db.execute_wrapper(coordinate):
                            try:
                                if resume:
                                    self.reanudar(pause.pausa_id, actor=actor)
                                else:
                                    self.pausar(actor=actor)
                            except PermissionDenied:
                                return True
                            return False
                    finally:
                        db.close()

                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_backend_pid()")
                    blocker = cursor.fetchone()[0]
                with ThreadPoolExecutor(max_workers=1) as pool:
                    with transaction.atomic():
                        self.operador.is_active = False
                        self.operador.save(update_fields=["is_active"])
                        future = pool.submit(worker)
                        self.assertTrue(attempted.wait(timeout=5))
                        self.assert_bloqueado_por(backend["pid"], blocker)
                    self.assertTrue(future.result(timeout=12))
                self.assertEqual(self.counts(), before)
                self.operador.is_active = True
                self.operador.save(update_fields=["is_active"])

    def test_desactivacion_espera_pausa_y_reanudacion_y_conserva_registros(self):
        def deactivate(actor):
            actor.is_active = False
            actor.save(update_fields=["is_active"])

        for resume in (False, True):
            with self.subTest(reanudar=resume):
                pause = self.pausar() if resume else None
                first, _ = self.simultaneos(
                    (lambda actor: self.reanudar(pause.pausa_id, actor=actor)) if resume
                    else (lambda actor: self.pausar(actor=actor)),
                    deactivate,
                )
                self.operador.refresh_from_db()
                self.assertFalse(self.operador.is_active)
                stored = Pausa.objects.get(pk=first.pausa_id)
                self.assertEqual(stored.fin, first.confirmada_en if resume else None)
                self.assertEqual(stored.operador_id, self.operador.pk)
                self.operador.is_active = True
                self.operador.save(update_fields=["is_active"])

    def test_asignacion_espera_usuario_y_es_compatible_con_pausa(self):
        office = Oficina.objects.create(nombre="Oficina")

        def assign(actor):
            admin = Usuario.objects.get(pk=self.admin.pk)
            return crear_asignacion(actor=admin, operador_id=actor.pk, oficina_id=office.pk)

        first, _ = self.simultaneos(lambda actor: self.pausar(actor=actor), assign)
        stored = Pausa.objects.get(pk=first.pausa_id)
        self.assertIsNone(stored.oficina_contexto_id)
        self.assertIsNone(stored.folio_contexto_id)
        self.assertTrue(office.asignaciones_operadores.filter(operador=self.operador, activo=True).exists())
