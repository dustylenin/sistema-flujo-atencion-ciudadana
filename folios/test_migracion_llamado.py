"""Conservación histórica preparada para una ejecución posterior autorizada."""

from datetime import timedelta
from uuid import uuid4

from django.db import connection, models
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone

from oficinas.testing import CatalogosPostgreSQLTransactionTestCase

from .test_disponibilidad import DisponibilidadFixturesMixin


class MigracionLlamadoTests(DisponibilidadFixturesMixin, CatalogosPostgreSQLTransactionTestCase):
    anterior = ("folios", "0002_pausaoperador_eventodisponibilidad_solicitudoperador_and_more")
    nueva = ("folios", "0003_llamado_y_reserva")

    def setUp(self):
        # El runner de esta prueba NO está autorizado en la etapa de preparación.
        # La limpieza se registra antes de retroceder para recuperar el esquema
        # del runner incluso si falla el setUp; nunca usa la base normal.
        self.addCleanup(self.restaurar_esquema)
        executor = MigrationExecutor(connection)
        executor.migrate([self.anterior])
        self.old_apps = executor.loader.project_state([self.anterior]).apps

    def restaurar_esquema(self):
        MigrationExecutor(connection).migrate([self.nueva])

    def insertar(self, model, **kwargs):
        obj = model(**kwargs)
        models.Model.save(obj, force_insert=True)
        return obj

    def test_migracion_conserva_creacion_y_comprobantes_de_pausa_reanudacion(self):
        usuario = self.old_apps.get_model("usuarios", "Usuario")
        recepcion = self.insertar(usuario, username="migracion_recepcion", password="!", rol="RECEPCION")
        operador = self.insertar(usuario, username="migracion_operador", password="!", rol="OPERADOR")
        oficina = self.insertar(self.old_apps.get_model("oficinas", "Oficina"), nombre="Migración")
        tramite = self.insertar(self.old_apps.get_model("tramites", "Tramite"), nombre="Solicitud", oficina=oficina)
        inicio = timezone.now()
        fin = inicio + timedelta(seconds=1)
        folio = self.insertar(
            self.old_apps.get_model("folios", "Folio"), nombre_completo="Prueba histórica",
            oficina=oficina, tramite=tramite, registrado_por=recepcion, llegada_original=inicio,
        )
        self.insertar(
            self.old_apps.get_model("folios", "EventoFolio"), folio=folio, actor=recepcion,
            fecha=inicio, operacion="CREACION", estado_anterior=None, estado_nuevo="EN_ESPERA",
            datos_iniciales={"nombre_completo": "Prueba histórica", "oficina_id": oficina.pk},
        )
        pausa = self.insertar(
            self.old_apps.get_model("folios", "PausaOperador"), operador=operador,
            motivo="Descanso", inicio=inicio, fin=fin,
        )
        evento_model = self.old_apps.get_model("folios", "EventoDisponibilidad")
        inicio_evento = self.insertar(evento_model, pausa=pausa, actor=operador, fecha=inicio, operacion="PAUSA")
        fin_evento = self.insertar(evento_model, pausa=pausa, actor=operador, fecha=fin, operacion="REANUDACION")
        solicitud_model = self.old_apps.get_model("folios", "SolicitudOperador")
        self.insertar(
            solicitud_model, operador=operador, solicitud_id=uuid4(), operacion="PAUSAR",
            motivo_solicitado="Descanso", pausa_resultado=pausa, evento_resultado=inicio_evento,
            resultado="PAUSADA", confirmada_en=inicio,
        )
        self.insertar(
            solicitud_model, operador=operador, solicitud_id=uuid4(), operacion="REANUDAR",
            pausa_objetivo=pausa, pausa_resultado=pausa, evento_resultado=fin_evento,
            resultado="REANUDADA", confirmada_en=fin,
        )
        nombres = ("Folio", "EventoFolio", "PausaOperador", "EventoDisponibilidad", "SolicitudOperador")
        anteriores = {nombre: list(self.old_apps.get_model("folios", nombre).objects.order_by("pk").values()) for nombre in nombres}
        executor = MigrationExecutor(connection)
        executor.migrate([self.nueva])
        nuevas_apps = executor.loader.project_state([self.nueva]).apps
        for nombre, filas in anteriores.items():
            nuevo_model = nuevas_apps.get_model("folios", nombre)
            self.assertEqual(list(nuevo_model.objects.order_by("pk").values(*filas[0].keys())), filas)
        evento = nuevas_apps.get_model("folios", "EventoFolio").objects.get()
        self.assertEqual((evento.operador_responsable_id, evento.asignacion_autorizante_id), (None, None))
        for solicitud in nuevas_apps.get_model("folios", "SolicitudOperador").objects.all():
            self.assertEqual((solicitud.folio_resultado_id, solicitud.evento_folio_resultado_id), (None, None))
