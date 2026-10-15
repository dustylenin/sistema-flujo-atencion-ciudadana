"""Concurrencia PostgreSQL preparada, pendiente de ejecución aislada."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event
from uuid import uuid4

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection, connections

from oficinas.services import crear_asignacion
from oficinas.testing import CatalogosPostgreSQLTransactionTestCase
from oficinas.models import Oficina
from usuarios.models import Usuario

from . import test_llamado_concurrencia as llamado_concurrencia
from .models import Folio, PausaOperador, SolicitudOperador
from .services_disponibilidad import pausar_operador, reanudar_operador
from .services_inicio import iniciar_atencion
from .services_llamado import llamar_siguiente
from .test_inicio import InicioFixturesMixin


class InicioConcurrenciaTests(InicioFixturesMixin, CatalogosPostgreSQLTransactionTestCase):
    # Reutiliza coordinación y comprobación real de bloqueo sin heredar sus casos.
    contendientes = llamado_concurrencia.LlamadoConcurrenciaTests.contendientes
    assert_bloqueado_por = llamado_concurrencia.LlamadoConcurrenciaTests.assert_bloqueado_por

    def setUp(self):
        self.preparar()
        self.folio = self.reservar()

    def inicio(self, actor, clave=None):
        return iniciar_atencion(actor=actor, folio_id=self.folio.pk, solicitud_id=clave or uuid4())

    def test_misma_clave_un_inicio_evento_y_comprobante(self):
        clave = uuid4()
        antes = SolicitudOperador.objects.count()
        accion = lambda actor: self.inicio(actor, clave)
        uno, dos = self.contendientes(accion, accion)
        self.assertEqual((uno.resultado, dos.resultado), ("INICIADA", "INICIADA"))
        self.assertEqual((uno.evento_id, uno.confirmada_en), (dos.evento_id, dos.confirmada_en))
        self.assertEqual((uno.repetida, dos.repetida), (False, True))
        self.assertEqual((self.inicios().count(), SolicitudOperador.objects.count()), (1, antes + 1))

    def test_claves_distintas_conservan_un_solo_inicio(self):
        uno, dos = self.contendientes(self.inicio, self.inicio)
        self.assertEqual((uno.resultado, dos.resultado), ("INICIADA", "YA_EN_ATENCION"))
        self.assertIsNone(dos.evento_id)
        self.assertEqual(Folio.objects.get(pk=self.folio.pk).inicio_atencion, uno.confirmada_en)
        self.assertEqual(self.inicios().count(), 1)

    def test_rollback_del_primero_permite_confirmar_misma_clave(self):
        clave = uuid4()
        accion = lambda actor: self.inicio(actor, clave)
        _, dos = self.contendientes(accion, accion, revertir=True)
        self.assertEqual((dos.resultado, dos.repetida, self.inicios().count()), ("INICIADA", False, 1))
        self.assertEqual(SolicitudOperador.objects.filter(operacion="INICIAR").count(), 1)

    def test_inicio_antes_de_llamado_no_libera_capacidad(self):
        pendiente = self.registrar(self.segunda)
        llamar = lambda actor: llamar_siguiente(actor=actor, solicitud_id=uuid4())
        _, llamado = self.contendientes(self.inicio, llamar)
        self.assertEqual(llamado.resultado, "OCUPADO")
        self.assertEqual(Folio.objects.get(pk=pendiente.pk).estado, "EN_ESPERA")

    def test_llamado_antes_de_inicio_no_libera_capacidad(self):
        pendiente = self.registrar(self.segunda)
        llamado, inicio = self.contendientes(
            lambda actor: llamar_siguiente(actor=actor, solicitud_id=uuid4()), self.inicio,
        )
        self.assertEqual((llamado.resultado, inicio.resultado), ("OCUPADO", "INICIADA"))
        self.assertEqual(Folio.objects.get(pk=pendiente.pk).estado, "EN_ESPERA")

    def test_pausa_antes_de_inicio_confirma_en_pausa(self):
        pausa, inicio = self.contendientes(
            lambda actor: pausar_operador(actor=actor, motivo="Descanso", solicitud_id=uuid4()), self.inicio,
        )
        self.assertEqual(inicio.resultado, "EN_PAUSA")
        self.assertIsNone(Folio.objects.get(pk=self.folio.pk).inicio_atencion)
        self.assertEqual(PausaOperador.objects.get(pk=pausa.pausa_id).folio_contexto_id, self.folio.pk)

    def test_inicio_antes_de_pausa_conserva_atencion_y_fecha(self):
        inicio, pausa = self.contendientes(
            self.inicio, lambda actor: pausar_operador(actor=actor, motivo="Descanso", solicitud_id=uuid4()),
        )
        folio = Folio.objects.get(pk=self.folio.pk)
        self.assertEqual((folio.estado, folio.inicio_atencion), ("EN_ATENCION", inicio.confirmada_en))
        self.assertEqual(PausaOperador.objects.get(pk=pausa.pausa_id).folio_contexto_id, folio.pk)

    def test_reanudar_antes_de_nueva_intencion_permite_inicio(self):
        pausa = self.pausar()
        _, inicio = self.contendientes(
            lambda actor: reanudar_operador(actor=actor, pausa_id=pausa.pausa_id, solicitud_id=uuid4()), self.inicio,
        )
        self.assertEqual(inicio.resultado, "INICIADA")

    def test_inicio_en_pausa_antes_de_reanudar_conserva_comprobante(self):
        pausa = self.pausar()
        inicio, _ = self.contendientes(
            self.inicio,
            lambda actor: reanudar_operador(actor=actor, pausa_id=pausa.pausa_id, solicitud_id=uuid4()),
        )
        self.assertEqual(inicio.resultado, "EN_PAUSA")
        self.assertEqual(self.inicio(self.operador, inicio.solicitud_id).resultado, "EN_PAUSA")
        self.assertEqual(self.inicios().count(), 0)

    def test_operaciones_distintas_con_misma_clave_se_rechazan(self):
        clave = uuid4()
        def incompatible(actor):
            try:
                llamar_siguiente(actor=actor, solicitud_id=clave)
            except ValidationError:
                return True
            return False
        _, rechazado = self.contendientes(lambda actor: self.inicio(actor, clave), incompatible)
        self.assertTrue(rechazado)
        self.assertEqual(SolicitudOperador.objects.filter(solicitud_id=clave).count(), 1)

    def test_dos_operadores_comparten_oficina_sin_iniciar_folio_ajeno(self):
        pendiente = self.registrar()
        def ajeno(actor):
            try:
                return self.inicio(actor)
            except PermissionDenied:
                return "RECHAZADO"
        # El rechazo no intenta bloquear la oficina ajena; se comprueba por separado.
        self.assertEqual(ajeno(self.otro), "RECHAZADO")
        uno, dos = self.contendientes(
            self.inicio, lambda actor: llamar_siguiente(actor=actor, solicitud_id=uuid4()),
            actores=(self.operador.pk, self.otro.pk), tabla="oficinas_oficina",
        )
        self.assertEqual((uno.resultado, dos.folio_id), ("INICIADA", pendiente.pk))

    def test_desactivacion_antes_de_inicio_rechaza_instancia_obsoleta(self):
        def desactivar(actor):
            actor.is_active = False
            actor.save(update_fields=["is_active"])
        def intentar(actor):
            try:
                self.inicio(actor)
            except PermissionDenied:
                return True
            return False
        _, rechazado = self.contendientes(desactivar, intentar)
        self.assertTrue(rechazado)
        self.assertEqual(self.inicios().count(), 0)

    def test_inicio_antes_de_desactivacion_conserva_evidencia_y_bloquea_reintento(self):
        def desactivar(actor):
            actor.is_active = False
            actor.save(update_fields=["is_active"])
        inicio, _ = self.contendientes(self.inicio, desactivar)
        self.assertEqual(self.inicios().count(), 1)
        with self.assertRaises(PermissionDenied):
            self.inicio(self.operador, inicio.solicitud_id)

    def cambiar_rol(self, actor):
        # Fixture histórica, sin habilitar salida pública de OPERADOR.
        with connection.cursor() as cursor:
            cursor.execute('SELECT id FROM "usuarios_usuario" WHERE id=%s FOR UPDATE', [actor.pk])
            cursor.execute("UPDATE usuarios_usuario SET rol='RECEPCION' WHERE id=%s", [actor.pk])

    def test_cambio_rol_antes_de_inicio_revalida_despues_de_esperar(self):
        def intentar(actor):
            try:
                self.inicio(actor)
            except PermissionDenied:
                return True
            return False
        _, rechazado = self.contendientes(self.cambiar_rol, intentar)
        self.assertTrue(rechazado)
        self.assertEqual(self.inicios().count(), 0)

    def test_inicio_antes_de_cambio_rol_conserva_historia_sin_permitir_reintento(self):
        inicio, _ = self.contendientes(self.inicio, self.cambiar_rol)
        self.assertEqual(self.inicios().count(), 1)
        with self.assertRaises(PermissionDenied):
            self.inicio(self.operador, inicio.solicitud_id)

    def test_crear_asignacion_antes_de_inicio_no_es_requisito_de_autorizacion(self):
        _, inicio = self.contendientes(
            lambda actor: crear_asignacion(actor=actor, operador_id=self.operador.pk, oficina_id=self.ajena.pk),
            self.inicio, actores=(self.admin.pk, self.operador.pk),
        )
        self.assertEqual(inicio.resultado, "INICIADA")

    def test_inicio_antes_de_asignacion_es_compatible(self):
        inicio, _ = self.contendientes(
            self.inicio,
            lambda actor: crear_asignacion(actor=actor, operador_id=self.operador.pk, oficina_id=self.ajena.pk),
            actores=(self.operador.pk, self.admin.pk),
        )
        self.assertEqual(inicio.resultado, "INICIADA")

    def desactivar_oficina(self, actor):
        oficina = Oficina.objects.select_for_update().get(pk=self.oficina.pk)
        oficina.activo = False
        oficina.save(update_fields=["activo"])

    def test_catalogo_desactivado_antes_de_inicio_no_revoca_responsabilidad(self):
        _, inicio = self.contendientes(
            self.desactivar_oficina, self.inicio, actores=(self.admin.pk, self.operador.pk), tabla="oficinas_oficina",
        )
        self.assertEqual(inicio.resultado, "INICIADA")

    def test_inicio_antes_de_desactivar_catalogo_conserva_atencion(self):
        inicio, _ = self.contendientes(
            self.inicio, self.desactivar_oficina, actores=(self.operador.pk, self.admin.pk), tabla="oficinas_oficina",
        )
        self.assertEqual(inicio.resultado, "INICIADA")
        self.assertEqual(Folio.objects.get(pk=self.folio.pk).estado, "EN_ATENCION")

    def test_inicios_en_oficinas_disjuntas_avanzan_independientemente(self):
        crear_asignacion(actor=self.admin, operador_id=self.otro.pk, oficina_id=self.ajena.pk)
        folio_otro = self.registrar(self.ajena)
        self.llamar(actor=self.otro)
        retenido, liberar = Event(), Event()
        pids = {}
        def worker(indice):
            db = connections["default"]
            try:
                actor = Usuario.objects.get(pk=(self.operador.pk, self.otro.pk)[indice])
                with db.cursor() as cursor:
                    cursor.execute("SET lock_timeout = '8s'")
                    cursor.execute("SET statement_timeout = '12s'")
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
                            raise TimeoutError("No se liberó la oficina del primer inicio.")
                    return resultado
                with db.execute_wrapper(coordinar):
                    return iniciar_atencion(actor=actor, folio_id=(self.folio.pk, folio_otro.pk)[indice], solicitud_id=uuid4())
            finally:
                db.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            uno = pool.submit(worker, 0)
            try:
                self.assertTrue(retenido.wait(timeout=5))
                dos = pool.submit(worker, 1).result(timeout=5)
                self.assertNotEqual(pids[0], pids[1])
                self.assertFalse(liberar.is_set())
                self.assertEqual(dos.resultado, "INICIADA")
            finally:
                liberar.set()
            self.assertEqual(uno.result(timeout=15).resultado, "INICIADA")
