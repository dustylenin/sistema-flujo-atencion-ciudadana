"""Pruebas preparadas para folios.0003; no ejecutarlas durante la revisión DEMO."""

from dataclasses import FrozenInstanceError, asdict
from datetime import timedelta
from itertools import product
from unittest.mock import patch
from uuid import uuid4

from asgiref.sync import async_to_sync
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection, models, NotSupportedError, transaction
from django.db.models.deletion import ProtectedError
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from oficinas.models import AsignacionOperadorOficina, Oficina
from oficinas.services import crear_asignacion, reactivar_asignacion
from oficinas.testing import CatalogosPostgreSQLTestCase
from tramites.models import Tramite
from usuarios.models import Usuario

from .models import EventoFolio, Folio, PausaOperador, SolicitudOperador
from .services import registrar_folio
from .services_disponibilidad import Disponibilidad, consultar_disponibilidad, consultar_pausas
from .services_llamado import EstadoLlamado, llamar_siguiente
from .test_disponibilidad import DisponibilidadFixturesMixin, ejecutar_async


class LlamadoFixturesMixin(DisponibilidadFixturesMixin):
    def preparar(self):
        super().preparar()
        self.oficina = Oficina.objects.create(nombre="Primera")
        self.segunda = Oficina.objects.create(nombre="Segunda")
        self.ajena = Oficina.objects.create(nombre="Sin asignación")
        self.tramites = {
            oficina.pk: Tramite.objects.create(nombre="Solicitud", oficina=oficina)
            for oficina in (self.oficina, self.segunda, self.ajena)
        }
        self.asignaciones = {}
        for oficina in (self.oficina, self.segunda):
            resultado = crear_asignacion(actor=self.admin, operador_id=self.operador.pk, oficina_id=oficina.pk)
            self.asignaciones[oficina.pk] = resultado.asignacion_id
        crear_asignacion(actor=self.admin, operador_id=self.otro.pk, oficina_id=self.oficina.pk)

    def registrar(self, oficina=None, llegada=None):
        oficina = oficina or self.oficina
        with patch("folios.services.timezone.now", return_value=llegada or timezone.now()):
            resultado = registrar_folio(
                actor=self.recepcion, nombre_completo="Ciudadano ficticio de pruebas",
                oficina_id=oficina.pk, tramite_id=self.tramites[oficina.pk].pk,
            )
        return Folio.objects.get(pk=resultado.folio_id)

    def llamar(self, **extra):
        options = {"actor": self.operador, "solicitud_id": uuid4()}
        options.update(extra)
        return llamar_siguiente(**options)

    def llamados(self):
        return EventoFolio.objects.filter(operacion="LLAMADO")

    def snapshot(self):
        return (
            list(Folio.objects.order_by("pk").values()),
            list(EventoFolio.objects.order_by("pk").values()),
            list(SolicitudOperador.objects.order_by("pk").values()),
        )

    def historica_inactiva(self, asignacion_id):
        # Solo fixture de pruebas aisladas; no habilita retirada pública.
        with connection.cursor() as cursor:
            cursor.execute("UPDATE oficinas_asignacionoperadoroficina SET activo = false WHERE id = %s", [asignacion_id])


class LlamadoTests(LlamadoFixturesMixin, CatalogosPostgreSQLTestCase):
    def setUp(self):
        self.preparar()

    def test_reserva_evento_y_comprobante_conservan_registro(self):
        folio = self.registrar()
        anterior = Folio.objects.filter(pk=folio.pk).values().get()
        creacion = list(EventoFolio.objects.filter(folio=folio).values())
        instante = timezone.now()
        clave = uuid4()
        with patch("folios.services_llamado.timezone.now", return_value=instante):
            resultado = self.llamar(solicitud_id=str(clave))
        folio.refresh_from_db()
        evento = EventoFolio.objects.get(pk=resultado.evento_id)
        solicitud = SolicitudOperador.objects.get(solicitud_id=clave)
        self.assertEqual((resultado.resultado, resultado.folio_id, resultado.repetida), (EstadoLlamado.LLAMADO, folio.pk, False))
        self.assertEqual((folio.estado, folio.operador_responsable_id), ("LLAMADO", self.operador.pk))
        despues = Folio.objects.filter(pk=folio.pk).values().get()
        for campo in anterior.keys() - {"estado", "operador_responsable_id"}:
            self.assertEqual(anterior[campo], despues[campo])
        self.assertEqual(list(EventoFolio.objects.filter(folio=folio, operacion="CREACION").values()), creacion)
        self.assertEqual((evento.actor_id, evento.operador_responsable_id, evento.asignacion_autorizante_id),
                         (self.operador.pk, self.operador.pk, self.asignaciones[self.oficina.pk]))
        self.assertEqual((evento.estado_anterior, evento.estado_nuevo, evento.datos_iniciales), ("EN_ESPERA", "LLAMADO", None))
        self.assertEqual((evento.fecha, solicitud.confirmada_en, resultado.confirmada_en), (instante, instante, instante))
        self.assertEqual((solicitud.operacion, solicitud.folio_resultado_id, solicitud.evento_folio_resultado_id), ("LLAMAR", folio.pk, evento.pk))
        self.assertEqual((solicitud.pausa_resultado_id, solicitud.evento_resultado_id, solicitud.motivo_solicitado, solicitud.pausa_objetivo_id), (None, None, None, None))
        with self.assertRaises(FrozenInstanceError):
            resultado.folio_id = uuid4()

    def test_cola_conjunta_llegada_mas_antigua_y_exclusion_de_ajenos(self):
        ahora = timezone.now()
        self.registrar(self.ajena, ahora - timedelta(hours=2))
        reciente = self.registrar(self.oficina, ahora)
        antiguo = self.registrar(self.segunda, ahora - timedelta(hours=1))
        self.assertEqual(self.llamar().folio_id, antiguo.pk)
        reciente.refresh_from_db()
        self.assertEqual(reciente.estado, "EN_ESPERA")

    def test_desempate_por_uuid_con_llegadas_iguales(self):
        instante = timezone.now()
        folios = [self.registrar(oficina, instante) for oficina in (self.segunda, self.oficina)]
        self.assertEqual(self.llamar().folio_id, min(folio.pk for folio in folios))

    def test_oficina_y_tramite_desactivados_no_ocultan_pendiente(self):
        folio = self.registrar()
        self.oficina.activo = False
        self.oficina.save(update_fields=["activo"])
        tramite = self.tramites[self.oficina.pk]
        tramite.activo = False
        tramite.save(update_fields=["activo"])
        self.assertEqual(self.llamar().folio_id, folio.pk)
        estado = consultar_disponibilidad(actor=self.operador, operador_id=self.operador.pk)
        self.assertEqual(estado.disponibilidad, Disponibilidad.OCUPADO)

    def test_asignacion_inactiva_no_incluye_sus_pendientes(self):
        self.registrar(self.oficina, timezone.now() - timedelta(hours=1))
        valido = self.registrar(self.segunda)
        self.historica_inactiva(self.asignaciones[self.oficina.pk])
        self.assertEqual(self.llamar().folio_id, valido.pk)

    def test_sin_asignaciones_y_sin_pendientes_solo_comprobante(self):
        resultado = self.llamar()
        self.assertEqual(resultado.resultado, EstadoLlamado.SIN_PENDIENTES)
        for pk in self.asignaciones.values():
            self.historica_inactiva(pk)
        resultado = self.llamar()
        self.assertEqual(resultado.resultado, EstadoLlamado.SIN_ASIGNACIONES)
        self.assertEqual((resultado.folio_id, resultado.evento_id), (None, None))
        self.assertEqual((Folio.objects.count(), EventoFolio.objects.count(), SolicitudOperador.objects.count()), (0, 0, 2))

    def test_capacidad_global_no_es_una_por_oficina(self):
        primero = self.registrar(self.oficina, timezone.now() - timedelta(hours=1))
        segundo = self.registrar(self.segunda)
        self.assertEqual(self.llamar().folio_id, primero.pk)
        resultado = self.llamar()
        self.assertEqual((resultado.resultado, resultado.folio_id, resultado.evento_id), (EstadoLlamado.OCUPADO, None, None))
        segundo.refresh_from_db()
        self.assertEqual(segundo.estado, "EN_ESPERA")
        self.assertEqual(self.llamados().count(), 1)

    def test_varios_operadores_por_oficina_reservan_folios_distintos(self):
        primero = self.registrar(llegada=timezone.now() - timedelta(hours=1))
        segundo = self.registrar()
        self.assertEqual(self.llamar().folio_id, primero.pk)
        self.assertEqual(self.llamar(actor=self.otro).folio_id, segundo.pk)

    def test_pausa_sin_folio_bloquea_y_repeticion_conserva_resultado(self):
        self.registrar()
        pausa = self.pausar()
        clave = uuid4()
        resultado = self.llamar(solicitud_id=clave)
        self.assertEqual((resultado.resultado, resultado.folio_id, resultado.evento_id), (EstadoLlamado.EN_PAUSA, None, None))
        self.reanudar(pausa.pausa_id)
        antes = self.snapshot()
        repetida = self.llamar(solicitud_id=clave)
        self.assertTrue(repetida.repetida)
        self.assertEqual(repetida.resultado, EstadoLlamado.EN_PAUSA)
        self.assertEqual(antes, self.snapshot())
        self.assertEqual(self.llamar().resultado, EstadoLlamado.LLAMADO)

    def test_pausa_con_llamado_real_preserva_folio_y_reanuda_ocupado(self):
        folio = self.registrar()
        llamado = self.llamar()
        antes = Folio.objects.filter(pk=folio.pk).values().get()
        pausa = self.pausar()
        registro = PausaOperador.objects.get(pk=pausa.pausa_id)
        self.assertEqual((registro.folio_contexto_id, registro.oficina_contexto_id), (folio.pk, folio.oficina_id))
        self.assertEqual(self.llamar().resultado, EstadoLlamado.EN_PAUSA)
        self.assertEqual(consultar_disponibilidad(actor=self.operador, operador_id=self.operador.pk).disponibilidad, Disponibilidad.EN_PAUSA)
        self.reanudar(pausa.pausa_id)
        self.assertEqual(consultar_disponibilidad(actor=self.operador, operador_id=self.operador.pk).disponibilidad, Disponibilidad.OCUPADO)
        self.assertEqual(Folio.objects.filter(pk=folio.pk).values().get(), antes)
        self.assertEqual(self.llamar(solicitud_id=llamado.solicitud_id).folio_id, folio.pk)
        historial = consultar_pausas(actor=self.admin, operador_id=self.operador.pk)
        self.assertEqual((historial[0].folio_id, len(historial[0].eventos)), (folio.pk, 2))

    def test_folio_actual_global_con_asignacion_historica_inactiva(self):
        folio = self.registrar()
        self.llamar()
        self.historica_inactiva(self.asignaciones[self.oficina.pk])
        self.assertEqual(self.llamar().resultado, EstadoLlamado.OCUPADO)
        estado = consultar_disponibilidad(actor=self.operador, operador_id=self.operador.pk)
        self.assertEqual(estado.folio_actual.folio_id, folio.pk)
        self.assertEqual(self.pausar().resultado, "PAUSADA")

    def test_autorizacion_vigente_incluso_en_repeticion(self):
        self.registrar()
        clave = uuid4()
        self.llamar(solicitud_id=clave)
        self.operador.is_active = False
        self.operador.save(update_fields=["is_active"])
        antes = self.snapshot()
        with self.assertRaises(PermissionDenied):
            self.llamar(solicitud_id=clave)
        self.assertEqual(self.snapshot(), antes)

    def test_rol_obsoleto_no_autoriza_nueva_ni_repetida(self):
        resultado = self.llamar()
        # Cambio histórico controlado; no habilita salida pública de OPERADOR.
        with connection.cursor() as cursor:
            cursor.execute("UPDATE usuarios_usuario SET rol = 'RECEPCION' WHERE id = %s", [self.operador.pk])
        antes = self.snapshot()
        for clave in (resultado.solicitud_id, uuid4()):
            with self.assertRaises(PermissionDenied):
                self.llamar(solicitud_id=clave)
        self.assertEqual(self.snapshot(), antes)

    def test_anonimo_no_persistido_o_de_otro_alias_no_autoriza(self):
        ajeno = Usuario.objects.get(pk=self.operador.pk)
        ajeno._state.db = "otra_base"
        for actor in (AnonymousUser(), Usuario(rol="OPERADOR"), ajeno):
            with self.assertRaises(PermissionDenied):
                self.llamar(actor=actor)
        self.assertEqual(SolicitudOperador.objects.count(), 0)

    def test_flags_tecnicos_no_sustituyen_rol_y_operador_no_los_necesita(self):
        for actor in (self.recepcion, self.admin):
            actor.is_staff = actor.is_superuser = True
            actor.save(update_fields=["is_staff", "is_superuser"])
            with self.assertRaises(PermissionDenied):
                self.llamar(actor=actor)
        for staff, superuser in product((False, True), repeat=2):
            self.operador.is_staff, self.operador.is_superuser = staff, superuser
            self.operador.save(update_fields=["is_staff", "is_superuser"])
            self.assertEqual(self.llamar().resultado, EstadoLlamado.SIN_PENDIENTES)

    def test_clave_invalida_y_argumentos_reservados_no_escriben(self):
        for clave in (None, 1, b"abc", "no-uuid"):
            with self.assertRaises(ValidationError):
                self.llamar(solicitud_id=clave)
        for campo in ("oficina_id", "folio_id", "operador_id", "estado", "fecha", "using", "omitir_validaciones"):
            with self.assertRaises(TypeError):
                self.llamar(**{campo: 1})
        self.assertEqual(SolicitudOperador.objects.count(), 0)

    def test_repeticion_llamado_precede_estado_actual_y_no_escribe(self):
        self.registrar()
        resultado = self.llamar()
        self.pausar()
        antes = self.snapshot()
        with patch("folios.services_llamado._asignaciones_bloqueadas", side_effect=AssertionError("No debe consultar asignaciones")):
            repetida = self.llamar(solicitud_id=resultado.solicitud_id)
        self.assertEqual({k: v for k, v in asdict(repetida).items() if k != "repetida"},
                         {k: v for k, v in asdict(resultado).items() if k != "repetida"})
        self.assertTrue(repetida.repetida)
        self.assertEqual(self.snapshot(), antes)

    def test_sin_pendientes_historico_no_llama_un_registro_posterior(self):
        resultado = self.llamar()
        self.registrar()
        antes = self.snapshot()
        self.assertEqual(self.llamar(solicitud_id=resultado.solicitud_id).resultado, EstadoLlamado.SIN_PENDIENTES)
        self.assertEqual(self.snapshot(), antes)
        self.assertEqual(self.llamar().resultado, EstadoLlamado.LLAMADO)

    def test_sin_asignaciones_historico_no_llama_tras_reactivar(self):
        for pk in self.asignaciones.values():
            self.historica_inactiva(pk)
        resultado = self.llamar()
        self.registrar()
        reactivar_asignacion(actor=self.admin, operador_id=self.operador.pk, oficina_id=self.oficina.pk)
        self.assertEqual(self.llamar(solicitud_id=resultado.solicitud_id).resultado, EstadoLlamado.SIN_ASIGNACIONES)
        self.assertEqual(self.llamados().count(), 0)
        self.assertEqual(self.llamar().resultado, EstadoLlamado.LLAMADO)

    def test_clave_compartida_entre_operaciones_rechaza_incompatibles(self):
        pausa = self.pausar()
        reanudada = self.reanudar(pausa.pausa_id)
        for clave in (pausa.solicitud_id, reanudada.solicitud_id):
            with self.assertRaises(ValidationError):
                self.llamar(solicitud_id=clave)
        llamado = self.llamar()
        antes = self.snapshot()
        with self.assertRaises(ValidationError):
            self.pausar(solicitud_id=llamado.solicitud_id)
        with self.assertRaises(ValidationError):
            self.reanudar(pausa.pausa_id, solicitud_id=llamado.solicitud_id)
        self.assertEqual(self.snapshot(), antes)

    def test_misma_clave_de_otro_operador_tiene_ambito_independiente(self):
        self.registrar()
        self.registrar()
        clave = uuid4()
        uno = self.llamar(solicitud_id=clave)
        otro = self.llamar(actor=self.otro, solicitud_id=clave)
        self.assertNotEqual(uno.folio_id, otro.folio_id)
        self.assertEqual(SolicitudOperador.objects.filter(solicitud_id=clave).count(), 2)

    def test_fallo_de_cada_escritura_revierte_reserva_evento_y_comprobante(self):
        self.registrar()
        for tabla in ("folios_folio", "folios_eventofolio", "folios_solicitudoperador"):
            antes = self.snapshot()
            def fallar(execute, sql, params, many, context):
                if (sql.lstrip().upper().startswith(("UPDATE", "INSERT")) and f'"{tabla}"' in sql):
                    raise RuntimeError("Fallo de persistencia simulado")
                return execute(sql, params, many, context)
            with connection.execute_wrapper(fallar):
                with self.assertRaises(RuntimeError):
                    self.llamar()
            self.assertEqual(self.snapshot(), antes)

    def test_rollback_exterior_revierte_tambien_comprobante(self):
        self.registrar()
        antes = self.snapshot()
        with transaction.atomic():
            self.llamar()
            transaction.set_rollback(True)
        self.assertEqual(self.snapshot(), antes)

    def test_unicidad_global_y_estado_en_atencion_no_habilitado(self):
        self.registrar()
        self.llamar()
        folio = self.registrar(self.segunda)
        def segundo():
            with connection.cursor() as cursor:
                cursor.execute("UPDATE folios_folio SET estado = 'LLAMADO', operador_responsable_id = %s WHERE id = %s", [self.operador.pk, folio.pk])
        self.assert_rechazo_postgresql(segundo, "23505", "folios_folio_actual_unico")
        def estado_futuro():
            with connection.cursor() as cursor:
                cursor.execute("UPDATE folios_folio SET estado = 'EN_ATENCION', operador_responsable_id = %s WHERE id = %s", [self.otro.pk, folio.pk])
        self.assert_rechazo_postgresql(estado_futuro, "23514", "folios_folio_estado_responsable")
        self.assertNotIn("EN_ATENCION", Folio.Estado.values)

    def test_check_evento_llamado_rechaza_null_y_actor_distinto(self):
        self.registrar()
        resultado = self.llamar()
        evento = EventoFolio.objects.get(pk=resultado.evento_id)
        for campo, valor in (("estado_anterior", None), ("estado_anterior", ""), ("estado_nuevo", "EN_ESPERA"),
                             ("operador_responsable_id", None), ("asignacion_autorizante_id", None),
                             ("actor_id", self.otro.pk), ("datos_iniciales", '{}')):
            def alterar():
                with connection.cursor() as cursor:
                    cursor.execute(f'UPDATE folios_eventofolio SET "{campo}" = %s WHERE id = %s', [valor, evento.pk])
            self.assert_rechazo_postgresql(alterar, "23514", "folios_evento_campos_coherentes")

    def test_check_comprobante_llamar_exige_referencias_coherentes(self):
        self.registrar()
        resultado = self.llamar()
        solicitud = SolicitudOperador.objects.get(solicitud_id=resultado.solicitud_id)
        pausa = self.pausar()
        for campo, valor in (("folio_resultado_id", None), ("evento_folio_resultado_id", None),
                             ("pausa_resultado_id", pausa.pausa_id), ("pausa_objetivo_id", pausa.pausa_id),
                             ("evento_resultado_id", pausa.evento_id), ("motivo_solicitado", "motivo"),
                             ("resultado", "SIN_PENDIENTES")):
            def alterar():
                with connection.cursor() as cursor:
                    cursor.execute(f'UPDATE folios_solicitudoperador SET "{campo}" = %s WHERE id = %s', [valor, solicitud.pk])
            self.assert_rechazo_postgresql(alterar, "23514", "folios_solicitud_campos_coherentes")

    def test_resultados_sin_transicion_rechazan_referencias_de_llamado(self):
        resultado = self.llamar()
        folio = self.registrar()
        llamado = self.llamar()
        solicitud = SolicitudOperador.objects.get(solicitud_id=resultado.solicitud_id)
        for campo, valor in (("folio_resultado_id", folio.pk), ("evento_folio_resultado_id", llamado.evento_id)):
            def alterar():
                with connection.cursor() as cursor:
                    cursor.execute(f'UPDATE folios_solicitudoperador SET "{campo}" = %s WHERE id = %s', [valor, solicitud.pk])
            self.assert_rechazo_postgresql(alterar, "23514", "folios_solicitud_campos_coherentes")

    def test_nuevas_claves_foraneas_rechazan_referencias_inexistentes(self):
        self.registrar()
        resultado = self.llamar()
        solicitud = SolicitudOperador.objects.get(solicitud_id=resultado.solicitud_id)
        for tabla, pk, campo, valor in (
            ("folios_eventofolio", resultado.evento_id, "asignacion_autorizante_id", 9999999),
            ("folios_solicitudoperador", solicitud.pk, "folio_resultado_id", uuid4()),
            ("folios_solicitudoperador", solicitud.pk, "evento_folio_resultado_id", 9999999),
        ):
            def alterar():
                with connection.cursor() as cursor:
                    cursor.execute(f'UPDATE "{tabla}" SET "{campo}" = %s WHERE id = %s', [valor, pk])
                    cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
            self.assert_rechazo_postgresql(alterar, "23503")

    def test_nuevas_referencias_protect_y_barreras_publicas(self):
        folio = self.registrar()
        resultado = self.llamar()
        evento = EventoFolio.objects.get(pk=resultado.evento_id)
        solicitud = SolicitudOperador.objects.get(solicitud_id=resultado.solicitud_id)
        asignacion = AsignacionOperadorOficina.objects.get(pk=evento.asignacion_autorizante_id)
        for obj in (folio, evento, solicitud, asignacion):
            with self.assertRaises(NotSupportedError):
                obj.save()
        for obj in (folio, evento, asignacion, self.operador):
            with self.assertRaises(ProtectedError):
                models.Model.delete(obj)
        relaciones = (self.operador.eventos_llamado_responsable, asignacion.eventos_llamado,
                      folio.solicitudes_llamado, evento.solicitudes_llamado)
        for relacion in relaciones:
            for manager in (relacion, relacion(manager="objects")(manager="objects")):
                for metodo in ("add", "set", "remove", "clear"):
                    args = ([solicitud],) if metodo == "set" else () if metodo == "clear" else (solicitud,)
                    with self.assertRaises(NotSupportedError):
                        getattr(manager, metodo)(*args)
                    with self.assertRaises(NotSupportedError):
                        async_to_sync(ejecutar_async)(getattr(manager, "a" + metodo), *args)

    def test_orden_de_bloqueos_y_update_limitado(self):
        self.registrar()
        with CaptureQueriesContext(connection) as consultas:
            self.llamar()
        locks = [fila["sql"] for fila in consultas if "FOR UPDATE" in fila["sql"]]
        tablas = ["usuarios_usuario", "oficinas_oficina", "oficinas_oficina",
                  "oficinas_asignacionoperadoroficina", "oficinas_asignacionoperadoroficina", "folios_folio"]
        self.assertEqual(len(locks), len(tablas))
        for sql, tabla in zip(locks, tablas):
            self.assertIn(f'"{tabla}"', sql)
            self.assertNotIn("SKIP LOCKED", sql)
        self.assertIn('FOR UPDATE OF "folios_folio"', locks[-1])
        updates = [fila["sql"] for fila in consultas if fila["sql"].startswith("UPDATE")]
        self.assertEqual(len(updates), 1)
        self.assertIn('"estado"', updates[0])
        self.assertIn('"operador_responsable_id"', updates[0])
        self.assertNotIn('"llegada_original"', updates[0])
