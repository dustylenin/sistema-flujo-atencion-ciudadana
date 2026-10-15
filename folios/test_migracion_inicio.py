"""Preservación de 0003 a 0004 preparada; ejecución todavía pendiente."""

from datetime import timedelta
from uuid import uuid4

from django.db import connection, models
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone

from oficinas.testing import CatalogosPostgreSQLTransactionTestCase
from usuarios.models import Usuario

from .models import EventoFolio, Folio, SolicitudOperador
from .services_disponibilidad import pausar_operador, reanudar_operador
from .services_inicio import iniciar_atencion
from .services_llamado import llamar_siguiente
from .test_disponibilidad import DisponibilidadFixturesMixin


class MigracionInicioTests(DisponibilidadFixturesMixin, CatalogosPostgreSQLTransactionTestCase):
    anterior = ("folios", "0003_llamado_y_reserva")
    nueva = ("folios", "0004_inicio_de_atencion")

    def setUp(self):
        # Registrar antes de cualquier operación: también se ejecuta si falla setUp.
        self.addCleanup(self.restaurar_esquema)
        executor = MigrationExecutor(connection)
        executor.migrate([self.anterior])
        self.old_apps = executor.loader.project_state([self.anterior]).apps

    def restaurar_esquema(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

    def insertar(self, app, modelo, **datos):
        instancia = self.old_apps.get_model(app, modelo)(**datos)
        models.Model.save(instancia, force_insert=True)
        return instancia

    def historicos(self):
        recepcion = self.insertar("usuarios", "Usuario", username="recepcion_migracion", password="!", rol="RECEPCION")
        operador = self.insertar("usuarios", "Usuario", username="operador_migracion", password="!", rol="OPERADOR")
        otro = self.insertar("usuarios", "Usuario", username="otro_migracion", password="!", rol="OPERADOR")
        oficina = self.insertar("oficinas", "Oficina", nombre="Oficina histórica")
        tramite = self.insertar("tramites", "Tramite", nombre="Trámite histórico", oficina=oficina)
        asignacion = self.insertar("oficinas", "AsignacionOperadorOficina", operador=operador, oficina=oficina)
        llegada = timezone.now() - timedelta(hours=2)
        folios = []
        for estado in ("LLAMADO", "EN_ESPERA"):
            folio = self.insertar(
                "folios", "Folio", nombre_completo="Ciudadano histórico", correo="demo@example.test",
                telefono="123", oficina=oficina, tramite=tramite, registrado_por=recepcion,
                llegada_original=llegada, estado=estado, operador_responsable=operador if estado == "LLAMADO" else None,
            )
            self.insertar(
                "folios", "EventoFolio", folio=folio, actor=recepcion, fecha=llegada,
                operacion="CREACION", estado_anterior=None, estado_nuevo="EN_ESPERA",
                datos_iniciales={"nombre_completo": "Ciudadano histórico", "oficina_id": oficina.pk,
                                "llegada_original": llegada.isoformat()},
            )
            folios.append(folio)
        llamado, _ = folios
        evento_llamado = self.insertar(
            "folios", "EventoFolio", folio=llamado, actor=operador, fecha=llegada + timedelta(minutes=1),
            operacion="LLAMADO", estado_anterior="EN_ESPERA", estado_nuevo="LLAMADO", datos_iniciales=None,
            operador_responsable=operador, asignacion_autorizante=asignacion,
        )
        pausa = self.insertar(
            "folios", "PausaOperador", operador=operador, motivo="  Descanso histórico  ",
            inicio=llegada + timedelta(minutes=2), fin=llegada + timedelta(minutes=3),
            folio_contexto=llamado, oficina_contexto=oficina,
        )
        abierta = self.insertar(
            "folios", "PausaOperador", operador=otro, motivo="Pausa abierta", inicio=llegada,
        )
        for p in (pausa, abierta):
            self.insertar("folios", "EventoDisponibilidad", pausa=p, actor=p.operador, fecha=p.inicio, operacion="PAUSA")
        evento_pausa = self.old_apps.get_model("folios", "EventoDisponibilidad").objects.get(pausa=pausa)
        evento_fin = self.insertar("folios", "EventoDisponibilidad", pausa=pausa, actor=operador,
                                   fecha=pausa.fin, operacion="REANUDACION")
        for resultado in ("PAUSADA", "YA_EN_PAUSA", "REANUDADA", "YA_REANUDADA"):
            reanuda = resultado in {"REANUDADA", "YA_REANUDADA"}
            self.insertar(
                "folios", "SolicitudOperador", operador=operador, solicitud_id=uuid4(),
                operacion="REANUDAR" if reanuda else "PAUSAR", resultado=resultado,
                motivo_solicitado=None if reanuda else pausa.motivo,
                pausa_objetivo=pausa if reanuda else None, pausa_resultado=pausa,
                evento_resultado=(evento_fin if reanuda else evento_pausa)
                if resultado in {"PAUSADA", "REANUDADA"} else None, confirmada_en=pausa.fin,
            )
        for resultado in ("EN_PAUSA", "OCUPADO", "SIN_ASIGNACIONES", "SIN_PENDIENTES", "LLAMADO"):
            self.insertar(
                "folios", "SolicitudOperador", operador=operador, solicitud_id=uuid4(), operacion="LLAMAR",
                resultado=resultado, confirmada_en=evento_llamado.fecha,
                folio_resultado=llamado if resultado == "LLAMADO" else None,
                evento_folio_resultado=evento_llamado if resultado == "LLAMADO" else None,
            )
        return operador.pk, llamado.pk

    def test_preserva_valores_referencias_y_reintentos_anteriores(self):
        operador_id, folio_id = self.historicos()
        tablas = (("usuarios", "Usuario"), ("oficinas", "Oficina"), ("tramites", "Tramite"),
                  ("oficinas", "AsignacionOperadorOficina"), ("folios", "Folio"),
                  ("folios", "EventoFolio"), ("folios", "PausaOperador"),
                  ("folios", "EventoDisponibilidad"), ("folios", "SolicitudOperador"))
        antes = {tabla: list(self.old_apps.get_model(*tabla).objects.order_by("pk").values()) for tabla in tablas}
        executor = MigrationExecutor(connection)
        executor.migrate([self.nueva])
        nuevas_apps = executor.loader.project_state([self.nueva]).apps
        for tabla, filas in antes.items():
            self.assertEqual(list(nuevas_apps.get_model(*tabla).objects.order_by("pk").values(*filas[0].keys())), filas)
        self.assertFalse(Folio.objects.exclude(inicio_atencion=None).exists())
        self.assertFalse(EventoFolio.objects.exclude(oficina_contexto=None).exists())
        self.assertFalse(SolicitudOperador.objects.exclude(folio_objetivo=None).exists())
        actor = Usuario.objects.get(pk=operador_id)
        originales = list(SolicitudOperador.objects.order_by("pk").values())
        for solicitud in SolicitudOperador.objects.order_by("pk"):
            argumentos = dict(actor=actor, solicitud_id=solicitud.solicitud_id)
            if solicitud.operacion == "LLAMAR":
                repetida = llamar_siguiente(**argumentos)
            elif solicitud.operacion == "PAUSAR":
                repetida = pausar_operador(**argumentos, motivo=solicitud.motivo_solicitado)
            else:
                repetida = reanudar_operador(**argumentos, pausa_id=solicitud.pausa_objetivo_id)
            self.assertTrue(repetida.repetida)
            self.assertEqual((repetida.resultado, repetida.confirmada_en),
                             (solicitud.resultado, solicitud.confirmada_en))
        self.assertEqual(list(SolicitudOperador.objects.order_by("pk").values()), originales)
        for tabla, filas in antes.items():
            self.assertEqual(list(nuevas_apps.get_model(*tabla).objects.order_by("pk").values(*filas[0].keys())), filas)
        resultado = iniciar_atencion(actor=actor, folio_id=folio_id, solicitud_id=uuid4())
        self.assertEqual(resultado.resultado, "INICIADA")
        self.assertEqual(Folio.objects.get(pk=folio_id).llegada_original, antes[("folios", "Folio")][0]["llegada_original"])

    def test_fallo_durante_migracion_permite_recuperar_esquema_vigente(self):
        self.historicos()
        def fallar(execute, sql, params, many, context):
            if 'ADD CONSTRAINT "folios_folio_inicio_coherente"' in sql:
                raise RuntimeError("Fallo simulado de DDL")
            return execute(sql, params, many, context)
        with connection.execute_wrapper(fallar), self.assertRaises(RuntimeError):
            MigrationExecutor(connection).migrate([self.nueva])
        # La misma limpieza registrada antes de setUp recupera las hojas actuales,
        # incluso tras un fallo. Nunca retrocede al destino histórico 0003.
        self.restaurar_esquema()
        executor = MigrationExecutor(connection)
        self.assertEqual(executor.migration_plan(executor.loader.graph.leaf_nodes()), [])
        self.assertEqual(list(Folio.objects.values_list("inicio_atencion", flat=True)), [None, None])
