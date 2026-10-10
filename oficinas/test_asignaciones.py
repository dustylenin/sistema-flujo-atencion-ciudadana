"""Asignaciones: solo PostgreSQL aislado; fixtures históricos no habilitan retirada."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event
from time import monotonic, sleep
from unittest.mock import patch

from asgiref.sync import async_to_sync
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection, connections, IntegrityError, models, NotSupportedError, transaction
from django.db.models.deletion import ProtectedError
from django.test import SimpleTestCase
from django.utils import timezone

from usuarios.models import Usuario
from .models import AsignacionOperadorOficina as Asignacion, EventoAsignacion as Evento, Oficina
from .services import crear_asignacion, reactivar_asignacion, EstadoAsignacion as Estado
from .testing import CatalogosPostgreSQLTestCase, CatalogosPostgreSQLTransactionTestCase


class EscrituraAsignacionesSinBaseTests(SimpleTestCase):
    def test_todas_las_vias_publicas_rechazan_escritura(self):
        for model in (Asignacion, Evento):
            instance = model(pk=1)
            with self.subTest(model=model.__name__):
                for operation in (instance.save, instance.delete):
                    with self.assertRaises(NotSupportedError):
                        operation()
                for manager in (model.objects, model._base_manager, model._default_manager):
                    for operation in (
                        lambda: manager.create(), lambda: manager.all().update(activo=False),
                        lambda: manager.get_or_create(pk=1),
                        lambda: manager.update_or_create(pk=1),
                        lambda: manager.bulk_create([]),
                        lambda: manager.bulk_create([], update_conflicts=True),
                        lambda: manager.bulk_update([], ["id"]), manager.all().delete,
                    ):
                        with self.assertRaises(NotSupportedError):
                            operation()

    def test_variantes_asincronas_rechazan_escritura(self):
        for model in (Asignacion, Evento):
            for operation, kwargs in (
                (model(pk=1).asave, {}), (model(pk=1).adelete, {}),
                (model.objects.acreate, {}), (model.objects.all().aupdate, {"activo": False}),
                (model.objects.aget_or_create, {"pk": 1}),
                (model.objects.aupdate_or_create, {"pk": 1}),
                (model.objects.abulk_create, {"objs": []}),
                (model.objects.abulk_update, {"objs": [], "fields": ["id"]}),
                (model.objects.all().adelete, {}),
            ):
                with self.subTest(model=model.__name__, operation=operation.__name__):
                    with self.assertRaises(NotSupportedError):
                        async_to_sync(operation)(**kwargs)


class AsignacionFixturesMixin:
    def preparar_cuentas(self):
        self.admin = Usuario.objects.create_user(username="administrador", rol=Usuario.Rol.ADMINISTRADOR)
        self.operador = Usuario.objects.create_user(username="operador", rol=Usuario.Rol.OPERADOR)
        self.oficina = Oficina.objects.create(nombre="Norte")

    def llamar(self, service=crear_asignacion, **kwargs):
        options = dict(actor=self.admin, operador_id=self.operador.pk, oficina_id=self.oficina.pk)
        options.update(kwargs)
        return service(**options)

    def fixture_inactiva(self, *, con_historia=False, operador=None):
        # Solo preparación de un estado histórico dentro de PostgreSQL de pruebas.
        # No se expone una operación de retirada en la aplicación.
        operador = operador or self.operador
        assignment = Asignacion(operador=operador, oficina=self.oficina, activo=False)
        models.Model.save(assignment, force_insert=True)
        if con_historia:
            event = Evento(
                asignacion=assignment, actor=self.admin, operacion=Evento.Operacion.CREACION,
                activo_anterior=None, activo_nuevo=True,
            )
            models.Model.save(event, force_insert=True)
        return assignment


class AsignacionesPostgreSQLTests(AsignacionFixturesMixin, CatalogosPostgreSQLTestCase):
    def setUp(self):
        self.preparar_cuentas()

    def test_creacion_evento_actual_y_ya_activa_sin_escrituras(self):
        before = timezone.now()
        result = self.llamar()
        self.assertEqual(result.estado, Estado.CREADA)
        assignment = Asignacion.objects.get(pk=result.asignacion_id)
        event = Evento.objects.get(pk=result.evento_id)
        self.assertEqual((assignment.operador_id, assignment.oficina_id, assignment.activo),
                         (self.operador.pk, self.oficina.pk, True))
        self.assertEqual((event.asignacion_id, event.actor_id, event.operacion,
                          event.activo_anterior, event.activo_nuevo),
                         (assignment.pk, self.admin.pk, "CREACION", None, True))
        self.assertLessEqual(before, event.fecha)
        self.assertLessEqual(event.fecha, timezone.now())
        for service in (crear_asignacion, reactivar_asignacion):
            queries = []
            def capture(execute, sql, params, many, context):
                queries.append(sql)
                return execute(sql, params, many, context)
            with connection.execute_wrapper(capture):
                unchanged = self.llamar(service)
            self.assertEqual((unchanged.estado, unchanged.asignacion_id, unchanged.evento_id),
                             (Estado.YA_ACTIVA, assignment.pk, None))
            self.assertFalse(any(sql.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE")) for sql in queries))
        self.assertEqual((Asignacion.objects.count(), Evento.objects.count()), (1, 1))

    def test_reactivacion_conserva_pk_y_eventos_anteriores(self):
        assignment = self.fixture_inactiva(con_historia=True)
        previous = list(assignment.eventos.values())
        result = self.llamar()
        self.assertEqual((result.estado, result.asignacion_id, result.evento_id),
                         (Estado.REQUIERE_REACTIVACION, assignment.pk, None))
        result = self.llamar(reactivar_asignacion)
        self.assertEqual((result.estado, result.asignacion_id), (Estado.REACTIVADA, assignment.pk))
        assignment.refresh_from_db()
        self.assertTrue(assignment.activo)
        self.assertEqual(list(Evento.objects.filter(pk=previous[0]["id"]).values()), previous)
        event = Evento.objects.get(pk=result.evento_id)
        self.assertEqual((event.operacion, event.activo_anterior, event.activo_nuevo),
                         ("REACTIVACION", False, True))
        self.assertEqual((Asignacion.objects.count(), Evento.objects.count()), (1, 2))

    def test_reactivar_inexistente_no_crea_registros(self):
        result = self.llamar(reactivar_asignacion)
        self.assertEqual((result.estado, result.asignacion_id, result.evento_id),
                         (Estado.ASIGNACION_INEXISTENTE, None, None))
        self.assertEqual((Asignacion.objects.count(), Evento.objects.count()), (0, 0))

    def test_multiplicidad_y_unicidad_incluso_inactiva_en_postgresql(self):
        other = Usuario.objects.create_user(username="otro", rol=Usuario.Rol.OPERADOR)
        south = Oficina.objects.create(nombre="Sur")
        self.llamar()
        self.llamar(operador_id=other.pk)
        self.llamar(oficina_id=south.pk)
        self.assertEqual(Asignacion.objects.count(), 3)
        for active in (False, True):
            duplicate = Asignacion(operador=self.operador, oficina=self.oficina, activo=active)
            self.assert_rechazo_postgresql(
                lambda: models.Model.save(duplicate, force_insert=True), "23505",
                "oficinas_asignacion_operador_oficina_unica",
            )
        # Otra pareja empieza inactiva; tampoco puede duplicarse como activa.
        historical = Asignacion(operador=other, oficina=south, activo=False)
        models.Model.save(historical, force_insert=True)
        duplicate = Asignacion(operador=other, oficina=south, activo=True)
        self.assert_rechazo_postgresql(lambda: models.Model.save(duplicate, force_insert=True), "23505")

    def test_autorizacion_no_depende_de_indicadores_tecnicos(self):
        # Administrador funcional sin staff/superuser ya está autorizado.
        self.assertFalse(self.admin.is_staff)
        self.assertFalse(self.admin.is_superuser)
        self.llamar()
        for role in (Usuario.Rol.RECEPCION, Usuario.Rol.OPERADOR):
            actor = Usuario.objects.create_superuser(username=role, rol=role)
            for service in (crear_asignacion, reactivar_asignacion):
                with self.subTest(role=role), self.assertRaises(PermissionDenied):
                    self.llamar(service, actor=actor)
        for actor in (AnonymousUser(), None, Usuario(pk=self.admin.pk, rol=Usuario.Rol.ADMINISTRADOR)):
            with self.assertRaises(PermissionDenied):
                self.llamar(actor=actor)
        self.assertEqual(Evento.objects.count(), 1)

    def test_actor_se_relee_incluso_en_resultados_sin_cambios(self):
        self.llamar()
        stale = Usuario.objects.get(pk=self.admin.pk)
        self.admin.is_active = False
        self.admin.save(update_fields=["is_active"])
        for service in (crear_asignacion, reactivar_asignacion):
            with self.assertRaises(PermissionDenied):
                self.llamar(service, actor=stale)
        self.admin.is_active = True
        self.admin.rol = Usuario.Rol.RECEPCION
        self.admin.save(update_fields=["is_active", "rol"])
        stale.is_active = True
        stale.rol = Usuario.Rol.ADMINISTRADOR
        with self.assertRaises(PermissionDenied):
            self.llamar(actor=stale)
        self.assertEqual(Evento.objects.count(), 1)

    def test_actor_eliminado_o_de_otra_base_no_autoriza(self):
        stale = Usuario.objects.get(pk=self.admin.pk)
        self.admin.delete()
        with self.assertRaises(PermissionDenied):
            self.llamar(actor=stale)
        stale._state.db = "otra"
        with self.assertRaises(PermissionDenied):
            self.llamar(actor=stale)

    def test_condiciones_actuales_de_operador_y_oficina_creacion_y_reactivacion(self):
        for reactivate in (False, True):
            for bad in ("rol", "cuenta", "oficina"):
                with self.subTest(reactivate=reactivate, bad=bad), transaction.atomic():
                    target = Usuario.objects.create_user(username=f"{reactivate}-{bad}", rol=Usuario.Rol.RECEPCION if bad == "rol" else Usuario.Rol.OPERADOR)
                    if bad == "cuenta":
                        target.is_active = False
                        target.save(update_fields=["is_active"])
                    office = Oficina.objects.create(nombre=f"{reactivate}-{bad}", activo=bad != "oficina")
                    if reactivate:
                        assignment = Asignacion(operador=target, oficina=office, activo=False)
                        models.Model.save(assignment, force_insert=True)
                    service = reactivar_asignacion if reactivate else crear_asignacion
                    with self.assertRaises(ValidationError):
                        self.llamar(service, operador_id=target.pk, oficina_id=office.pk)
                    if reactivate:
                        assignment.refresh_from_db()
                        self.assertFalse(assignment.activo)
        self.assertEqual(Evento.objects.count(), 0)

    def test_referencias_inexistentes_rechazadas(self):
        for service in (crear_asignacion, reactivar_asignacion):
            for kwargs in ({"operador_id": -1}, {"oficina_id": -1}):
                with self.subTest(service=service.__name__, kwargs=kwargs), self.assertRaises(ValidationError):
                    self.llamar(service, **kwargs)

    def test_estados_evento_y_null_en_check_real(self):
        assignment = self.fixture_inactiva()
        for operation in ("CREACION", "REACTIVACION", "OTRA"):
            for previous in (None, False, True):
                for new in (False, True):
                    if (operation, previous, new) in (("CREACION", None, True), ("REACTIVACION", False, True)):
                        continue
                    event = Evento(asignacion=assignment, actor=self.admin, operacion=operation,
                                   activo_anterior=previous, activo_nuevo=new)
                    with self.subTest(operation=operation, previous=previous, new=new):
                        self.assert_rechazo_postgresql(
                            lambda: models.Model.save(event, force_insert=True), "23514",
                            "oficinas_eventoasignacion_estados_coherentes",
                        )

    def test_referencias_y_not_null_del_evento_en_postgresql(self):
        result = self.llamar()
        for field, value, state in (("actor_id", -1, "23503"), ("asignacion_id", -1, "23503"),
                                    ("activo_nuevo", None, "23502"), ("fecha", None, "23502")):
            def write():
                with connection.cursor() as cursor:
                    cursor.execute(f'UPDATE oficinas_eventoasignacion SET "{field}" = %s WHERE id = %s', [value, result.evento_id])
                    cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
            with self.subTest(field=field):
                self.assert_rechazo_postgresql(write, state)

    def test_rollback_evento_fallido_revierte_creacion_y_reactivacion(self):
        # El fallo se provoca con un INSERT real que viola el CHECK del evento.
        from .services import _registrar_evento
        def invalid_event(**kwargs):
            kwargs["operacion"] = "INVALIDA"
            return _registrar_evento(**kwargs)
        for reactivate in (False, True):
            with self.subTest(reactivate=reactivate):
                assignment = self.fixture_inactiva(con_historia=True) if reactivate else None
                before = list(Evento.objects.values())
                with patch("oficinas.services._registrar_evento", side_effect=invalid_event):
                    with self.assertRaises(IntegrityError):
                        self.llamar(reactivar_asignacion if reactivate else crear_asignacion)
                self.assertEqual(list(Evento.objects.values()), before)
                if assignment:
                    assignment.refresh_from_db()
                    self.assertFalse(assignment.activo)
                else:
                    self.assertFalse(Asignacion.objects.exists())

    def test_fallo_asignacion_no_genera_evento_y_transaccion_exterior_revierte_ambos(self):
        def reject_insert(execute, sql, params, many, context):
            if sql.startswith('INSERT INTO "oficinas_asignacionoperadoroficina"'):
                params = list(params)
                params[0] = None  # NOT NULL real del operador.
            return execute(sql, params, many, context)
        with connection.execute_wrapper(reject_insert), self.assertRaises(IntegrityError):
            self.llamar()
        self.assertEqual((Asignacion.objects.count(), Evento.objects.count()), (0, 0))
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                self.llamar()
                raise RuntimeError("revertir transacción exterior")
        self.assertEqual((Asignacion.objects.count(), Evento.objects.count()), (0, 0))

    def test_managers_relacionados_no_abren_escrituras(self):
        result = self.llamar()
        assignment = Asignacion.objects.get(pk=result.asignacion_id)
        for manager in (self.operador.asignaciones_oficinas, self.oficina.asignaciones_operadores,
                        self.admin.eventos_asignaciones, assignment.eventos):
            for operation in (
                lambda: manager.create(), lambda: manager.get_or_create(pk=1),
                lambda: manager.update_or_create(pk=1), lambda: manager.update(activo=False),
                manager.all().delete,
            ):
                with self.assertRaises(NotSupportedError):
                    operation()
            instance = assignment if manager.model is Asignacion else Evento.objects.get(pk=result.evento_id)
            for bulk in (True, False):
                with self.assertRaises(NotSupportedError):
                    with transaction.atomic():
                        manager.add(instance, bulk=bulk)
            with self.assertRaises(NotSupportedError):
                async def rejected_create():
                    return await manager.acreate()
                async_to_sync(rejected_create)()
        self.assertEqual(Evento.objects.count(), 1)

    def test_referencias_protegidas_y_no_efectos_automaticos(self):
        result = self.llamar()
        for user in (self.operador, self.admin):
            with self.assertRaises(ProtectedError):
                user.delete()
        assignment = Asignacion.objects.get(pk=result.asignacion_id)
        with self.assertRaises(ProtectedError):
            models.Model.delete(assignment)  # Referencia protegida del evento.
        with self.assertRaises(ProtectedError):
            models.Model.delete(self.oficina)
        with self.assertRaises(NotSupportedError):
            assignment.operador_id = self.admin.pk
            assignment.save()
        self.operador.is_active = False
        self.operador.save(update_fields=["is_active"])
        self.oficina.activo = False
        self.oficina.save(update_fields=["activo"])
        assignment.refresh_from_db()
        self.assertEqual((assignment.operador_id, assignment.activo), (self.operador.pk, True))
        self.assertEqual(Evento.objects.count(), 1)

    def test_historia_inactiva_no_exige_rol_operador_para_conservarse(self):
        reception = Usuario.objects.create_user(username="historica", rol=Usuario.Rol.RECEPCION)
        assignment = self.fixture_inactiva(operador=reception)
        self.assertEqual(reception.asignaciones_oficinas.get().pk, assignment.pk)
        with self.assertRaises(ValidationError):
            self.llamar(reactivar_asignacion, operador_id=reception.pk)
        assignment.refresh_from_db()
        self.assertFalse(assignment.activo)


class AsignacionesConcurrenciaTests(AsignacionFixturesMixin, CatalogosPostgreSQLTransactionTestCase):
    def setUp(self):
        self.preparar_cuentas()

    def concurrentes(self, service):
        otro_admin = Usuario.objects.create_user(username="otro_admin", rol=Usuario.Rol.ADMINISTRADOR)
        first_read = Event()
        second_lock = Event()
        release = Event()
        backends = {}

        def run(actor_id, first):
            db = connections["default"]
            try:
                actor = Usuario.objects.get(pk=actor_id)
                with db.cursor() as cursor:
                    cursor.execute("SET lock_timeout = '8s'")
                    cursor.execute("SELECT pg_backend_pid()")
                    pid = cursor.fetchone()[0]
                backends[first] = pid

                def coordinate(execute, sql, params, many, context):
                    # El segundo actor es distinto: debe esperar al operador,
                    # no quedar serializado accidentalmente por el mismo actor.
                    if not first and "FOR UPDATE" in sql.upper() and '"usuarios_usuario"' in sql and self.operador.pk in (params or ()):
                        second_lock.set()
                    result = execute(sql, params, many, context)
                    # Detiene la primera transición después de leer la pareja
                    # bajo bloqueo y antes de persistir asignación o evento.
                    if first and "FOR UPDATE" in sql.upper() and '"oficinas_asignacionoperadoroficina"' in sql:
                        first_read.set()
                        if not release.wait(timeout=10):
                            raise TimeoutError("No se liberó la primera transición concurrente.")
                    return result

                with db.execute_wrapper(coordinate):
                    result = service(actor=actor, operador_id=self.operador.pk, oficina_id=self.oficina.pk)
                return pid, result
            finally:
                db.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(run, self.admin.pk, True)]
            try:
                self.assertTrue(first_read.wait(timeout=5), "La primera transición debe llegar a la pareja.")
                futures.append(pool.submit(run, otro_admin.pk, False))
                self.assertTrue(second_lock.wait(timeout=5), "La segunda transición debe intentar bloquear al operador.")
                self.assertNotEqual(backends[True], backends[False])
                blocked = False
                deadline = monotonic() + 3
                while monotonic() < deadline:
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT %s = ANY(pg_blocking_pids(%s))", [backends[True], backends[False]])
                        blocked = cursor.fetchone()[0]
                    if blocked:
                        break
                    sleep(0.01)
                self.assertTrue(blocked, "La segunda conexión debe esperar el bloqueo real del operador.")
            finally:
                release.set()
            outcomes = [future.result(timeout=15) for future in futures]
        self.assertNotEqual(outcomes[0][0], outcomes[1][0])
        return [outcome[1] for outcome in outcomes]

    def test_creacion_simultanea_una_asignacion_y_un_evento(self):
        results = self.concurrentes(crear_asignacion)
        self.assertCountEqual([result.estado for result in results], [Estado.CREADA, Estado.YA_ACTIVA])
        self.assertEqual(results[0].asignacion_id, results[1].asignacion_id)
        self.assertEqual((Asignacion.objects.count(), Evento.objects.count()), (1, 1))

    def test_reactivacion_simultanea_misma_pk_y_un_evento_nuevo(self):
        assignment = self.fixture_inactiva(con_historia=True)
        results = self.concurrentes(reactivar_asignacion)
        self.assertCountEqual([result.estado for result in results], [Estado.REACTIVADA, Estado.YA_ACTIVA])
        self.assertTrue(all(result.asignacion_id == assignment.pk for result in results))
        self.assertEqual((Asignacion.objects.count(), Evento.objects.count()), (1, 2))

    def test_cambios_estado_confirmados_se_releen_tras_esperar_bloqueo(self):
        for target in ("actor", "operador", "oficina"):
            with self.subTest(target=target):
                started = Event()
                backend = {}
                def worker():
                    db = connections["default"]
                    try:
                        actor = Usuario.objects.get(pk=self.admin.pk)  # Lectura obsoleta intencional.
                        with db.cursor() as cursor:
                            cursor.execute("SET lock_timeout = '5s'")
                            cursor.execute("SELECT pg_backend_pid()")
                            backend["pid"] = cursor.fetchone()[0]
                        started.set()
                        try:
                            crear_asignacion(actor=actor, operador_id=self.operador.pk, oficina_id=self.oficina.pk)
                        except (PermissionDenied, ValidationError) as error:
                            return type(error)
                        return None
                    finally:
                        db.close()
                with ThreadPoolExecutor(max_workers=1) as pool:
                    with transaction.atomic():
                        obj = self.admin if target == "actor" else self.operador if target == "operador" else self.oficina
                        field = "activo" if target == "oficina" else "is_active"
                        setattr(obj, field, False)
                        obj.save(update_fields=[field])
                        future = pool.submit(worker)
                        self.assertTrue(started.wait(timeout=5))
                        blocked = False
                        deadline = monotonic() + 3
                        while monotonic() < deadline:
                            with connection.cursor() as cursor:
                                cursor.execute("SELECT cardinality(pg_blocking_pids(%s))", [backend["pid"]])
                                blocked = cursor.fetchone()[0] > 0
                            if blocked:
                                break
                            sleep(0.01)
                        self.assertTrue(blocked, "La otra conexión debe esperar el bloqueo real.")
                    self.assertIs(future.result(timeout=10), PermissionDenied if target == "actor" else ValidationError)
                setattr(obj, field, True)
                obj.save(update_fields=[field])
                self.assertEqual((Asignacion.objects.count(), Evento.objects.count()), (0, 0))
