"""Backend preparado; no ejecutar sobre DEMO sin preservación y autorización."""

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

from oficinas.testing import CatalogosPostgreSQLTestCase
from usuarios.models import Usuario

from .models import EventoDisponibilidad, EventoFolio, Folio, PausaOperador, SolicitudOperador
from .services_disponibilidad import Disponibilidad, consultar_disponibilidad
from .services_inicio import EstadoInicio, _propiedad_y_estado, iniciar_atencion
from .services_operador import consultar_folio_actual_operador, consultar_pendientes_operador
from .test_disponibilidad import ejecutar_async
from .test_llamado import LlamadoFixturesMixin


class InicioFixturesMixin(LlamadoFixturesMixin):
    def reservar(self, **kwargs):
        folio = self.registrar(**kwargs)
        self.llamar()
        return Folio.objects.get(pk=folio.pk)

    def iniciar(self, folio, **kwargs):
        argumentos = dict(actor=self.operador, folio_id=folio.pk, solicitud_id=uuid4())
        argumentos.update(kwargs)
        return iniciar_atencion(**argumentos)

    def inicios(self):
        return EventoFolio.objects.filter(operacion="INICIO")

    def evidencia(self):
        return tuple(list(model.objects.order_by("pk").values()) for model in (
            Folio, EventoFolio, PausaOperador, EventoDisponibilidad, SolicitudOperador,
        ))


class InicioTests(InicioFixturesMixin, CatalogosPostgreSQLTestCase):
    def setUp(self):
        self.preparar()

    def test_inicio_atomico_conserva_campos_historia_y_contexto(self):
        folio = self.reservar()
        antes = Folio.objects.filter(pk=folio.pk).values().get()
        historia = list(folio.eventos.order_by("pk").values())
        instante = timezone.now()
        with patch("folios.services_inicio.timezone.now", return_value=instante):
            resultado = self.iniciar(folio)
        despues = Folio.objects.filter(pk=folio.pk).values().get()
        self.assertEqual((despues["estado"], despues["inicio_atencion"]), ("EN_ATENCION", instante))
        for campo in antes.keys() - {"estado", "inicio_atencion"}:
            self.assertEqual(antes[campo], despues[campo])
        self.assertEqual(list(folio.eventos.exclude(operacion="INICIO").order_by("pk").values()), historia)
        evento = self.inicios().get()
        solicitud = SolicitudOperador.objects.get(solicitud_id=resultado.solicitud_id)
        self.assertEqual((evento.folio_id, evento.actor_id, evento.operador_responsable_id,
                          evento.oficina_contexto_id, evento.asignacion_autorizante_id, evento.datos_iniciales),
                         (folio.pk, self.operador.pk, self.operador.pk, folio.oficina_id, None, None))
        self.assertEqual((evento.estado_anterior, evento.estado_nuevo), ("LLAMADO", "EN_ATENCION"))
        self.assertEqual((evento.fecha, solicitud.confirmada_en, resultado.confirmada_en), (instante,) * 3)
        self.assertEqual((solicitud.operacion, solicitud.folio_objetivo_id, solicitud.folio_resultado_id,
                          solicitud.evento_folio_resultado_id), ("INICIAR", folio.pk, folio.pk, evento.pk))
        self.assertEqual((solicitud.motivo_solicitado, solicitud.pausa_objetivo_id,
                          solicitud.pausa_resultado_id, solicitud.evento_resultado_id), (None,) * 4)
        self.assertEqual((resultado.resultado, resultado.evento_id, resultado.repetida),
                         (EstadoInicio.INICIADA, evento.pk, False))
        with self.assertRaises(FrozenInstanceError):
            resultado.folio_id = uuid4()

    def test_responsabilidad_sin_asignacion_activa_y_catalogos_desactivados(self):
        folio = self.reservar()
        for asignacion in self.asignaciones.values():
            self.historica_inactiva(asignacion)
        for catalogo in (self.oficina, self.tramites[self.oficina.pk]):
            catalogo.activo = False
            catalogo.save(update_fields=["activo"])
        with CaptureQueriesContext(connection) as consultas:
            resultado = self.iniciar(folio)
        self.assertEqual(resultado.resultado, EstadoInicio.INICIADA)
        self.assertFalse(any('"oficinas_asignacionoperadoroficina"' in c["sql"] for c in consultas))
        self.assertIsNone(self.inicios().get().asignacion_autorizante_id)
        self.assertIsNotNone(folio.eventos.get(operacion="LLAMADO").asignacion_autorizante_id)

    def test_pausa_requiere_otra_intencion_explicita_despues_de_reanudar(self):
        folio = self.reservar()
        pausa = self.pausar()
        clave = uuid4()
        antes = Folio.objects.filter(pk=folio.pk).values().get()
        bloqueado = self.iniciar(folio, solicitud_id=clave)
        self.assertEqual((bloqueado.resultado, bloqueado.evento_id), (EstadoInicio.EN_PAUSA, None))
        self.assertEqual(Folio.objects.filter(pk=folio.pk).values().get(), antes)
        self.reanudar(pausa.pausa_id)
        self.assertEqual(Folio.objects.filter(pk=folio.pk).values().get(), antes)
        evidencia = self.evidencia()
        repetida = self.iniciar(folio, solicitud_id=clave)
        self.assertEqual((repetida.resultado, repetida.repetida), (EstadoInicio.EN_PAUSA, True))
        self.assertEqual(self.evidencia(), evidencia)
        self.assertEqual(self.iniciar(folio).resultado, EstadoInicio.INICIADA)

    def test_misma_clave_antes_y_despues_de_pausar_no_repite_inicio(self):
        folio = self.reservar()
        resultado = self.iniciar(folio)
        self.pausar()
        antes = self.evidencia()
        repetida = self.iniciar(folio, solicitud_id=str(resultado.solicitud_id), folio_id=str(folio.pk))
        self.assertEqual({**asdict(resultado), "repetida": True}, asdict(repetida))
        self.assertEqual(self.evidencia(), antes)

    def test_clave_nueva_ya_en_atencion_precede_a_pausa_y_conserva_inicio(self):
        folio = self.reservar()
        self.iniciar(folio)
        pausa = self.pausar()
        antes = list(Folio.objects.values()), list(EventoFolio.objects.values())
        resultado = self.iniciar(folio)
        self.assertEqual((resultado.resultado, resultado.evento_id, resultado.repetida),
                         (EstadoInicio.YA_EN_ATENCION, None, False))
        self.assertEqual((list(Folio.objects.values()), list(EventoFolio.objects.values())), antes)
        self.assertIsNone(PausaOperador.objects.get(pk=pausa.pausa_id).fin)

    def test_folio_antiguo_no_se_sustituye_por_actual_y_comprobante_sigue_historico(self):
        antiguo = self.reservar()
        iniciado = self.iniciar(antiguo)
        # Fixture histórica exclusivamente aislada; no implementa una corrección pública.
        with connection.cursor() as cursor:
            cursor.execute("UPDATE folios_folio SET operador_responsable_id = %s WHERE id = %s",
                           [self.otro.pk, antiguo.pk])
        nuevo = self.reservar(oficina=self.segunda)
        antes = self.evidencia()
        repetida = self.iniciar(antiguo, solicitud_id=iniciado.solicitud_id)
        self.assertTrue(repetida.repetida)
        with self.assertRaises(PermissionDenied):
            self.iniciar(antiguo)
        self.assertEqual(self.evidencia(), antes)
        self.assertEqual(Folio.objects.get(pk=nuevo.pk).estado, "LLAMADO")

    def test_clave_incompatible_con_otro_objetivo_u_operacion_no_escribe(self):
        folio = self.reservar()
        resultado = self.iniciar(folio)
        antes = self.evidencia()
        for accion in (
            lambda: self.iniciar(folio, solicitud_id=resultado.solicitud_id, folio_id=uuid4()),
            lambda: self.llamar(solicitud_id=resultado.solicitud_id),
            lambda: self.pausar(solicitud_id=resultado.solicitud_id),
        ):
            with self.assertRaises(ValidationError):
                accion()
        pausa = self.pausar()
        with self.assertRaises(ValidationError):
            self.reanudar(pausa.pausa_id, solicitud_id=resultado.solicitud_id)
        self.reanudar(pausa.pausa_id)
        # Las únicas diferencias son las operaciones explícitas de pausa/reanudación.
        self.assertEqual(self.inicios().count(), 1)
        self.assertEqual(self.evidencia()[:2], antes[:2])

    def test_clave_de_pausa_reanudacion_o_llamado_no_se_reutiliza(self):
        folio = self.reservar()
        pausa = self.pausar()
        reanudacion = self.reanudar(pausa.pausa_id)
        claves = [pausa.solicitud_id, reanudacion.solicitud_id,
                  SolicitudOperador.objects.get(resultado="LLAMADO").solicitud_id]
        antes = self.evidencia()
        for clave in claves:
            with self.assertRaises(ValidationError):
                self.iniciar(folio, solicitud_id=clave)
        self.assertEqual(self.evidencia(), antes)

    def test_misma_clave_de_otro_operador_tiene_ambito_independiente(self):
        uno = self.reservar()
        dos = self.registrar()
        self.llamar(actor=self.otro)
        clave = uuid4()
        self.iniciar(uno, solicitud_id=clave)
        self.iniciar(dos, actor=self.otro, solicitud_id=clave)
        self.assertEqual(self.inicios().count(), 2)

    def test_identidades_invalidas_y_uuid_invalidos_no_escriben(self):
        folio = self.reservar()
        ajeno_alias = Usuario.objects.get(pk=self.operador.pk)
        ajeno_alias._state.db = "otro"
        antes = self.evidencia()
        for actor in (AnonymousUser(), Usuario(username="sin_guardar", rol="OPERADOR"), ajeno_alias):
            with self.assertRaises(PermissionDenied):
                self.iniciar(folio, actor=actor)
        for campo in ("solicitud_id", "folio_id"):
            for valor in (None, 1, True, "", "invalido"):
                with self.assertRaises(ValidationError):
                    self.iniciar(folio, **{campo: valor})
        self.assertEqual(self.evidencia(), antes)

    def test_rol_y_actividad_vigentes_antes_de_recuperar_comprobante(self):
        folio = self.reservar()
        resultado = self.iniciar(folio)
        antes = self.evidencia()
        for campo, valor in (("is_active", False), ("rol", "RECEPCION"), ("rol", "ADMINISTRADOR")):
            original = getattr(self.operador, campo)
            self.escribir_sql("usuarios_usuario", campo, valor, self.operador.pk)
            for clave in (uuid4(), resultado.solicitud_id):
                with self.assertRaises(PermissionDenied):
                    self.iniciar(folio, solicitud_id=clave)
            self.escribir_sql("usuarios_usuario", campo, original, self.operador.pk)
        self.assertEqual(self.evidencia(), antes)

    def test_flags_tecnicos_no_sustituyen_rol_ni_son_requisito(self):
        folio = self.reservar()
        for staff, superuser in product((False, True), repeat=2):
            for actor in (self.operador, self.recepcion, self.admin):
                actor.is_staff, actor.is_superuser = staff, superuser
                actor.save(update_fields=["is_staff", "is_superuser"])
                if actor.pk == self.operador.pk:
                    self.assertIn(self.iniciar(folio).resultado, {EstadoInicio.INICIADA, EstadoInicio.YA_EN_ATENCION})
                else:
                    with self.assertRaises(PermissionDenied):
                        self.iniciar(folio, actor=actor)

    def test_inexistente_ajeno_y_estado_incompatible_no_escriben(self):
        folio = self.reservar()
        antes = self.evidencia()
        with self.assertRaises(ValidationError):
            self.iniciar(folio, folio_id=uuid4())
        with self.assertRaises(PermissionDenied):
            self.iniciar(folio, actor=self.otro)
        self.assertEqual(self.evidencia(), antes)
        pendiente = self.registrar(self.segunda)
        antes = self.evidencia()
        with self.assertRaises(PermissionDenied):
            self.iniciar(pendiente)
        # Estado defensivo en memoria: el CHECK impide persistirlo con responsable.
        folio.estado = "ESTADO_NO_ADMITIDO"
        with self.assertRaises(ValidationError):
            _propiedad_y_estado(folio, self.operador)
        self.assertEqual(self.evidencia(), antes)

    def test_argumentos_no_admiten_fechas_destinos_ni_omitir_validacion(self):
        folio = self.reservar()
        antes = self.evidencia()
        for campo in ("operador_id", "oficina_id", "estado", "inicio_atencion", "using", "omitir_validaciones"):
            with self.assertRaises(TypeError):
                self.iniciar(folio, **{campo: 1})
        self.assertEqual(self.evidencia(), antes)

    def test_rechaza_contexto_modificado_despues_de_bloquear_oficina(self):
        folio = self.reservar()
        original = folio.oficina_id
        def cambiar(execute, sql, params, many, context):
            resultado = execute(sql, params, many, context)
            if "FOR UPDATE" in sql and '"oficinas_oficina"' in sql:
                with connection.cursor() as cursor:
                    cursor.execute("UPDATE folios_folio SET oficina_id = %s WHERE id = %s",
                                   [self.segunda.pk, folio.pk])
            return resultado
        with connection.execute_wrapper(cambiar), self.assertRaises(ValidationError):
            self.iniciar(folio)
        self.assertEqual(Folio.objects.get(pk=folio.pk).oficina_id, original)

    def test_tiempo_anterior_a_llegada_o_evento_no_se_ajusta(self):
        folio = self.reservar(llegada=timezone.now() - timedelta(hours=1))
        llamado = folio.eventos.get(operacion="LLAMADO")
        antes = self.evidencia()
        for instante in (folio.llegada_original - timedelta(seconds=1), llamado.fecha - timedelta(seconds=1)):
            with patch("folios.services_inicio.timezone.now", return_value=instante), self.assertRaises(ValidationError):
                self.iniciar(folio)
        self.assertEqual(self.evidencia(), antes)

    def test_cada_fallo_de_escritura_y_rollback_exterior_revierten_conjunto(self):
        folio = self.reservar()
        antes = self.evidencia()
        for tabla in ("folios_folio", "folios_eventofolio", "folios_solicitudoperador"):
            def fallar(execute, sql, params, many, context):
                if sql.lstrip().upper().startswith(("UPDATE", "INSERT")) and f'"{tabla}"' in sql:
                    raise RuntimeError("Fallo de persistencia simulado")
                return execute(sql, params, many, context)
            with connection.execute_wrapper(fallar), self.assertRaises(RuntimeError):
                self.iniciar(folio)
            self.assertEqual(self.evidencia(), antes)
        with transaction.atomic():
            self.iniciar(folio)
            transaction.set_rollback(True)
        self.assertEqual(self.evidencia(), antes)

    def test_orden_de_bloqueos_y_update_limitado(self):
        folio = self.reservar()
        with CaptureQueriesContext(connection) as consultas:
            self.iniciar(folio)
        locks = [fila["sql"] for fila in consultas if "FOR UPDATE" in fila["sql"]]
        self.assertEqual(len(locks), 3)
        for sql, tabla in zip(locks, ("usuarios_usuario", "oficinas_oficina", "folios_folio")):
            self.assertIn(f'"{tabla}"', sql)
            self.assertNotIn("SKIP LOCKED", sql)
        self.assertIn('FOR UPDATE OF "folios_folio"', locks[-1])
        updates = [fila["sql"] for fila in consultas if fila["sql"].startswith("UPDATE")]
        self.assertEqual(len(updates), 1)
        self.assertIn('"inicio_atencion"', updates[0])
        self.assertNotIn('"operador_responsable_id"', updates[0])
        self.assertNotIn('"llegada_original"', updates[0])

    def test_lecturas_y_disponibilidad_no_liberan_folio_en_atencion(self):
        folio = self.reservar()
        self.iniciar(folio)
        pendiente = self.registrar(self.segunda)
        antes = self.evidencia()
        actual = consultar_folio_actual_operador(actor=self.operador)
        self.assertEqual((actual.folio_id, actual.estado), (folio.pk, "EN_ATENCION"))
        self.assertEqual([f.folio_id for f in consultar_pendientes_operador(actor=self.operador).pendientes], [pendiente.pk])
        self.assertEqual(self.evidencia(), antes)
        self.assertEqual(self.llamar().resultado, "OCUPADO")
        pausa = self.pausar()
        self.assertEqual(PausaOperador.objects.get(pk=pausa.pausa_id).folio_contexto_id, folio.pk)
        self.assertEqual(self.llamar().resultado, "EN_PAUSA")
        self.reanudar(pausa.pausa_id)
        self.assertEqual(consultar_disponibilidad(actor=self.operador, operador_id=self.operador.pk).disponibilidad,
                         Disponibilidad.OCUPADO)

    def test_reintentos_previos_de_todos_los_resultados_conservan_comprobantes(self):
        from oficinas.services import reactivar_asignacion
        for asignacion in self.asignaciones.values():
            self.historica_inactiva(asignacion)
        sin_asignaciones = self.llamar()
        for oficina in (self.oficina, self.segunda):
            reactivar_asignacion(actor=self.admin, operador_id=self.operador.pk, oficina_id=oficina.pk)
        sin_pendientes = self.llamar()
        folio = self.reservar()
        ocupado = self.llamar()
        pausa = self.pausar()
        ya_pausa = self.pausar()
        en_pausa = self.llamar()
        reanudada = self.reanudar(pausa.pausa_id)
        ya_reanudada = self.reanudar(pausa.pausa_id)
        llamado = SolicitudOperador.objects.get(resultado="LLAMADO")
        self.iniciar(folio)
        antes = self.evidencia()
        acciones = [
            (r, lambda r=r: self.llamar(solicitud_id=r.solicitud_id))
            for r in (sin_asignaciones, sin_pendientes, ocupado, en_pausa, llamado)
        ]
        acciones += [(r, lambda r=r: self.pausar(solicitud_id=r.solicitud_id)) for r in (pausa, ya_pausa)]
        acciones += [(r, lambda r=r: self.reanudar(pausa.pausa_id, solicitud_id=r.solicitud_id))
                     for r in (reanudada, ya_reanudada)]
        for original, accion in acciones:
            repetida = accion()
            self.assertTrue(repetida.repetida)
            self.assertEqual((repetida.resultado, repetida.confirmada_en),
                             (original.resultado, original.confirmada_en))
        self.assertEqual(self.evidencia(), antes)


class InicioRestriccionesTests(InicioFixturesMixin, CatalogosPostgreSQLTestCase):
    def setUp(self):
        self.preparar()
        self.folio = self.reservar()
        self.inicio = self.iniciar(self.folio)
        self.evento = self.inicios().get()
        self.solicitud = SolicitudOperador.objects.get(solicitud_id=self.inicio.solicitud_id)

    def rechazar_cambio(self, tabla, pk, campo, valor, constraint, sqlstate="23514"):
        self.assert_rechazo_postgresql(
            lambda: self.escribir_sql(tabla, campo, valor, pk), sqlstate, constraint,
        )

    def test_estado_fecha_responsable_y_llegada_coherentes(self):
        for campo, valor in (("inicio_atencion", None), ("operador_responsable_id", None),
                             ("estado", "LLAMADO"), ("estado", "EN_ESPERA"), ("estado", "")):
            self.rechazar_cambio("folios_folio", self.folio.pk, campo, valor, "folios_folio_estado_responsable")
        self.rechazar_cambio("folios_folio", self.folio.pk, "inicio_atencion",
                             self.folio.llegada_original - timedelta(seconds=1), "folios_folio_inicio_coherente")
        pendiente = self.registrar(self.segunda)
        self.rechazar_cambio("folios_folio", pendiente.pk, "inicio_atencion", timezone.now(), "folios_folio_estado_responsable")

    def test_unicidad_global_con_en_atencion(self):
        pendiente = self.registrar(self.segunda)
        def segundo():
            with connection.cursor() as cursor:
                cursor.execute("UPDATE folios_folio SET estado='LLAMADO', operador_responsable_id=%s WHERE id=%s",
                               [self.operador.pk, pendiente.pk])
        self.assert_rechazo_postgresql(segundo, "23505", "folios_folio_actual_unico")

    def test_evento_inicio_exige_evidencia_sin_asignacion(self):
        for campo, valor in (("estado_anterior", None), ("estado_anterior", "EN_ESPERA"),
                             ("estado_nuevo", "LLAMADO"), ("operador_responsable_id", None),
                             ("actor_id", self.otro.pk), ("oficina_contexto_id", None),
                             ("asignacion_autorizante_id", self.asignaciones[self.oficina.pk]),
                             ("datos_iniciales", '{}'), ("operacion", "INVALIDA")):
            self.rechazar_cambio("folios_eventofolio", self.evento.pk, campo, valor, "folios_evento_campos_coherentes")
        for evento in self.folio.eventos.exclude(operacion="INICIO"):
            self.rechazar_cambio("folios_eventofolio", evento.pk, "oficina_contexto_id", self.oficina.pk,
                                 "folios_evento_campos_coherentes")

    def test_comprobante_inicio_null_explicitos_y_objetivo_igual(self):
        otro_folio = self.registrar(self.segunda)
        pausa = self.pausar()
        for campo, valor in (("folio_objetivo_id", None), ("folio_resultado_id", None),
                             ("folio_objetivo_id", otro_folio.pk), ("evento_folio_resultado_id", None),
                             ("motivo_solicitado", "Motivo"), ("pausa_objetivo_id", pausa.pausa_id),
                             ("pausa_resultado_id", pausa.pausa_id), ("evento_resultado_id", pausa.evento_id),
                             ("resultado", "LLAMADO"), ("resultado", "EN_PAUSA")):
            self.rechazar_cambio("folios_solicitudoperador", self.solicitud.pk, campo, valor,
                                 "folios_solicitud_campos_coherentes")
        ya = self.iniciar(self.folio)
        ya_solicitud = SolicitudOperador.objects.get(solicitud_id=ya.solicitud_id)
        self.rechazar_cambio("folios_solicitudoperador", ya_solicitud.pk, "evento_folio_resultado_id",
                             self.evento.pk, "folios_solicitud_campos_coherentes")
        for solicitud in SolicitudOperador.objects.exclude(operacion="INICIAR"):
            self.rechazar_cambio("folios_solicitudoperador", solicitud.pk, "folio_objetivo_id", self.folio.pk,
                                 "folios_solicitud_campos_coherentes")

    def test_referencias_nuevas_unicidad_y_barreras_publicas(self):
        self.rechazar_cambio("folios_eventofolio", self.evento.pk, "oficina_contexto_id", 9999999, None, "23503")
        # Ambos argumentos deben coincidir para alcanzar la FK, no fallar antes en el CHECK.
        objetivo = uuid4()
        def fk():
            with connection.cursor() as cursor:
                cursor.execute("UPDATE folios_solicitudoperador SET folio_objetivo_id=%s, folio_resultado_id=%s WHERE id=%s",
                               [objetivo, objetivo, self.solicitud.pk])
                cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
        self.assert_rechazo_postgresql(fk, "23503")
        duplicado = SolicitudOperador.objects.get(pk=self.solicitud.pk)
        duplicado.pk = None
        self.assert_rechazo_postgresql(lambda: models.Model.save(duplicado, force_insert=True),
                                       "23505", "folios_solicitud_operador_unica")
        for obj in (self.folio, self.evento, self.solicitud):
            with self.assertRaises(NotSupportedError):
                obj.save()
        for obj in (self.folio, self.evento, self.oficina):
            with self.assertRaises(ProtectedError):
                models.Model.delete(obj)
        for relacion, obj in ((self.folio.solicitudes_inicio_objetivo, self.solicitud),
                              (self.oficina.eventos_inicio, self.evento)):
            for manager in (relacion, relacion(manager="objects")(manager="objects")):
                for metodo in ("add", "set", "remove", "clear"):
                    argumentos = ([obj],) if metodo == "set" else () if metodo == "clear" else (obj,)
                    with self.assertRaises(NotSupportedError):
                        getattr(manager, metodo)(*argumentos)
                    with self.assertRaises(NotSupportedError):
                        async_to_sync(ejecutar_async)(getattr(manager, "a" + metodo), *argumentos)

    def test_comprobante_en_pausa_exige_objetivo_y_no_admite_evento(self):
        folio = self.registrar()
        self.llamar(actor=self.otro)
        self.pausar(actor=self.otro)
        resultado = self.iniciar(folio, actor=self.otro)
        self.assertEqual(resultado.resultado, EstadoInicio.EN_PAUSA)
        solicitud = SolicitudOperador.objects.get(solicitud_id=resultado.solicitud_id)
        for campo, valor in (("folio_objetivo_id", None), ("folio_resultado_id", None),
                             ("evento_folio_resultado_id", self.evento.pk), ("resultado", "INICIADA")):
            self.rechazar_cambio("folios_solicitudoperador", solicitud.pk, campo, valor,
                                 "folios_solicitud_campos_coherentes")
