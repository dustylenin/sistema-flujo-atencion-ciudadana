"""Pruebas completas del módulo de resolución de atención."""

from unittest.mock import patch
from uuid import uuid4

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from oficinas.testing import CatalogosPostgreSQLTestCase
from usuarios.models import Usuario

from .forms_operador import FormularioFinalizar
from .models import EventoFolio, Folio, SolicitudOperador
from .services_inicio import iniciar_atencion
from .services_resolucion import EstadoResolucion, finalizar_atencion
from .test_inicio import InicioFixturesMixin


class ResolucionFixturesMixin(InicioFixturesMixin):
    def preparar_en_atencion(self):
        folio = self.reservar()
        iniciar_atencion(actor=self.operador, folio_id=folio.pk, solicitud_id=uuid4())
        return Folio.objects.get(pk=folio.pk)

    def finalizar(self, folio, **kwargs):
        argumentos = dict(
            actor=self.operador,
            folio_id=folio.pk,
            solicitud_id=uuid4(),
            resultado=Folio.Estado.FINALIZADO,
            notas_resolucion="Atención ciudadana completada satisfactoriamente.",
        )
        argumentos.update(kwargs)
        return finalizar_atencion(**argumentos)

    def resoluciones(self):
        return EventoFolio.objects.filter(operacion=EventoFolio.Operacion.RESOLUCION)


class ResolucionServicioTests(ResolucionFixturesMixin, CatalogosPostgreSQLTestCase):
    def setUp(self):
        self.preparar()

    def test_finalizar_atencion_satisfactoria(self):
        folio = self.preparar_en_atencion()
        inicio_atencion_original = folio.inicio_atencion
        self.assertIsNotNone(inicio_atencion_original)
        self.assertEqual(folio.operador_responsable, self.operador)

        clave = uuid4()
        instante = timezone.now()
        notas = "El trámite fue resuelto con éxito."
        with patch("folios.services_resolucion.timezone.now", return_value=instante):
            resultado = self.finalizar(
                folio, solicitud_id=clave, resultado=Folio.Estado.FINALIZADO, notas_resolucion=notas,
            )

        self.assertFalse(resultado.repetida)
        self.assertEqual(resultado.resultado, EstadoResolucion.FINALIZADO)
        self.assertEqual(resultado.operacion, SolicitudOperador.Operacion.FINALIZAR)
        self.assertEqual(resultado.folio_id, folio.pk)
        self.assertEqual(resultado.confirmada_en, instante)

        # Verificar modelo Folio
        folio_actualizado = Folio.objects.get(pk=folio.pk)
        self.assertEqual(folio_actualizado.estado, Folio.Estado.FINALIZADO)
        self.assertIsNone(folio_actualizado.operador_responsable)
        self.assertEqual(folio_actualizado.inicio_atencion, inicio_atencion_original)

        # Verificar EventoFolio
        evento = self.resoluciones().get(pk=resultado.evento_id)
        self.assertEqual(evento.folio, folio_actualizado)
        self.assertEqual(evento.actor, self.operador)
        self.assertEqual(evento.operador_responsable, self.operador)
        self.assertEqual(evento.operacion, EventoFolio.Operacion.RESOLUCION)
        self.assertEqual(evento.estado_anterior, Folio.Estado.EN_ATENCION)
        self.assertEqual(evento.estado_nuevo, Folio.Estado.FINALIZADO)
        self.assertEqual(evento.oficina_contexto_id, folio.oficina_id)
        self.assertIsNone(evento.asignacion_autorizante)
        self.assertEqual(evento.datos_iniciales, {"notas_resolucion": notas})
        self.assertEqual(evento.fecha, instante)

        # Verificar SolicitudOperador
        solicitud = SolicitudOperador.objects.get(solicitud_id=clave)
        self.assertEqual(solicitud.operador, self.operador)
        self.assertEqual(solicitud.operacion, SolicitudOperador.Operacion.FINALIZAR)
        self.assertEqual(solicitud.resultado, EstadoResolucion.FINALIZADO)
        self.assertEqual(solicitud.folio_objetivo, folio_actualizado)
        self.assertEqual(solicitud.folio_resultado, folio_actualizado)
        self.assertEqual(solicitud.evento_folio_resultado, evento)
        self.assertEqual(solicitud.motivo_solicitado, notas)
        self.assertIsNone(solicitud.pausa_objetivo)
        self.assertIsNone(solicitud.pausa_resultado)
        self.assertIsNone(solicitud.evento_resultado)
        self.assertEqual(solicitud.confirmada_en, instante)

    def test_denegar_atencion_satisfactoria(self):
        folio = self.preparar_en_atencion()
        inicio_atencion_original = folio.inicio_atencion

        clave = uuid4()
        notas = "El ciudadano no presentó la documentación requerida."
        resultado = self.finalizar(
            folio, solicitud_id=clave, resultado=Folio.Estado.DENEGADO, notas_resolucion=notas,
        )

        self.assertFalse(resultado.repetida)
        self.assertEqual(resultado.resultado, EstadoResolucion.DENEGADO)

        folio_actualizado = Folio.objects.get(pk=folio.pk)
        self.assertEqual(folio_actualizado.estado, Folio.Estado.DENEGADO)
        self.assertIsNone(folio_actualizado.operador_responsable)
        self.assertEqual(folio_actualizado.inicio_atencion, inicio_atencion_original)

        evento = self.resoluciones().get(pk=resultado.evento_id)
        self.assertEqual(evento.estado_nuevo, Folio.Estado.DENEGADO)
        self.assertEqual(evento.datos_iniciales, {"notas_resolucion": notas})

        solicitud = SolicitudOperador.objects.get(solicitud_id=clave)
        self.assertEqual(solicitud.resultado, EstadoResolucion.DENEGADO)

    def test_idempotencia_misma_clave_mismos_argumentos(self):
        folio = self.preparar_en_atencion()
        clave = uuid4()
        notas = "Nota para idempotencia."

        res1 = self.finalizar(folio, solicitud_id=clave, resultado=Folio.Estado.FINALIZADO, notas_resolucion=notas)
        self.assertFalse(res1.repetida)

        conteo_eventos = self.resoluciones().count()
        conteo_solicitudes = SolicitudOperador.objects.count()

        # Repetición idéntica
        res2 = self.finalizar(folio, solicitud_id=clave, resultado=Folio.Estado.FINALIZADO, notas_resolucion=notas)
        self.assertTrue(res2.repetida)
        self.assertEqual(res2.solicitud_id, res1.solicitud_id)
        self.assertEqual(res2.resultado, res1.resultado)
        self.assertEqual(res2.evento_id, res1.evento_id)
        self.assertEqual(res2.confirmada_en, res1.confirmada_en)

        # No se crearon nuevos eventos ni solicitudes
        self.assertEqual(self.resoluciones().count(), conteo_eventos)
        self.assertEqual(SolicitudOperador.objects.count(), conteo_solicitudes)

    def test_idempotencia_misma_clave_argumentos_diferentes(self):
        folio = self.preparar_en_atencion()
        clave = uuid4()

        self.finalizar(folio, solicitud_id=clave, resultado=Folio.Estado.FINALIZADO, notas_resolucion="Nota original")

        # Con notas distintas
        with self.assertRaises(ValidationError) as error:
            self.finalizar(folio, solicitud_id=clave, resultado=Folio.Estado.FINALIZADO, notas_resolucion="Nota cambiada")
        self.assertIn("solicitud_id", error.exception.message_dict)

        # Con resultado distinto
        with self.assertRaises(ValidationError) as error:
            self.finalizar(folio, solicitud_id=clave, resultado=Folio.Estado.DENEGADO, notas_resolucion="Nota original")
        self.assertIn("solicitud_id", error.exception.message_dict)

    def test_folio_debe_estar_en_atencion(self):
        # Folio llamado (a cargo del operador, pero en estado LLAMADO, no EN_ATENCION)
        folio_llamado = self.reservar()
        self.assertEqual(folio_llamado.operador_responsable, self.operador)
        self.assertEqual(folio_llamado.estado, Folio.Estado.LLAMADO)
        with self.assertRaises(ValidationError) as error:
            self.finalizar(folio_llamado)
        self.assertEqual(error.exception.messages, ["El folio no está En atención."])

        # Folio en espera (sin operador responsable)
        folio_espera = self.registrar()
        self.assertIsNone(folio_espera.operador_responsable)
        with self.assertRaises(PermissionDenied):
            self.finalizar(folio_espera)

    def test_solo_operador_responsable_puede_finalizar(self):
        folio = self.preparar_en_atencion()
        with self.assertRaises(PermissionDenied):
            self.finalizar(folio, actor=self.otro)

    def test_actor_no_operador_o_inactivo(self):
        folio = self.preparar_en_atencion()

        with self.assertRaises(PermissionDenied):
            self.finalizar(folio, actor=self.recepcion)

        with self.assertRaises(PermissionDenied):
            self.finalizar(folio, actor=self.admin)

        self.operador.is_active = False
        self.operador.save()
        with self.assertRaises(PermissionDenied):
            self.finalizar(folio)

    def test_resultado_invalido(self):
        folio = self.preparar_en_atencion()
        for invalido in ("EN_ESPERA", "LLAMADO", "EN_ATENCION", "OTRO", ""):
            with self.assertRaises(ValidationError):
                self.finalizar(folio, resultado=invalido)

    def test_notas_resolucion_obligatorias_con_contenido(self):
        folio = self.preparar_en_atencion()
        for vacio in ("", "   ", "\n\t  "):
            with self.assertRaises(ValidationError):
                self.finalizar(folio, notas_resolucion=vacio)

    def test_folio_inexistente_o_invalido(self):
        self.preparar_en_atencion()
        with self.assertRaises(ValidationError):
            finalizar_atencion(
                actor=self.operador, folio_id=uuid4(), solicitud_id=uuid4(),
                resultado=Folio.Estado.FINALIZADO, notas_resolucion="Nota",
            )
        with self.assertRaises(ValidationError):
            finalizar_atencion(
                actor=self.operador, folio_id="no-es-uuid", solicitud_id=uuid4(),
                resultado=Folio.Estado.FINALIZADO, notas_resolucion="Nota",
            )


class ResolucionRestriccionesTests(ResolucionFixturesMixin, CatalogosPostgreSQLTestCase):
    def setUp(self):
        self.preparar()
        self.folio = self.preparar_en_atencion()
        self.res = self.finalizar(self.folio)
        self.evento = self.resoluciones().get(pk=self.res.evento_id)
        self.solicitud = SolicitudOperador.objects.get(solicitud_id=self.res.solicitud_id)

    def rechazar_sql(self, sql, params, constraint, sqlstate="23514"):
        def op():
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
        self.assert_rechazo_postgresql(op, sqlstate, constraint)

    def test_restriccion_folio_finalizado_sin_responsable_y_con_inicio(self):
        # Folio FINALIZADO no puede tener operador_responsable
        self.rechazar_sql(
            'UPDATE "folios_folio" SET "operador_responsable_id" = %s WHERE id = %s',
            [self.operador.pk, self.folio.pk],
            "folios_folio_estado_responsable",
        )
        # Folio FINALIZADO debe conservar inicio_atencion (no puede ser NULL)
        self.rechazar_sql(
            'UPDATE "folios_folio" SET "inicio_atencion" = NULL WHERE id = %s',
            [self.folio.pk],
            "folios_folio_estado_responsable",
        )

    def test_restriccion_folio_denegado_sin_responsable_y_con_inicio(self):
        otro = self.preparar_en_atencion()
        self.finalizar(otro, resultado=Folio.Estado.DENEGADO)
        # Folio DENEGADO no puede tener operador_responsable
        self.rechazar_sql(
            'UPDATE "folios_folio" SET "operador_responsable_id" = %s WHERE id = %s',
            [self.operador.pk, otro.pk],
            "folios_folio_estado_responsable",
        )
        # Folio DENEGADO debe conservar inicio_atencion (no puede ser NULL)
        self.rechazar_sql(
            'UPDATE "folios_folio" SET "inicio_atencion" = NULL WHERE id = %s',
            [otro.pk],
            "folios_folio_estado_responsable",
        )

    def test_restriccion_evento_resolucion_campos_coherentes(self):
        # datos_iniciales no puede ser NULL en RESOLUCION
        self.rechazar_sql(
            'UPDATE "folios_eventofolio" SET "datos_iniciales" = NULL WHERE id = %s',
            [self.evento.pk],
            "folios_evento_campos_coherentes",
        )
        # oficina_contexto no puede ser NULL en RESOLUCION
        self.rechazar_sql(
            'UPDATE "folios_eventofolio" SET "oficina_contexto_id" = NULL WHERE id = %s',
            [self.evento.pk],
            "folios_evento_campos_coherentes",
        )
        # estado_anterior debe ser EN_ATENCION
        self.rechazar_sql(
            'UPDATE "folios_eventofolio" SET "estado_anterior" = %s WHERE id = %s',
            ["LLAMADO", self.evento.pk],
            "folios_evento_campos_coherentes",
        )

    def test_restriccion_solicitud_finalizar_campos_coherentes(self):
        # motivo_solicitado no puede ser NULL en FINALIZAR
        self.rechazar_sql(
            'UPDATE "folios_solicitudoperador" SET "motivo_solicitado" = NULL WHERE id = %s',
            [self.solicitud.pk],
            "folios_solicitud_campos_coherentes",
        )
        # evento_folio_resultado no puede ser NULL en FINALIZAR
        self.rechazar_sql(
            'UPDATE "folios_solicitudoperador" SET "evento_folio_resultado_id" = NULL WHERE id = %s',
            [self.solicitud.pk],
            "folios_solicitud_campos_coherentes",
        )


class ResolucionFormularioYVistasTests(ResolucionFixturesMixin, CatalogosPostgreSQLTestCase):
    def setUp(self):
        self.preparar()
        self.client = Client()
        self.client.force_login(self.operador)
        self.actual_url = reverse("usuarios:operador_actual")
        self.finalizar_url = reverse("usuarios:operador_finalizar")

    def test_formulario_finalizar_intencion_valida(self):
        folio = self.preparar_en_atencion()
        form = FormularioFinalizar(actor=self.operador, destino="usuarios:operador_actual", folio_id=folio.pk)
        token = form.initial["token"]

        form_bound = FormularioFinalizar(
            {"token": token, "resultado": Folio.Estado.FINALIZADO, "notas_resolucion": "Trámite resuelto."},
            actor=self.operador,
        )
        self.assertTrue(form_bound.is_valid())
        self.assertEqual(form_bound.intencion.folio_id, folio.pk)
        self.assertEqual(form_bound.intencion.destino, "usuarios:operador_actual")

    def test_formulario_finalizar_rechaza_notas_vacias(self):
        folio = self.preparar_en_atencion()
        form = FormularioFinalizar(actor=self.operador, destino="usuarios:operador_actual", folio_id=folio.pk)
        token = form.initial["token"]

        form_bound = FormularioFinalizar(
            {"token": token, "resultado": Folio.Estado.FINALIZADO, "notas_resolucion": "   "},
            actor=self.operador,
        )
        self.assertFalse(form_bound.is_valid())
        self.assertIn("notas_resolucion", form_bound.errors)

    def test_pantalla_actual_pasa_form_finalizar_en_atencion(self):
        folio = self.preparar_en_atencion()
        response = self.client.get(self.actual_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("form_finalizar", response.context)
        self.assertIsInstance(response.context["form_finalizar"], FormularioFinalizar)
        self.assertContains(response, 'action="/operacion/finalizar/"')
        self.assertContains(response, "Finalizar atención")

    def test_post_finalizar_exitoso_redirige_y_muestra_mensaje(self):
        folio = self.preparar_en_atencion()
        get_resp = self.client.get(self.actual_url)
        form_finalizar = get_resp.context["form_finalizar"]

        post_data = {
            "token": form_finalizar["token"].value(),
            "resultado": Folio.Estado.FINALIZADO,
            "notas_resolucion": "Ciudadano atendido correctamente.",
        }
        response = self.client.post(self.finalizar_url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Se finalizó la atención con éxito.")

        folio_db = Folio.objects.get(pk=folio.pk)
        self.assertEqual(folio_db.estado, Folio.Estado.FINALIZADO)
        self.assertIsNone(folio_db.operador_responsable)

    def test_post_finalizar_denegado_exitoso(self):
        folio = self.preparar_en_atencion()
        get_resp = self.client.get(self.actual_url)
        form_finalizar = get_resp.context["form_finalizar"]

        post_data = {
            "token": form_finalizar["token"].value(),
            "resultado": Folio.Estado.DENEGADO,
            "notas_resolucion": "Faltaron requisitos oficiales.",
        }
        response = self.client.post(self.finalizar_url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Se registró la atención como denegada.")

        folio_db = Folio.objects.get(pk=folio.pk)
        self.assertEqual(folio_db.estado, Folio.Estado.DENEGADO)

    def test_post_finalizar_invalido_muestra_accion_html(self):
        folio = self.preparar_en_atencion()
        get_resp = self.client.get(self.actual_url)
        form_finalizar = get_resp.context["form_finalizar"]

        post_data = {
            "token": form_finalizar["token"].value(),
            "resultado": Folio.Estado.FINALIZADO,
            "notas_resolucion": "",
        }
        response = self.client.post(self.finalizar_url, post_data)
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Revisar solicitud", status_code=400)
        self.assertContains(response, "Escribe las notas de resolución.", status_code=400)

    def test_get_finalizar_metodo_no_permitido(self):
        response = self.client.get(self.finalizar_url)
        self.assertEqual(response.status_code, 405)

    def test_finalizar_requiere_rol_operador(self):
        client_recepcion = Client()
        client_recepcion.force_login(self.recepcion)
        response = client_recepcion.post(self.finalizar_url, {})
        # Requiere rol OPERADOR, redirige o 403
        self.assertNotEqual(response.status_code, 200)
