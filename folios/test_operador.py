"""HTTP de Operador preparado; no ejecutar sin preservar primero DEMO."""

from itertools import product
from unittest.mock import patch
from uuid import UUID, uuid4

from django.conf import settings
from django.core import signing
from django.db import DatabaseError
from django.test import Client
from django.urls import reverse
from django.utils.html import escape

from oficinas.testing import CatalogosPostgreSQLTestCase
from .models import EventoDisponibilidad, EventoFolio, Folio, PausaOperador, SolicitudOperador
from .services import registrar_folio
from .services_disponibilidad import pausar_operador, reanudar_operador
from .services_llamado import llamar_siguiente
from .test_llamado import LlamadoFixturesMixin


class OperadorHTTPTests(LlamadoFixturesMixin, CatalogosPostgreSQLTestCase):
    def setUp(self):
        self.preparar()
        self.client.force_login(self.operador)
        self.cola = reverse("usuarios:operacion")
        self.actual = reverse("usuarios:operador_actual")
        self.rutas = {accion: reverse(f"usuarios:operador_{accion}") for accion in ("llamar", "pausar", "reanudar")}

    def datos(self, accion, *, pagina=None, client=None, **extra):
        response = (client or self.client).get(pagina or self.cola)
        self.assertEqual(response.status_code, 200)
        campo = {"llamar": "form_llamar", "pausar": "form_pausar", "reanudar": "form_reanudar"}[accion]
        form = response.context[campo]
        datos = {"token": form["token"].value()}
        if accion == "pausar":
            datos["motivo"] = "  Incidencia del área\n  "
        datos.update(extra)
        return datos

    def intencion(self, datos):
        return signing.loads(datos["token"], salt="folios.operador.formulario.v1")

    def firmar(self, datos):
        return {"token": signing.dumps(datos, salt="folios.operador.formulario.v1")}

    def estado(self):
        return tuple(list(modelo.objects.order_by("pk").values()) for modelo in (
            Folio, EventoFolio, PausaOperador, EventoDisponibilidad, SolicitudOperador,
        ))

    def registrar_nombre(self, nombre, oficina=None, **extra):
        oficina = oficina or self.oficina
        return registrar_folio(
            actor=self.recepcion, nombre_completo=nombre, oficina_id=oficina.pk,
            tramite_id=self.tramites[oficina.pk].pk, **extra,
        ).folio_id

    def test_dos_entradas_de_navegacion_y_salida_post(self):
        for pagina in (self.cola, self.actual):
            response = self.client.get(pagina)
            html = response.content.decode()
            nav = html.split('<nav aria-label="Navegación de Operador">')[1].split('</nav>')[0]
            self.assertEqual(nav.count('<a '), 2)
            self.assertIn('href="/operacion/"', nav)
            self.assertIn('href="/operacion/actual/"', nav)
            self.assertEqual(nav.count('aria-current="page"'), 1)
            self.assertContains(response, 'method="post" action="/salir/"')
            self.assertContains(response, 'href="#contenido"')
            self.assertContains(response, self.operador.username)
            for texto in ("Iniciar atención", "Guardar nota", "Finalizar", "Denegar", "Historial", "<select"):
                self.assertNotContains(response, texto)

    def test_get_solo_consulta_y_no_crea_comprobantes(self):
        self.registrar()
        antes = self.estado()
        for _ in range(2):
            self.assertEqual(self.client.get(self.cola).status_code, 200)
            self.assertEqual(self.client.get(self.actual).status_code, 200)
        self.assertEqual(self.estado(), antes)

    def test_sin_asignaciones_y_vacios_autorizados(self):
        for asignacion in self.asignaciones.values():
            self.historica_inactiva(asignacion)
        self.assertContains(self.client.get(self.cola), "No hay pendientes en tu cola")
        self.assertContains(self.client.get(self.actual), "Sin folio actual")
        datos = self.datos("llamar")
        response = self.client.post(self.rutas["llamar"], datos, follow=True)
        self.assertContains(response, "No tienes oficinas asignadas activamente")
        self.assertEqual(SolicitudOperador.objects.get().resultado, "SIN_ASIGNACIONES")

    def test_anonimo_no_accede_a_paginas_o_acciones(self):
        client = Client()
        for url in (self.cola, self.actual):
            self.assertRedirects(client.get(url), "/acceso/")
        for url in self.rutas.values():
            self.assertRedirects(client.post(url, {}), "/acceso/")
        self.assertEqual(SolicitudOperador.objects.count(), 0)

    def test_roles_ajenos_rechazados_con_cualquier_flag(self):
        for actor, flags in product((self.admin, self.recepcion), product((False, True), repeat=2)):
            actor.is_staff, actor.is_superuser = flags
            actor.save(update_fields=["is_staff", "is_superuser"])
            self.client.force_login(actor)
            for url in (self.cola, self.actual):
                self.assertEqual(self.client.get(url).status_code, 403)
            for url in self.rutas.values():
                self.assertEqual(self.client.post(url, {}).status_code, 403)
        self.assertEqual(SolicitudOperador.objects.count(), 0)

    def test_operador_admite_todas_las_combinaciones_de_flags(self):
        for staff, superuser in product((False, True), repeat=2):
            self.operador.is_staff, self.operador.is_superuser = staff, superuser
            self.operador.save(update_fields=["is_staff", "is_superuser"])
            self.assertEqual(self.client.get(self.actual).status_code, 200)
            self.assertEqual(self.client.post(self.rutas["llamar"], self.datos("llamar")).status_code, 302)
        self.assertEqual(SolicitudOperador.objects.count(), 4)

    def test_desactivar_cuenta_con_sesion_existente_bloquea_post(self):
        datos = self.datos("llamar")
        self.operador.is_active = False
        self.operador.save(update_fields=["is_active"])
        for pagina in (self.cola, self.actual):
            self.assertRedirects(self.client.get(pagina), "/acceso/")
        self.assertRedirects(self.client.post(self.rutas["llamar"], datos), "/acceso/")
        self.assertEqual(SolicitudOperador.objects.count(), 0)

    def test_rol_vigente_con_sesion_y_servicio_tras_autorizacion_de_vista(self):
        datos = self.datos("llamar")
        def cambiar_y_llamar(**kwargs):
            self.escribir_sql("usuarios_usuario", "rol", "RECEPCION", self.operador.pk)
            return llamar_siguiente(**kwargs)
        with patch("folios.views_operador.llamar_siguiente", side_effect=cambiar_y_llamar):
            self.assertEqual(self.client.post(self.rutas["llamar"], datos).status_code, 403)
        for pagina in (self.cola, self.actual):
            self.assertEqual(self.client.get(pagina).status_code, 403)
        self.assertEqual(SolicitudOperador.objects.count(), 0)

    def test_metodos_permitidos_y_never_cache(self):
        for pagina in (self.cola, self.actual):
            self.assertEqual(self.client.post(pagina, {}).status_code, 405)
            self.assertIn("no-store", self.client.get(pagina).headers["Cache-Control"])
        for ruta in self.rutas.values():
            for metodo in (self.client.get, self.client.put, self.client.delete):
                self.assertEqual(metodo(ruta).status_code, 405)
            error = self.client.post(ruta, {})
            self.assertIn("no-store", error.headers["Cache-Control"])

    def test_csrf_real_ausente_incorrecto_y_valido_en_tres_acciones(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.operador)
        for accion in ("llamar", "pausar", "reanudar"):
            datos = self.datos(accion, client=client)
            antes = self.estado()
            for csrf in (None, "incorrecto"):
                contenido = dict(datos)
                if csrf is not None:
                    contenido["csrfmiddlewaretoken"] = csrf
                self.assertEqual(client.post(self.rutas[accion], contenido).status_code, 403)
            self.assertEqual(self.estado(), antes)
            datos["csrfmiddlewaretoken"] = client.cookies[settings.CSRF_COOKIE_NAME].value
            self.assertEqual(client.post(self.rutas[accion], datos).status_code, 302)
        self.assertFalse(PausaOperador.objects.filter(fin__isnull=True).exists())

    def test_cola_paginada_y_cursor_invalido(self):
        for n in range(51):
            self.registrar(self.oficina if n % 2 else self.segunda)
        self.registrar(self.ajena)
        antes = self.estado()
        primera = self.client.get(self.cola)
        self.assertEqual(len(primera.context["pendientes"].pendientes), 50)
        self.assertContains(primera, "Siguiente página")
        cursor = primera.context["pendientes"].cursor_siguiente
        ultima = self.client.get(self.cola, {"cursor": cursor})
        self.assertEqual(len(ultima.context["pendientes"].pendientes), 1)
        self.assertNotContains(ultima, "Siguiente página")
        self.assertContains(ultima, "Volver al inicio")
        invalida = self.client.get(self.cola, {"cursor": "manipulado"})
        self.assertContains(invalida, "No se pudo abrir esa página", status_code=400)
        self.assertEqual(self.estado(), antes)

    def test_llamado_desde_otra_pagina_sigue_el_primero_global(self):
        folios = [self.registrar() for _ in range(51)]
        primera = self.client.get(self.cola)
        segunda = self.client.get(self.cola, {"cursor": primera.context["pendientes"].cursor_siguiente})
        datos = {"token": segunda.context["form_llamar"]["token"].value()}
        response = self.client.post(self.rutas["llamar"], {
            **datos, "folio_id": str(folios[-1].pk), "oficina_id": self.ajena.pk,
            "operador_id": self.otro.pk, "solicitud_id": str(uuid4()),
        })
        self.assertRedirects(response, self.actual)
        folios[0].refresh_from_db()
        self.assertEqual(folios[0].operador_responsable_id, self.operador.pk)
        self.assertEqual(SolicitudOperador.objects.get().solicitud_id, UUID(self.intencion(datos)["solicitud_id"]))

    def test_campos_visibles_y_folios_ajenos(self):
        propio = self.registrar_nombre("Ciudadano propio", self.segunda, correo="privado@example.test", telefono="dato-privado")
        self.registrar_nombre("Ciudadano ajeno", self.ajena)
        self.assertContains(self.client.get(self.cola), "Ciudadano propio")
        self.assertNotContains(self.client.get(self.cola), "Ciudadano ajeno")
        self.llamar()
        pantalla = self.client.get(self.actual, {"folio_id": str(uuid4()), "operador_id": self.otro.pk})
        self.assertContains(pantalla, "Ciudadano propio")
        self.assertContains(pantalla, "Llamado")
        for texto in ("privado@example.test", "dato-privado", str(propio), "Ciudadano ajeno"):
            self.assertNotContains(pantalla, texto)
        self.client.force_login(self.otro)
        ajena = self.client.get(self.actual, {"folio_id": str(propio)})
        self.assertContains(ajena, "Sin folio actual")
        self.assertNotContains(ajena, "Ciudadano propio")
        self.assertEqual(self.client.get(self.actual + str(propio) + "/").status_code, 404)

    def test_catalogos_desactivados_y_actual_sin_asignaciones(self):
        self.registrar_nombre("Pendiente conservado")
        for catalogo in (self.oficina, self.tramites[self.oficina.pk]):
            catalogo.activo = False
            catalogo.save(update_fields=["activo"])
        self.assertContains(self.client.get(self.cola), "Pendiente conservado")
        self.client.post(self.rutas["llamar"], self.datos("llamar"))
        for asignacion in self.asignaciones.values():
            self.historica_inactiva(asignacion)
        self.assertContains(self.client.get(self.actual), "Pendiente conservado")
        self.assertContains(self.client.get(self.actual), "Ocupado")

    def test_firma_manipulada_o_ausente_no_invoca_servicios(self):
        original = self.datos("llamar")
        antes = self.estado()
        for token in (None, "", original["token"] + "x", "x" * 2049):
            with patch("folios.views_operador.llamar_siguiente") as servicio:
                error = self.client.post(self.rutas["llamar"], {} if token is None else {"token": token})
                self.assertEqual(error.status_code, 400)
                self.assertNotContains(error, 'data-envio-operador', status_code=400)
                servicio.assert_not_called()
        self.assertEqual(self.estado(), antes)

    def test_token_otra_cuenta_u_operacion_se_rechaza(self):
        llamar = self.datos("llamar")
        pausa = self.datos("pausar")
        for accion, datos in (("llamar", pausa), ("pausar", {**llamar, "motivo": "Motivo"})):
            self.assertEqual(self.client.post(self.rutas[accion], datos).status_code, 400)
        self.client.force_login(self.otro)
        for accion, datos in (("llamar", llamar), ("pausar", pausa)):
            self.assertEqual(self.client.post(self.rutas[accion], datos).status_code, 400)
        self.assertEqual(SolicitudOperador.objects.count(), 0)

    def test_payload_firmado_invalido_no_crea_comprobante(self):
        base = self.intencion(self.datos("llamar"))
        for datos in (
            [], {}, {**base, "solicitud_id": "invalido"}, {**base, "actor_id": True},
            {**base, "destino": "https://externo.invalid/"}, {**base, "destino": "/administracion/"},
            {**base, "pausa_id": 1}, {**base, "extra": "no admitido"},
        ):
            self.assertEqual(self.client.post(self.rutas["llamar"], self.firmar(datos)).status_code, 400)
        self.assertEqual(SolicitudOperador.objects.count(), 0)

    def test_tokens_de_reanudar_exigen_pausa_positiva(self):
        self.pausar()
        base = self.intencion(self.datos("reanudar"))
        for pausa_id in (None, True, 0, -1, "1"):
            self.assertEqual(self.client.post(self.rutas["reanudar"], self.firmar({**base, "pausa_id": pausa_id})).status_code, 400)
        self.assertEqual(EventoDisponibilidad.objects.count(), 1)

    def test_pausa_ajena_firmada_no_elude_autorizacion_del_servicio(self):
        ajena = self.pausar(actor=self.otro)
        base = self.intencion(self.datos("pausar"))
        datos = self.firmar({**base, "operacion": "REANUDAR", "pausa_id": ajena.pausa_id})
        self.assertEqual(self.client.post(self.rutas["reanudar"], datos).status_code, 403)
        self.assertIsNone(PausaOperador.objects.get(pk=ajena.pausa_id).fin)

    def test_destinos_restringidos_e_ignorar_next_y_referer(self):
        datos = self.datos("pausar", pagina=self.actual)
        response = self.client.post(self.rutas["pausar"] + "?next=https://externo.invalid/", {
            **datos, "destino": "https://externo.invalid/", "next": "/administracion/",
        }, HTTP_REFERER="https://externo.invalid/")
        self.assertRedirects(response, self.actual)
        response = self.client.post(self.rutas["reanudar"], self.datos("reanudar"))
        self.assertRedirects(response, self.cola)

    def test_doble_envio_llamado_reutiliza_comprobante_y_mensaje_historico(self):
        self.registrar()
        datos = self.datos("llamar")
        primera = self.client.post(self.rutas["llamar"], datos, follow=True)
        self.assertContains(primera, "Se realizó el llamado")
        antes = self.estado()
        repetida = self.client.post(self.rutas["llamar"], datos, follow=True)
        self.assertContains(repetida, "Solicitud ya procesada")
        self.assertContains(repetida, "Resultado original: llamado realizado")
        self.assertNotContains(repetida, "Se realizó el llamado")
        self.assertEqual(self.estado(), antes)

    def test_doble_post_sin_seguir_redirect_no_acumula_mensaje_de_transicion(self):
        self.registrar()
        datos = self.datos("llamar")
        self.client.post(self.rutas["llamar"], datos)
        repetida = self.client.post(self.rutas["llamar"], datos, follow=True)
        self.assertContains(repetida, "Solicitud ya procesada")
        self.assertNotContains(repetida, "Se realizó el llamado")
        self.assertEqual(SolicitudOperador.objects.count(), 1)

    def test_solicitudes_distintas_no_llaman_dos_folios(self):
        self.registrar()
        self.registrar(self.segunda)
        una, otra = self.datos("llamar"), self.datos("llamar")
        self.assertNotEqual(self.intencion(una)["solicitud_id"], self.intencion(otra)["solicitud_id"])
        self.client.post(self.rutas["llamar"], una)
        response = self.client.post(self.rutas["llamar"], otra, follow=True)
        self.assertContains(response, "Ya tienes un folio a tu cargo")
        self.assertEqual(Folio.objects.filter(estado="LLAMADO").count(), 1)
        self.assertEqual(SolicitudOperador.objects.count(), 2)

    def test_motivo_obligatorio_no_recorta_texto_y_pausa_no_cambia_folio(self):
        self.registrar()
        self.llamar()
        folios = list(Folio.objects.values())
        datos = self.datos("pausar", motivo="  Motivo\ncon detalle  ")
        with patch("folios.views_operador.pausar_operador", wraps=pausar_operador) as servicio:
            response = self.client.post(self.rutas["pausar"], datos)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(servicio.call_args.kwargs["motivo"], datos["motivo"])
        self.assertEqual(PausaOperador.objects.get().motivo, datos["motivo"])
        self.assertEqual(SolicitudOperador.objects.get(operacion="PAUSAR").motivo_solicitado, datos["motivo"])
        self.assertEqual(list(Folio.objects.values()), folios)

    def test_formulario_invalido_conserva_token_y_motivo_sin_crear_clave(self):
        datos = self.datos("pausar")
        for motivo in ("", " \t\n "):
            with patch("folios.forms_operador.uuid4", side_effect=AssertionError("No generar otra clave")):
                error = self.client.post(self.rutas["pausar"], {**datos, "motivo": motivo})
            self.assertEqual(error.status_code, 400)
            self.assertEqual(error.context["form"]["token"].value(), datos["token"])
            self.assertEqual(error.context["form"]["motivo"].value(), motivo)
            self.assertContains(error, 'aria-invalid="true"', status_code=400)
        self.assertEqual(SolicitudOperador.objects.count(), 0)
        self.assertEqual(self.client.post(self.rutas["pausar"], datos).status_code, 302)

    def test_misma_clave_y_otro_motivo_rechaza_sin_reemplazarlo(self):
        datos = self.datos("pausar")
        self.client.post(self.rutas["pausar"], datos)
        antes = self.estado()
        with patch("folios.forms_operador.uuid4", side_effect=AssertionError("No generar otra clave")):
            error = self.client.post(self.rutas["pausar"], {**datos, "motivo": "Motivo distinto"})
        self.assertContains(error, "Esta clave ya confirmó argumentos diferentes", status_code=400)
        self.assertEqual(error.context["form"]["token"].value(), datos["token"])
        self.assertEqual(self.estado(), antes)

    def test_doble_envio_pausa_y_reanudacion_no_duplica_eventos(self):
        for accion in ("pausar", "reanudar"):
            datos = self.datos(accion)
            self.assertEqual(self.client.post(self.rutas[accion], datos).status_code, 302)
            antes = self.estado()
            response = self.client.post(self.rutas[accion], datos, follow=True)
            self.assertContains(response, "Solicitud ya procesada")
            self.assertEqual(self.estado(), antes)
        self.assertEqual(EventoDisponibilidad.objects.count(), 2)

    def test_reanudar_antigua_no_cierra_pausa_posterior(self):
        primera = self.pausar()
        antiguo = self.datos("reanudar")
        self.reanudar(primera.pausa_id)
        segunda = self.pausar(motivo="Pausa posterior")
        with patch("folios.views_operador.reanudar_operador", wraps=reanudar_operador) as servicio:
            response = self.client.post(self.rutas["reanudar"], {
                **antiguo, "pausa_id": segunda.pausa_id,
            }, follow=True)
        self.assertEqual(servicio.call_args.kwargs["pausa_id"], primera.pausa_id)
        self.assertContains(response, "Esa pausa ya estaba cerrada")
        self.assertContains(response, "En pausa")
        self.assertIsNone(PausaOperador.objects.get(pk=segunda.pausa_id).fin)

    def test_reintento_de_resultado_bloqueado_no_se_convierte_en_llamado(self):
        self.registrar()
        antiguo = self.datos("llamar")
        pausa = self.pausar()
        primera = self.client.post(self.rutas["llamar"], antiguo, follow=True)
        self.assertContains(primera, "Estás en pausa")
        self.reanudar(pausa.pausa_id)
        repetida = self.client.post(self.rutas["llamar"], antiguo, follow=True)
        self.assertContains(repetida, "Resultado original: en pausa; sin llamado")
        self.assertEqual(Folio.objects.get().estado, "EN_ESPERA")
        nueva = self.client.post(self.rutas["llamar"], self.datos("llamar"))
        self.assertRedirects(nueva, self.actual)

    def test_respuesta_perdida_conserva_intencion_para_reintentar(self):
        self.registrar()
        datos = self.datos("llamar")
        def confirmar_y_perder_respuesta(**kwargs):
            llamar_siguiente(**kwargs)
            raise DatabaseError("Respuesta perdida simulada")
        with patch("folios.views_operador.llamar_siguiente", side_effect=confirmar_y_perder_respuesta):
            with patch("folios.forms_operador.uuid4", side_effect=AssertionError("No generar otra clave")):
                error = self.client.post(self.rutas["llamar"], datos)
        self.assertEqual(error.status_code, 503)
        self.assertEqual(error.context["form"]["token"].value(), datos["token"])
        antes = self.estado()
        repetida = self.client.post(self.rutas["llamar"], datos, follow=True)
        self.assertContains(repetida, "Solicitud ya procesada")
        self.assertEqual(self.estado(), antes)

    def test_relecturas_distintas_no_prometen_aceptacion_del_post(self):
        datos = self.datos("llamar")
        self.pausar()
        response = self.client.post(self.rutas["llamar"], datos, follow=True)
        self.assertContains(response, "Estás en pausa")
        self.assertEqual(SolicitudOperador.objects.get(operacion="LLAMAR").resultado, "EN_PAUSA")

    def test_html_escapado_en_ciudadano_y_motivo_invalido(self):
        nombre = '<script>alert("ciudadano")</script>'
        self.registrar_nombre(nombre)
        self.assertContains(self.client.get(self.cola), escape(nombre))
        self.assertNotContains(self.client.get(self.cola), nombre)
        datos = self.datos("pausar", motivo='<script>alert("motivo")</script>')
        with patch("folios.views_operador.pausar_operador", side_effect=DatabaseError("fallo")):
            error = self.client.post(self.rutas["pausar"], datos)
        self.assertContains(error, escape(datos["motivo"]), status_code=503)
        self.assertNotContains(error, datos["motivo"], status_code=503)

    def test_pausa_sin_folio_y_ocupacion_se_presentan_sin_datos_extra(self):
        self.client.post(self.rutas["pausar"], self.datos("pausar"))
        pagina = self.client.get(self.actual)
        self.assertContains(pagina, "En pausa")
        self.assertContains(pagina, "Sin folio actual")
        self.assertContains(pagina, "Reanudar atención")
        self.assertNotContains(pagina, "Incidencia del área")
        self.client.post(self.rutas["reanudar"], self.datos("reanudar"))
        self.registrar()
        self.client.post(self.rutas["llamar"], self.datos("llamar"))
        pagina = self.client.get(self.actual)
        self.assertContains(pagina, "Ocupado")
        self.assertNotIn("form_llamar", pagina.context)
        self.assertIn("form_iniciar", pagina.context)

    def test_sin_javascript_las_tres_acciones_y_paginacion_son_html_nativo(self):
        self.registrar()
        pagina = self.client.get(self.cola)
        self.assertContains(pagina, '<summary class="boton secundario">Pausar atención</summary>', html=True)
        self.assertContains(pagina, 'method="post" action="/operacion/llamar/"')
        self.assertContains(pagina, 'method="post" action="/operacion/pausar/"')
        self.assertContains(pagina, '<label for="id_pausar_motivo">')
        self.client.post(self.rutas["llamar"], self.datos("llamar"))
        self.client.post(self.rutas["pausar"], self.datos("pausar"))
        pagina = self.client.get(self.actual)
        self.assertContains(pagina, 'method="post" action="/operacion/reanudar/"')
        self.assertEqual(self.client.post(self.rutas["reanudar"], self.datos("reanudar")).status_code, 302)

    def test_mensajes_no_reaparecen_al_recargar_get(self):
        response = self.client.post(self.rutas["llamar"], self.datos("llamar"), follow=True)
        self.assertContains(response, "No hay pendientes en tu cola. No se realizó un llamado.")
        self.assertNotContains(self.client.get(self.cola), "No hay pendientes en tu cola. No se realizó un llamado.")
        self.assertEqual(SolicitudOperador.objects.count(), 1)
