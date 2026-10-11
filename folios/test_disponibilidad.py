"""Pausas: PostgreSQL exclusivo de migraciones; sin simular estados futuros."""

from dataclasses import FrozenInstanceError, asdict
from datetime import timedelta
from itertools import product
from unittest.mock import patch
from uuid import uuid4

from asgiref.sync import async_to_sync
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection, IntegrityError, models, NotSupportedError, transaction
from django.db.models.deletion import ProtectedError
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from oficinas.models import Oficina
from oficinas.services import crear_asignacion
from oficinas.testing import CatalogosPostgreSQLTestCase
from tramites.models import Tramite
from usuarios.models import Usuario

from .models import EventoDisponibilidad as Evento, EventoFolio, Folio, PausaOperador as Pausa
from .models import SolicitudOperador as Solicitud
from .services import registrar_folio
from .services_disponibilidad import (
    Disponibilidad, DisponibilidadPropia, consultar_disponibilidad, consultar_pausas,
    pausar_operador, reanudar_operador,
)


async def ejecutar_async(method, *args, **kwargs):
    return await method(*args, **kwargs)


class DisponibilidadFixturesMixin:
    @classmethod
    def setUpClass(cls):
        # Más estricto que el auxiliar compartido: solo la configuración autorizada.
        from django.conf import settings
        if (
            settings.SETTINGS_MODULE != "config.settings_test_migrations"
            or connection.settings_dict["NAME"] != "test_atencion_catalogos_migraciones"
        ):
            raise RuntimeError("Esta entrega requiere config.settings_test_migrations.")
        super().setUpClass()

    def preparar(self):
        self.operador = Usuario.objects.create_user(username="operador", rol="OPERADOR")
        self.otro = Usuario.objects.create_user(username="otro", rol="OPERADOR")
        self.recepcion = Usuario.objects.create_user(username="recepcion", rol="RECEPCION")
        self.admin = Usuario.objects.create_user(username="admin", rol="ADMINISTRADOR")

    def pausar(self, **kwargs):
        options = dict(actor=self.operador, motivo="  Descanso  ", solicitud_id=uuid4())
        options.update(kwargs)
        return pausar_operador(**options)

    def reanudar(self, pausa_id, **kwargs):
        options = dict(actor=self.operador, pausa_id=pausa_id, solicitud_id=uuid4())
        options.update(kwargs)
        return reanudar_operador(**options)

    def counts(self):
        return (Pausa.objects.count(), Evento.objects.count(), Solicitud.objects.count())

    def escribir_sql(self, table, field, value, pk):
        with connection.cursor() as cursor:
            cursor.execute(f'UPDATE "{table}" SET "{field}" = %s WHERE id = %s', [value, pk])
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")


class DisponibilidadTests(DisponibilidadFixturesMixin, CatalogosPostgreSQLTestCase):
    def setUp(self):
        self.preparar()

    def test_pausa_reanudacion_y_eventos_conservan_valores(self):
        inicio = timezone.now()
        with patch("folios.services_disponibilidad.timezone.now", return_value=inicio):
            result = self.pausar()
        pausa = Pausa.objects.get(pk=result.pausa_id)
        evento = Evento.objects.get(pk=result.evento_id)
        solicitud = Solicitud.objects.get(solicitud_id=result.solicitud_id)
        self.assertEqual((result.resultado, result.repetida), ("PAUSADA", False))
        self.assertEqual((pausa.operador_id, pausa.motivo, pausa.inicio, pausa.fin),
                         (self.operador.pk, "  Descanso  ", inicio, None))
        self.assertEqual((pausa.folio_contexto_id, pausa.oficina_contexto_id), (None, None))
        self.assertEqual((evento.pausa_id, evento.actor_id, evento.operacion, evento.fecha),
                         (pausa.pk, self.operador.pk, "PAUSA", inicio))
        self.assertEqual((solicitud.motivo_solicitado, solicitud.pausa_objetivo_id), (pausa.motivo, None))
        originales = list(Evento.objects.values()), list(Solicitud.objects.values())
        fin = inicio + timedelta(minutes=3)
        with patch("folios.services_disponibilidad.timezone.now", return_value=fin):
            closed = self.reanudar(pausa.pk)
        pausa.refresh_from_db()
        self.assertEqual((pausa.motivo, pausa.inicio, pausa.fin), ("  Descanso  ", inicio, fin))
        evento_fin = Evento.objects.get(pk=closed.evento_id)
        self.assertEqual((evento_fin.fecha, evento_fin.operacion), (fin, "REANUDACION"))
        self.assertEqual(list(Evento.objects.filter(pk=evento.pk).values()), originales[0])
        self.assertEqual(list(Solicitud.objects.filter(pk=solicitud.pk).values()), originales[1])
        self.assertEqual(self.counts(), (1, 2, 2))
        with self.assertRaises(FrozenInstanceError):
            result.pausa_id = 100

    def test_pausa_abierta_no_edita_motivo_y_resultados_sin_evento(self):
        original = self.pausar()
        before = list(Pausa.objects.values()), list(Evento.objects.values())
        result = self.pausar(motivo="Otro motivo válido")
        self.assertEqual((result.resultado, result.pausa_id, result.evento_id),
                         ("YA_EN_PAUSA", original.pausa_id, None))
        self.assertEqual((list(Pausa.objects.values()), list(Evento.objects.values())), before)
        self.assertEqual(Solicitud.objects.get(solicitud_id=result.solicitud_id).motivo_solicitado,
                         "Otro motivo válido")
        self.assertEqual(self.counts(), (1, 1, 2))

    def test_pausa_antigua_cerrada_no_cierra_la_posterior(self):
        primera = self.pausar()
        cerrada = self.reanudar(primera.pausa_id)
        segunda = self.pausar(motivo="Nueva pausa")
        before = list(Pausa.objects.values()), list(Evento.objects.values())
        result = self.reanudar(primera.pausa_id)
        self.assertEqual((result.resultado, result.evento_id), ("YA_REANUDADA", None))
        self.assertEqual((list(Pausa.objects.values()), list(Evento.objects.values())), before)
        replay = self.reanudar(primera.pausa_id, solicitud_id=cerrada.solicitud_id)
        self.assertTrue(replay.repetida)
        self.assertEqual(consultar_disponibilidad(actor=self.operador, operador_id=self.operador.pk).pausa_abierta_id,
                         segunda.pausa_id)

    def test_repeticiones_historicas_no_escriben_ni_alteran_disponibilidad(self):
        first = self.pausar()
        unchanged = self.pausar(motivo="Duplicada")
        closed = self.reanudar(first.pausa_id)
        no_close = self.reanudar(first.pausa_id)
        for result, call in (
            (first, lambda: self.pausar(solicitud_id=str(first.solicitud_id))),
            (unchanged, lambda: self.pausar(motivo="Duplicada", solicitud_id=unchanged.solicitud_id)),
            (closed, lambda: self.reanudar(first.pausa_id, solicitud_id=closed.solicitud_id)),
            (no_close, lambda: self.reanudar(first.pausa_id, solicitud_id=no_close.solicitud_id)),
        ):
            with CaptureQueriesContext(connection) as queries:
                replay = call()
            expected = asdict(result)
            expected["repetida"] = True
            self.assertEqual(asdict(replay), expected)
            self.assertFalse(any(q["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE")) for q in queries))
        current = consultar_disponibilidad(actor=self.operador, operador_id=self.operador.pk)
        self.assertEqual(current.disponibilidad, Disponibilidad.LIBRE)
        self.assertEqual(self.counts(), (1, 2, 4))

    def test_misma_clave_con_argumentos_incompatibles_y_ambito_por_operador(self):
        first = self.pausar()
        other = self.pausar(actor=self.otro, solicitud_id=first.solicitud_id)
        self.assertNotEqual(first.pausa_id, other.pausa_id)
        before = self.counts()
        for call in (
            lambda: self.pausar(motivo="Descanso", solicitud_id=first.solicitud_id),
            lambda: self.reanudar(first.pausa_id, solicitud_id=first.solicitud_id),
        ):
            with self.assertRaises(ValidationError):
                call()
        closed = self.reanudar(first.pausa_id)
        with self.assertRaises(ValidationError):
            self.reanudar(other.pausa_id, solicitud_id=closed.solicitud_id)
        self.assertEqual(self.counts(), (before[0], before[1] + 1, before[2] + 1))

    def test_motivo_obligatorio_incluso_con_pausa_abierta(self):
        for abierta in (False, True):
            if abierta:
                self.pausar()
            before = self.counts()
            for motivo in (None, 10, "", " \t\n "):
                with self.subTest(abierta=abierta, motivo=motivo), self.assertRaises(ValidationError):
                    self.pausar(motivo=motivo)
                self.assertEqual(self.counts(), before)

    def test_identificadores_invalidos_pausa_inexistente_y_ajena(self):
        for value in (None, 1, "inválido", True):
            with self.assertRaises(ValidationError):
                self.pausar(solicitud_id=value)
        for value in (None, True, 0, -1, "1", 99999):
            with self.assertRaises(ValidationError):
                self.reanudar(value)
        other = self.pausar(actor=self.otro)
        before = self.counts()
        with self.assertRaises(PermissionDenied):
            self.reanudar(other.pausa_id)
        self.assertEqual(self.counts(), before)

    def test_actor_autenticado_persistido_misma_base_y_rol_actual(self):
        first = self.pausar()
        foreign = Usuario.objects.get(pk=self.operador.pk)
        foreign._state.db = "otra"
        for actor in (None, AnonymousUser(), Usuario(pk=self.operador.pk), foreign, self.admin, self.recepcion):
            # Recepción tiene la consulta mínima, pero ninguna mutación.
            if actor is not self.recepcion:
                with self.assertRaises(PermissionDenied):
                    consultar_disponibilidad(actor=actor, operador_id=self.operador.pk)
            with self.assertRaises(PermissionDenied):
                self.pausar(actor=actor)
            with self.assertRaises(PermissionDenied):
                self.reanudar(first.pausa_id, actor=actor)
        before = self.counts()
        self.operador.is_active = False
        self.operador.save(update_fields=["is_active"])
        self.operador.is_active = True  # Instancia obsoleta.
        for call in (
            lambda: self.pausar(solicitud_id=first.solicitud_id),
            lambda: self.reanudar(first.pausa_id),
            lambda: consultar_disponibilidad(actor=self.operador, operador_id=self.operador.pk),
        ):
            with self.assertRaises(PermissionDenied):
                call()
        self.assertEqual(self.counts(), before)

    def test_rol_no_depende_de_flags_tecnicos(self):
        self.assertFalse(self.operador.is_staff or self.operador.is_superuser)
        first = self.pausar()
        self.reanudar(first.pausa_id)
        for role in ("RECEPCION", "ADMINISTRADOR"):
            actor = Usuario.objects.create_superuser(username=f"tecnico-{role}", rol=role)
            with self.assertRaises(PermissionDenied):
                self.pausar(actor=actor)
        stale = Usuario.objects.get(pk=self.recepcion.pk)
        self.recepcion.rol = "ADMINISTRADOR"
        self.recepcion.save(update_fields=["rol"])
        with self.assertRaises(PermissionDenied):
            consultar_disponibilidad(actor=stale, operador_id=self.operador.pk)
        stale.rol = "OPERADOR"
        with self.assertRaises(PermissionDenied):
            self.pausar(actor=stale)

    def test_proyecciones_y_disponibilidad_en_una_consulta_sin_escrituras(self):
        for en_pausa in (False, True):
            if en_pausa:
                self.pausar()
            expected = Disponibilidad.EN_PAUSA if en_pausa else Disponibilidad.LIBRE
            with self.assertNumQueries(1), CaptureQueriesContext(connection) as queries:
                own = consultar_disponibilidad(actor=self.operador, operador_id=self.operador.pk)
            self.assertIsInstance(own, DisponibilidadPropia)
            self.assertEqual(own.disponibilidad, expected)
            self.assertIsNone(own.folio_actual)
            self.assertEqual(set(asdict(own)), {"operador_id", "username", "disponibilidad", "pausa_abierta_id", "folio_actual"})
            self.assertTrue(all(q["sql"].lstrip().upper().startswith("SELECT") for q in queries))
            sql = queries[0]["sql"]
            self.assertIn("LLAMADO", sql)
            self.assertIn("EN_ATENCION", sql)
            self.assertNotIn("oficinas_asignacion", sql)
            self.assertNotIn('"oficinas_oficina"', sql)
            with self.assertNumQueries(1):
                reception = consultar_disponibilidad(actor=self.recepcion, operador_id=self.operador.pk)
            self.assertEqual(set(asdict(reception)), {"operador_id", "username", "disponibilidad"})
            self.assertEqual(reception.disponibilidad, expected)
        with self.assertRaises(PermissionDenied):
            consultar_disponibilidad(actor=self.operador, operador_id=self.otro.pk)
        with self.assertRaises(PermissionDenied):
            consultar_disponibilidad(actor=self.admin, operador_id=self.operador.pk)
        for pk in (99999, self.recepcion.pk):
            with self.assertRaises(ValidationError):
                consultar_disponibilidad(actor=self.recepcion, operador_id=pk)

    def test_cuenta_inactiva_se_consulta_sin_inventar_disponibilidad(self):
        self.pausar()
        self.operador.is_active = False
        self.operador.save(update_fields=["is_active"])
        result = consultar_disponibilidad(actor=self.recepcion, operador_id=self.operador.pk)
        self.assertEqual(result.disponibilidad, Disponibilidad.EN_PAUSA)
        self.assertEqual(len(consultar_pausas(actor=self.admin, operador_id=self.operador.pk)), 1)

    def test_administrador_historial_filtros_duracion_y_sin_escrituras(self):
        inicio = timezone.now()
        with patch("folios.services_disponibilidad.timezone.now", return_value=inicio):
            first = self.pausar()
        fin = inicio + timedelta(minutes=2)
        with patch("folios.services_disponibilidad.timezone.now", return_value=fin):
            self.reanudar(first.pausa_id)
            self.pausar(motivo="Segunda")
        with patch("folios.services_disponibilidad.timezone.now", return_value=fin + timedelta(minutes=1)):
            with CaptureQueriesContext(connection) as queries:
                rows = consultar_pausas(actor=self.admin, operador_id=self.operador.pk)
        self.assertTrue(all(q["sql"].lstrip().upper().startswith("SELECT") for q in queries))
        self.assertEqual(len(rows), 2)
        self.assertEqual((rows[0].motivo, rows[0].inicio, rows[0].fin, rows[0].duracion),
                         ("  Descanso  ", inicio, fin, timedelta(minutes=2)))
        self.assertEqual((rows[0].folio_id, rows[0].oficina_id), (None, None))
        self.assertEqual([e.operacion for e in rows[0].eventos], ["PAUSA", "REANUDACION"])
        self.assertEqual(rows[1].duracion, timedelta(minutes=1))
        filtered = consultar_pausas(
            actor=self.admin, operador_id=self.operador.pk, accion="REANUDACION",
            fecha_desde=fin, fecha_hasta=fin,
        )
        self.assertEqual(len(filtered), 1)
        self.assertEqual([e.operacion for e in filtered[0].eventos], ["REANUDACION"])
        self.assertEqual(consultar_pausas(actor=self.admin, operador_id=self.operador.pk, oficina_id=99999), ())
        for actor in (self.operador, self.recepcion):
            with self.assertRaises(PermissionDenied):
                consultar_pausas(actor=actor, operador_id=self.operador.pk)
        self.admin.is_active = False
        self.admin.save(update_fields=["is_active"])
        self.admin.is_active = True
        with self.assertRaises(PermissionDenied):
            consultar_pausas(actor=self.admin, operador_id=self.operador.pk)

    def test_historial_argumentos_invalidos_y_autorizacion_revalidada(self):
        self.pausar()
        for options in (
            {"accion": "OTRA"}, {"oficina_id": True}, {"fecha_desde": "ayer"},
            {"fecha_desde": timezone.now().replace(tzinfo=None)},
            {"fecha_desde": timezone.now(), "fecha_hasta": timezone.now() - timedelta(days=1)},
        ):
            with self.assertRaises(ValidationError):
                consultar_pausas(actor=self.admin, operador_id=self.operador.pk, **options)
        changed = False
        def deactivate_after_authorization(execute, sql, params, many, context):
            nonlocal changed
            result = execute(sql, params, many, context)
            if not changed and sql.lstrip().startswith("SELECT") and '"folios_pausaoperador"' not in sql:
                changed = True
                Usuario.objects.filter(pk=self.admin.pk).update(is_active=False)
            return result
        with connection.execute_wrapper(deactivate_after_authorization), self.assertRaises(PermissionDenied):
            consultar_pausas(actor=self.admin, operador_id=self.operador.pk)
        self.assertTrue(changed)

    def test_folios_eventos_y_bloqueos_provisionales_conservados(self):
        office = Oficina.objects.create(nombre="Norte")
        tramite = Tramite.objects.create(nombre="Solicitud", oficina=office)
        crear_asignacion(actor=self.admin, operador_id=self.operador.pk, oficina_id=office.pk)
        registrar_folio(actor=self.recepcion, nombre_completo="Ciudadano", oficina_id=office.pk, tramite_id=tramite.pk)
        before = list(Folio.objects.values()), list(EventoFolio.objects.values())
        office.activo = False
        office.save(update_fields=["activo"])
        pause = self.pausar()
        self.reanudar(pause.pausa_id)
        self.assertEqual((list(Folio.objects.values()), list(EventoFolio.objects.values())), before)
        self.assertIsNone(Pausa.objects.get(pk=pause.pausa_id).oficina_contexto_id)
        self.operador.rol = "ADMINISTRADOR"
        with self.assertRaises(ValidationError):
            self.operador.save(update_fields=["rol"])
        with self.assertRaises(NotSupportedError):
            self.operador.asignaciones_oficinas.update(activo=False)

    def test_restricciones_reales_pausa_motivo_tiempos_contexto_y_not_null(self):
        result = self.pausar()
        table = Pausa._meta.db_table
        for field, value, state, constraint in (
            ("motivo", " \t\n ", "23514", "folios_pausa_motivo_contenido"),
            ("motivo", None, "23502", None), ("inicio", None, "23502", None),
            ("operador_id", None, "23502", None), ("operador_id", 99999, "23503", None),
            ("fin", timezone.now() - timedelta(days=1), "23514", "folios_pausa_tiempos_coherentes"),
            ("folio_contexto_id", uuid4(), "23514", "folios_pausa_contexto_coherente"),
            ("oficina_contexto_id", 99999, "23514", "folios_pausa_contexto_coherente"),
        ):
            with self.subTest(field=field, value=value):
                self.assert_rechazo_postgresql(
                    lambda: self.escribir_sql(table, field, value, result.pausa_id), state, constraint,
                )
        # Ambos valores presentes satisfacen el CHECK; referencias inexistentes
        # siguen rechazadas por sus FKs, sin preparar un folio de un estado futuro.
        def invalid_context():
            with connection.cursor() as cursor:
                cursor.execute(
                    f'UPDATE "{table}" SET folio_contexto_id = %s, oficina_contexto_id = %s WHERE id = %s',
                    [uuid4(), 99999, result.pausa_id],
                )
                cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
        self.assert_rechazo_postgresql(invalid_context, "23503")

    def test_una_pausa_abierta_por_operador_y_varias_historicas(self):
        first = self.pausar()
        duplicate = Pausa(operador=self.operador, motivo="Otra", inicio=timezone.now())
        self.assert_rechazo_postgresql(
            lambda: models.Model.save(duplicate, force_insert=True), "23505", "folios_pausa_abierta_unica",
        )
        self.pausar(actor=self.otro)
        self.reanudar(first.pausa_id)
        self.pausar()
        self.assertEqual(Pausa.objects.filter(operador=self.operador).count(), 2)

    def test_evento_operacion_unicidad_referencias_y_not_null(self):
        result = self.pausar()
        event = Evento.objects.get(pk=result.evento_id)
        duplicate = Evento(pausa_id=event.pausa_id, actor=self.operador, fecha=event.fecha, operacion="PAUSA")
        self.assert_rechazo_postgresql(
            lambda: models.Model.save(duplicate, force_insert=True), "23505", "folios_disponibilidad_evento_unico",
        )
        for field, value, state in (
            ("operacion", "OTRA", "23514"), ("operacion", None, "23502"),
            ("fecha", None, "23502"), ("actor_id", None, "23502"),
            ("pausa_id", None, "23502"), ("actor_id", 99999, "23503"), ("pausa_id", 99999, "23503"),
        ):
            with self.subTest(field=field):
                self.assert_rechazo_postgresql(
                    lambda: self.escribir_sql(Evento._meta.db_table, field, value, event.pk), state,
                )

    def test_check_solicitud_combinaciones_de_null_y_resultados(self):
        first = self.pausar()
        otra = self.pausar(actor=self.otro)
        for operacion, motivo, objetivo, resultado, evento in product(
            ("PAUSAR", "REANUDAR", "OTRA"), (None, "", "Válido"),
            (None, first.pausa_id, otra.pausa_id), Solicitud.Resultado.values, (None, first.evento_id),
        ):
            valid_args = (
                operacion == "PAUSAR" and motivo == "Válido" and objetivo is None
                and resultado in ("PAUSADA", "YA_EN_PAUSA")
            ) or (
                operacion == "REANUDAR" and motivo is None and objetivo == first.pausa_id
                and resultado in ("REANUDADA", "YA_REANUDADA")
            )
            valid_event = (evento is not None) == (resultado in ("PAUSADA", "REANUDADA"))
            if valid_args and valid_event:
                continue
            candidate = Solicitud(
                operador=self.operador, solicitud_id=uuid4(), operacion=operacion, motivo_solicitado=motivo,
                pausa_objetivo_id=objetivo, resultado=resultado, pausa_resultado_id=first.pausa_id,
                evento_resultado_id=evento, confirmada_en=timezone.now(),
            )
            with self.subTest(args=(operacion, motivo, objetivo, resultado, evento)):
                self.assert_rechazo_postgresql(
                    lambda: models.Model.save(candidate, force_insert=True), "23514",
                    "folios_solicitud_campos_coherentes",
                )

    def test_solicitud_unicidad_not_null_y_referencias(self):
        first = self.pausar()
        original = Solicitud.objects.get(solicitud_id=first.solicitud_id)
        duplicate = Solicitud(**{f.attname: getattr(original, f.attname) for f in Solicitud._meta.fields if not f.primary_key})
        self.assert_rechazo_postgresql(
            lambda: models.Model.save(duplicate, force_insert=True), "23505", "folios_solicitud_operador_unica",
        )
        for field in ("operador_id", "solicitud_id", "operacion", "resultado", "pausa_resultado_id", "confirmada_en"):
            self.assert_rechazo_postgresql(
                lambda: self.escribir_sql(Solicitud._meta.db_table, field, None, original.pk), "23502",
            )
        for field in ("operador_id", "pausa_resultado_id", "evento_resultado_id"):
            self.assert_rechazo_postgresql(
                lambda: self.escribir_sql(Solicitud._meta.db_table, field, 99999, original.pk), "23503",
            )

    def test_fallo_real_de_cada_escritura_revierte_pausa_evento_y_comprobante(self):
        for cerrar in (False, True):
            for table, action, field, invalid in (
                (Pausa._meta.db_table, "UPDATE" if cerrar else "INSERT", "fin" if cerrar else "motivo", None if cerrar else ""),
                (Evento._meta.db_table, "INSERT", "operacion", "INVALIDA"),
                (Solicitud._meta.db_table, "INSERT", "resultado", "INVALIDO"),
            ):
                with self.subTest(cerrar=cerrar, table=table):
                    # Cada escenario usa un operador independiente para conservar los anteriores.
                    op = Usuario.objects.create_user(username=f"fallo-{cerrar}-{table}", rol="OPERADOR")
                    first = self.pausar(actor=op) if cerrar else None
                    before = list(Pausa.objects.values()), list(Evento.objects.values()), list(Solicitud.objects.values())
                    hit = False
                    def reject(execute, sql, params, many, context):
                        nonlocal hit
                        if sql.startswith(f'{action} "{table}"') or sql.startswith(f'{action} INTO "{table}"'):
                            hit = True
                            params = list(params)
                            if action == "INSERT":
                                columns = [c.strip().strip('"') for c in sql.split("(", 1)[1].split(")", 1)[0].split(",")]
                                params[columns.index(field)] = invalid
                            else:
                                # Un fin anterior a inicio viola el CHECK de la actualización real.
                                params[0] = timezone.now() - timedelta(days=1)
                            return execute(sql, params, many, context)
                        return execute(sql, params, many, context)
                    with connection.execute_wrapper(reject), self.assertRaises(IntegrityError):
                        if cerrar:
                            self.reanudar(first.pausa_id, actor=op)
                        else:
                            self.pausar(actor=op)
                    self.assertTrue(hit)
                    self.assertEqual((list(Pausa.objects.values()), list(Evento.objects.values()), list(Solicitud.objects.values())), before)

    def test_transaccion_exterior_revierte_apertura_y_cierre(self):
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                self.pausar()
                raise RuntimeError("rollback exterior")
        self.assertEqual(self.counts(), (0, 0, 0))
        first = self.pausar()
        before = list(Pausa.objects.values()), list(Evento.objects.values()), list(Solicitud.objects.values())
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                self.reanudar(first.pausa_id)
                raise RuntimeError("rollback exterior")
        self.assertEqual((list(Pausa.objects.values()), list(Evento.objects.values()), list(Solicitud.objects.values())), before)

    def test_referencias_protect_y_conservacion_al_desactivar(self):
        first = self.pausar()
        for instance in (
            self.operador, Pausa.objects.get(pk=first.pausa_id), Evento.objects.get(pk=first.evento_id),
        ):
            with self.assertRaises(ProtectedError):
                models.Model.delete(instance)
        before = list(Pausa.objects.values()), list(Evento.objects.values()), list(Solicitud.objects.values())
        self.operador.is_active = False
        self.operador.save(update_fields=["is_active"])
        self.assertEqual((list(Pausa.objects.values()), list(Evento.objects.values()), list(Solicitud.objects.values())), before)

    def test_barreras_publicas_modelos_managers_y_asincronas(self):
        first = self.pausar()
        for model, pk in ((Pausa, first.pausa_id), (Evento, first.evento_id),
                          (Solicitud, Solicitud.objects.get(solicitud_id=first.solicitud_id).pk)):
            instance = model.objects.get(pk=pk)
            for operation in (instance.save, instance.delete, lambda: instance.save(update_fields=[]),
                              lambda: async_to_sync(instance.asave)(), lambda: async_to_sync(instance.adelete)()):
                with self.assertRaises(NotSupportedError):
                    operation()
            for manager in (model.objects, model._base_manager, model._default_manager):
                for name, args, kwargs in (
                    ("create", (), {}), ("update", (), {"id": pk}), ("get_or_create", (), {"pk": pk}),
                    ("update_or_create", (), {"pk": pk}), ("bulk_create", ([],), {}),
                    ("bulk_create", ([],), {"update_conflicts": True}),
                    ("bulk_update", ([], ["id"]), {}), ("delete", (), {}),
                ):
                    for asynchronous in (False, True):
                        method = getattr(manager.all(), ("a" if asynchronous else "") + name)
                        with self.assertRaises(NotSupportedError):
                            async_to_sync(method)(*args, **kwargs) if asynchronous else method(*args, **kwargs)

    def test_todas_relaciones_inversas_y_seleccion_repetida_rechazan_mutacion(self):
        first = self.pausar()
        pausa = Pausa.objects.get(pk=first.pausa_id)
        evento = Evento.objects.get(pk=first.evento_id)
        office = Oficina.objects.create(nombre="Contexto")
        tramite = Tramite.objects.create(nombre="Solicitud", oficina=office)
        result = registrar_folio(actor=self.recepcion, nombre_completo="Ciudadano", oficina_id=office.pk, tramite_id=tramite.pk)
        folio = Folio.objects.get(pk=result.folio_id)
        # Relaciones de contexto vacías: no se prepara ningún folio Llamado ficticio.
        relations = (
            self.operador.pausas_operador, self.operador.eventos_disponibilidad,
            self.operador.solicitudes_operador, folio.pausas_contexto, office.pausas_contexto,
            pausa.eventos, pausa.solicitudes_reanudacion, pausa.solicitudes_resultado,
            evento.solicitudes_resultado,
        )
        for original in relations:
            expected = list(original.order_by("pk").values_list("pk", flat=True))
            selected = original(manager="objects")
            for manager in (original, selected, selected(manager="objects"), selected.db_manager("default")):
                self.assertEqual(list(manager.order_by("pk").values_list("pk", flat=True)), expected)
                sample = manager.model.objects.first()
                operations = [
                    ("add", ()), ("add", (sample,)), ("set", ([],)), ("set", ([sample],)),
                    ("remove", ()), ("remove", (sample,)), ("clear", ()),
                ]
                for name, args in operations:
                    for bulk in (False, True):
                        for asynchronous in (False, True):
                            with self.subTest(relation=manager.field.name, name=name, bulk=bulk, asynchronous=asynchronous):
                                with transaction.atomic(), self.assertRaises(NotSupportedError):
                                    method = getattr(manager, ("a" if asynchronous else "") + name)
                                    async_to_sync(method)(*args, bulk=bulk) if asynchronous else method(*args, bulk=bulk)
                for name, args in (("create", ()), ("get_or_create", ()), ("update_or_create", ()),
                                   ("update", ()), ("bulk_create", ([],)), ("bulk_update", ([], ["id"])), ("delete", ())):
                    for asynchronous in (False, True):
                        with self.assertRaises(NotSupportedError):
                            # Django expone adelete únicamente en el queryset.
                            target = manager.all() if asynchronous and name == "delete" else manager
                            method = getattr(target, ("a" if asynchronous else "") + name)
                            async_to_sync(ejecutar_async)(method, *args) if asynchronous else method(*args)
        self.assertEqual(self.counts(), (1, 1, 1))

    def test_orden_de_bloqueos_y_campos_de_servidor_no_admitidos(self):
        with CaptureQueriesContext(connection) as queries:
            first = self.pausar()
        locks = [q["sql"] for q in queries if "FOR UPDATE" in q["sql"]]
        self.assertIn('"usuarios_usuario"', locks[0])
        self.assertIn('"folios_pausaoperador"', locks[1])
        self.assertEqual(len(locks), 2)
        with CaptureQueriesContext(connection) as queries:
            self.reanudar(first.pausa_id)
        locks = [q["sql"] for q in queries if "FOR UPDATE" in q["sql"]]
        self.assertIn('"usuarios_usuario"', locks[0])
        self.assertIn('"folios_pausaoperador"', locks[1])
        for field in ("operador_id", "inicio", "fin", "folio_contexto", "using", "omitir_validaciones"):
            with self.assertRaises(TypeError):
                self.pausar(**{field: "entrada del cliente"})
