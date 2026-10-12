"""Concurrencia preparada, todavía no ejecutada; requiere folios.0003 aplicada."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event
from time import monotonic, sleep
from uuid import uuid4

from django.core.exceptions import PermissionDenied
from django.db import connection, connections, transaction

from oficinas.models import AsignacionOperadorOficina
from oficinas.services import crear_asignacion, reactivar_asignacion
from oficinas.testing import CatalogosPostgreSQLTransactionTestCase
from usuarios.models import Usuario

from .models import Folio, PausaOperador, SolicitudOperador
from .services import registrar_folio
from .services_disponibilidad import pausar_operador, reanudar_operador
from .services_llamado import llamar_siguiente
from .test_llamado import LlamadoFixturesMixin


class LlamadoConcurrenciaTests(LlamadoFixturesMixin, CatalogosPostgreSQLTransactionTestCase):
    def setUp(self):
        self.preparar()

    def assert_bloqueado_por(self, bloqueado, bloqueador):
        self.assertNotEqual(bloqueado, bloqueador)
        limite = monotonic() + 4
        while monotonic() < limite:
            with connection.cursor() as cursor:
                cursor.execute("SELECT %s = ANY(pg_blocking_pids(%s))", [bloqueador, bloqueado])
                if cursor.fetchone()[0]:
                    return
            sleep(0.01)
        self.fail("No se verificó contención real con PIDs distintos.")

    def contendientes(self, primera, segunda, *, actores=None, tabla="usuarios_usuario", revertir=False):
        actores = actores or (self.operador.pk, self.operador.pk)
        retenido, intentando, liberar = Event(), Event(), Event()
        pids = {}

        def worker(accion, indice):
            db = connections["default"]
            try:
                actor = Usuario.objects.get(pk=actores[indice])
                with db.cursor() as cursor:
                    cursor.execute("SET lock_timeout = '8s'")
                    cursor.execute("SET statement_timeout = '12s'")
                    cursor.execute("SELECT pg_backend_pid()")
                    pids[indice] = cursor.fetchone()[0]
                coordinado = False
                def coordinar(execute, sql, params, many, context):
                    nonlocal coordinado
                    bloqueo = "FOR UPDATE" in sql.upper() and f'"{tabla}"' in sql
                    if bloqueo and indice == 1:
                        intentando.set()
                    resultado = execute(sql, params, many, context)
                    if bloqueo and indice == 0 and not coordinado:
                        coordinado = True
                        retenido.set()
                        if not liberar.wait(timeout=10):
                            raise TimeoutError("No se liberó el bloqueo coordinado.")
                    return resultado
                with transaction.atomic(), db.execute_wrapper(coordinar):
                    resultado = accion(actor)
                    if indice == 0 and revertir:
                        transaction.set_rollback(True)
                return resultado
            finally:
                db.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            uno = pool.submit(worker, primera, 0)
            try:
                self.assertTrue(retenido.wait(timeout=5))
                dos = pool.submit(worker, segunda, 1)
                self.assertTrue(intentando.wait(timeout=5))
                self.assert_bloqueado_por(pids[1], pids[0])
            finally:
                liberar.set()
            return uno.result(timeout=15), dos.result(timeout=15)

    def test_misma_clave_un_llamado_un_evento_un_comprobante(self):
        self.registrar()
        clave = uuid4()
        accion = lambda actor: llamar_siguiente(actor=actor, solicitud_id=clave)
        uno, dos = self.contendientes(accion, accion)
        self.assertEqual((uno.resultado, dos.resultado), ("LLAMADO", "LLAMADO"))
        self.assertEqual((uno.folio_id, uno.evento_id, uno.confirmada_en), (dos.folio_id, dos.evento_id, dos.confirmada_en))
        self.assertEqual((uno.repetida, dos.repetida), (False, True))
        self.assertEqual((self.llamados().count(), SolicitudOperador.objects.count()), (1, 1))

    def test_claves_distintas_del_mismo_operador_no_superan_capacidad(self):
        self.registrar()
        self.registrar(self.segunda)
        accion = lambda actor: llamar_siguiente(actor=actor, solicitud_id=uuid4())
        uno, dos = self.contendientes(accion, accion)
        self.assertEqual((uno.resultado, dos.resultado), ("LLAMADO", "OCUPADO"))
        self.assertEqual((dos.folio_id, dos.evento_id), (None, None))
        self.assertEqual(Folio.objects.filter(estado="LLAMADO").count(), 1)
        self.assertEqual(SolicitudOperador.objects.count(), 2)

    def test_dos_operadores_un_pendiente_no_reservan_el_mismo(self):
        folio = self.registrar()
        accion = lambda actor: llamar_siguiente(actor=actor, solicitud_id=uuid4())
        uno, dos = self.contendientes(accion, accion, actores=(self.operador.pk, self.otro.pk), tabla="oficinas_oficina")
        self.assertEqual((uno.resultado, dos.resultado), ("LLAMADO", "SIN_PENDIENTES"))
        folio.refresh_from_db()
        self.assertEqual(folio.operador_responsable_id, self.operador.pk)
        self.assertEqual(self.llamados().count(), 1)

    def test_dos_operadores_dos_pendientes_respetan_llegada_despues_de_esperar(self):
        from django.utils import timezone
        antiguo = self.registrar(llegada=timezone.now() - timedelta(hours=1))
        reciente = self.registrar()
        accion = lambda actor: llamar_siguiente(actor=actor, solicitud_id=uuid4())
        uno, dos = self.contendientes(accion, accion, actores=(self.operador.pk, self.otro.pk), tabla="oficinas_oficina")
        self.assertEqual((uno.folio_id, dos.folio_id), (antiguo.pk, reciente.pk))

    def test_rollback_del_primero_devuelve_el_mas_antiguo_al_segundo(self):
        from django.utils import timezone
        antiguo = self.registrar(llegada=timezone.now() - timedelta(hours=1))
        reciente = self.registrar()
        accion = lambda actor: llamar_siguiente(actor=actor, solicitud_id=uuid4())
        uno, dos = self.contendientes(accion, accion, actores=(self.operador.pk, self.otro.pk), tabla="oficinas_oficina", revertir=True)
        self.assertEqual((uno.folio_id, dos.folio_id), (antiguo.pk, antiguo.pk))
        self.assertFalse(SolicitudOperador.objects.filter(solicitud_id=uno.solicitud_id).exists())
        reciente.refresh_from_db()
        self.assertEqual(reciente.estado, "EN_ESPERA")
        self.assertEqual((self.llamados().count(), SolicitudOperador.objects.count()), (1, 1))

    def test_rollback_misma_clave_no_deja_comprobante_parcial(self):
        self.registrar()
        clave = uuid4()
        accion = lambda actor: llamar_siguiente(actor=actor, solicitud_id=clave)
        uno, dos = self.contendientes(accion, accion, revertir=True)
        self.assertEqual((uno.resultado, dos.resultado, dos.repetida), ("LLAMADO", "LLAMADO", False))
        self.assertEqual((self.llamados().count(), SolicitudOperador.objects.count()), (1, 1))

    def test_colas_solapadas_con_varias_oficinas_no_invierten_orden_de_bloqueos(self):
        crear_asignacion(actor=self.admin, operador_id=self.otro.pk, oficina_id=self.segunda.pk)
        uno = self.registrar(self.segunda)
        dos = self.registrar(self.oficina)
        accion = lambda actor: llamar_siguiente(actor=actor, solicitud_id=uuid4())
        primero, segundo = self.contendientes(accion, accion, actores=(self.operador.pk, self.otro.pk), tabla="oficinas_oficina")
        self.assertEqual({primero.folio_id, segundo.folio_id}, {uno.pk, dos.pk})

    def test_colas_disjuntas_avanzan_mientras_la_otra_oficina_sigue_bloqueada(self):
        otra_asignacion = AsignacionOperadorOficina.objects.get(operador=self.otro, oficina=self.oficina)
        self.historica_inactiva(otra_asignacion.pk)
        crear_asignacion(actor=self.admin, operador_id=self.otro.pk, oficina_id=self.ajena.pk)
        folio_uno, folio_dos = self.registrar(), self.registrar(self.ajena)
        retenido, liberar = Event(), Event()
        pids = {}
        def worker(indice):
            db = connections["default"]
            try:
                actor = Usuario.objects.get(pk=(self.operador.pk, self.otro.pk)[indice])
                with db.cursor() as cursor:
                    cursor.execute("SET lock_timeout = '8s'")
                    cursor.execute("SELECT pg_backend_pid()")
                    pids[indice] = cursor.fetchone()[0]
                coordinado = False
                def coordinar(execute, sql, params, many, context):
                    nonlocal coordinado
                    resultado = execute(sql, params, many, context)
                    if indice == 0 and not coordinado and "FOR UPDATE" in sql and '"oficinas_oficina"' in sql:
                        coordinado = True
                        retenido.set()
                        if not liberar.wait(timeout=10):
                            raise TimeoutError("No se liberó la oficina de la primera cola.")
                    return resultado
                with db.execute_wrapper(coordinar):
                    return llamar_siguiente(actor=actor, solicitud_id=uuid4())
            finally:
                db.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            uno = pool.submit(worker, 0)
            try:
                self.assertTrue(retenido.wait(timeout=5))
                dos = pool.submit(worker, 1).result(timeout=5)
                self.assertNotEqual(pids[0], pids[1])
                self.assertFalse(liberar.is_set())
                self.assertEqual(dos.folio_id, folio_dos.pk)
            finally:
                liberar.set()
            self.assertEqual(uno.result(timeout=15).folio_id, folio_uno.pk)

    def test_pausar_antes_de_llamar_confirma_en_pausa(self):
        self.registrar()
        pausa, llamado = self.contendientes(
            lambda actor: pausar_operador(actor=actor, motivo="Descanso", solicitud_id=uuid4()),
            lambda actor: llamar_siguiente(actor=actor, solicitud_id=uuid4()),
        )
        self.assertEqual((pausa.resultado, llamado.resultado), ("PAUSADA", "EN_PAUSA"))
        self.assertEqual(self.llamados().count(), 0)

    def test_llamar_antes_de_pausar_conserva_contexto_real(self):
        self.registrar()
        llamado, pausa = self.contendientes(
            lambda actor: llamar_siguiente(actor=actor, solicitud_id=uuid4()),
            lambda actor: pausar_operador(actor=actor, motivo="Descanso", solicitud_id=uuid4()),
        )
        self.assertEqual(PausaOperador.objects.get(pk=pausa.pausa_id).folio_contexto_id, llamado.folio_id)
        self.assertEqual(Folio.objects.get(pk=llamado.folio_id).estado, "LLAMADO")

    def test_reanudar_antes_de_nuevo_llamado_libera_solo_la_pausa(self):
        self.registrar()
        pausa = self.pausar()
        reanudacion, llamado = self.contendientes(
            lambda actor: reanudar_operador(actor=actor, pausa_id=pausa.pausa_id, solicitud_id=uuid4()),
            lambda actor: llamar_siguiente(actor=actor, solicitud_id=uuid4()),
        )
        self.assertEqual((reanudacion.resultado, llamado.resultado), ("REANUDADA", "LLAMADO"))

    def test_llamar_en_pausa_antes_de_reanudar_no_deja_intencion_pendiente(self):
        self.registrar()
        pausa = self.pausar()
        llamado, _ = self.contendientes(
            lambda actor: llamar_siguiente(actor=actor, solicitud_id=uuid4()),
            lambda actor: reanudar_operador(actor=actor, pausa_id=pausa.pausa_id, solicitud_id=uuid4()),
        )
        repetido = self.llamar(solicitud_id=llamado.solicitud_id)
        self.assertEqual((repetido.resultado, repetido.repetida), ("EN_PAUSA", True))
        self.assertEqual(self.llamados().count(), 0)

    def test_desactivacion_antes_del_llamado_rechaza_instancia_obsoleta(self):
        self.registrar()
        def desactivar(actor):
            actor.is_active = False
            actor.save(update_fields=["is_active"])
        def intentar(actor):
            try:
                llamar_siguiente(actor=actor, solicitud_id=uuid4())
            except PermissionDenied:
                return True
            return False
        _, rechazado = self.contendientes(desactivar, intentar)
        self.assertTrue(rechazado)
        self.assertEqual((self.llamados().count(), SolicitudOperador.objects.count()), (0, 0))

    def test_llamado_antes_de_desactivacion_conserva_reserva(self):
        self.registrar()
        def desactivar(actor):
            actor.is_active = False
            actor.save(update_fields=["is_active"])
        llamado, _ = self.contendientes(lambda actor: llamar_siguiente(actor=actor, solicitud_id=uuid4()), desactivar)
        self.assertEqual(Folio.objects.get(pk=llamado.folio_id).operador_responsable_id, self.operador.pk)
        with self.assertRaises(PermissionDenied):
            self.llamar(solicitud_id=llamado.solicitud_id)

    def test_cambio_de_rol_antes_de_llamado_revalida_despues_de_esperar(self):
        self.registrar()
        def cambiar_rol(actor):
            # Fixture histórica bajo bloqueo: no habilita salida funcional.
            with connection.cursor() as cursor:
                cursor.execute('SELECT id FROM "usuarios_usuario" WHERE id = %s FOR UPDATE', [actor.pk])
                cursor.execute("UPDATE usuarios_usuario SET rol = 'RECEPCION' WHERE id = %s", [actor.pk])
        def intentar(actor):
            try:
                llamar_siguiente(actor=actor, solicitud_id=uuid4())
            except PermissionDenied:
                return True
            return False
        _, rechazado = self.contendientes(cambiar_rol, intentar)
        self.assertTrue(rechazado)
        self.assertEqual((self.llamados().count(), SolicitudOperador.objects.count()), (0, 0))

    def test_registro_antes_de_llamado_se_incluye_despues_de_esperar(self):
        registro, llamado = self.contendientes(
            lambda actor: registrar_folio(actor=actor, nombre_completo="Prueba", oficina_id=self.oficina.pk, tramite_id=self.tramites[self.oficina.pk].pk),
            lambda actor: llamar_siguiente(actor=actor, solicitud_id=uuid4()),
            actores=(self.recepcion.pk, self.operador.pk), tabla="oficinas_oficina",
        )
        self.assertEqual(llamado.folio_id, registro.folio_id)

    def test_llamado_antes_de_registro_no_reinterpreta_sin_pendientes(self):
        llamado, registro = self.contendientes(
            lambda actor: llamar_siguiente(actor=actor, solicitud_id=uuid4()),
            lambda actor: registrar_folio(actor=actor, nombre_completo="Prueba", oficina_id=self.oficina.pk, tramite_id=self.tramites[self.oficina.pk].pk),
            actores=(self.operador.pk, self.recepcion.pk), tabla="oficinas_oficina",
        )
        self.assertEqual(llamado.resultado, "SIN_PENDIENTES")
        self.assertEqual(self.llamar(solicitud_id=llamado.solicitud_id).resultado, "SIN_PENDIENTES")
        self.assertEqual(self.llamar().folio_id, registro.folio_id)

    def test_crear_asignacion_antes_de_llamar_incluye_nueva_oficina(self):
        folio = self.registrar(self.ajena)
        _, llamado = self.contendientes(
            lambda actor: crear_asignacion(actor=actor, operador_id=self.operador.pk, oficina_id=self.ajena.pk),
            lambda actor: llamar_siguiente(actor=actor, solicitud_id=uuid4()),
            actores=(self.admin.pk, self.operador.pk),
        )
        self.assertEqual(llamado.folio_id, folio.pk)

    def test_reactivar_asignacion_antes_de_llamar_conserva_evidencia(self):
        self.historica_inactiva(self.asignaciones[self.oficina.pk])
        folio = self.registrar()
        _, llamado = self.contendientes(
            lambda actor: reactivar_asignacion(actor=actor, operador_id=self.operador.pk, oficina_id=self.oficina.pk),
            lambda actor: llamar_siguiente(actor=actor, solicitud_id=uuid4()),
            actores=(self.admin.pk, self.operador.pk),
        )
        self.assertEqual(llamado.folio_id, folio.pk)

    def test_llamar_antes_de_crear_asignacion_conserva_resultado_historico(self):
        folio = self.registrar(self.ajena)
        llamado, _ = self.contendientes(
            lambda actor: llamar_siguiente(actor=actor, solicitud_id=uuid4()),
            lambda actor: crear_asignacion(actor=actor, operador_id=self.operador.pk, oficina_id=self.ajena.pk),
            actores=(self.operador.pk, self.admin.pk),
        )
        self.assertEqual(llamado.resultado, "SIN_PENDIENTES")
        self.assertEqual(self.llamar(solicitud_id=llamado.solicitud_id).resultado, "SIN_PENDIENTES")
        self.assertEqual(self.llamar().folio_id, folio.pk)
