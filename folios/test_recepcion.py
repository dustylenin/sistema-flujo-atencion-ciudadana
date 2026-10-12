"""Recepción HTTP real, exclusivamente con migraciones ya aplicadas en pruebas."""

from unittest.mock import patch
from uuid import uuid4

from django.conf import settings
from django.db import connection
from django.test import Client
from django.urls import reverse
from django.utils.html import escape

from oficinas.models import Oficina
from oficinas.testing import CatalogosPostgreSQLTestCase
from tramites.models import Tramite
from usuarios.models import Usuario

from .models import EventoFolio, Folio
from .services import registrar_folio


class RecepcionTests(CatalogosPostgreSQLTestCase):
    @classmethod
    def setUpClass(cls):
        if (
            settings.SETTINGS_MODULE != "config.settings_test_migrations"
            or connection.settings_dict["NAME"] != "test_atencion_catalogos_migraciones"
        ):
            raise RuntimeError("Use exclusivamente config.settings_test_migrations.")
        super().setUpClass()

    @classmethod
    def setUpTestData(cls):
        cls.actor = Usuario.objects.create_user(username="recepcion_pantalla", rol=Usuario.Rol.RECEPCION)
        cls.otra = Usuario.objects.create_user(username="otra_recepcion", rol=Usuario.Rol.RECEPCION)
        cls.oficina = Oficina.objects.create(nombre="Oficina disponible")
        cls.tramite = Tramite.objects.create(nombre="Trámite disponible", oficina=cls.oficina)
        cls.segunda = Oficina.objects.create(nombre="Otra oficina")
        cls.otro_tramite = Tramite.objects.create(nombre="Otro trámite", oficina=cls.segunda)
        cls.sin_tramites = Oficina.objects.create(nombre="Oficina sin trámites")
        cls.inactiva = Oficina.objects.create(nombre="Oficina inactiva", activo=False)
        cls.tramite_oficina_inactiva = Tramite.objects.create(nombre="Trámite de oficina inactiva", oficina=cls.inactiva)
        cls.tramite_inactivo = Tramite.objects.create(nombre="Trámite inactivo", oficina=cls.oficina, activo=False)

    def setUp(self):
        self.client.force_login(self.actor)
        self.url = reverse("usuarios:recepcion")
        self.url_tramites = reverse("usuarios:recepcion_tramites")

    def datos(self, **extra):
        datos = {
            "accion": "registrar", "nombre_completo": "  Ciudadano de prueba  ",
            "correo": "", "telefono": "", "oficina": self.oficina.pk, "tramite": self.tramite.pk,
        }
        datos.update(extra)
        return datos

    def registrar(self, actor=None, **extra):
        datos = self.datos(**extra)
        resultado = registrar_folio(
            actor=actor or self.actor, nombre_completo=datos["nombre_completo"],
            correo=datos["correo"], telefono=datos["telefono"],
            oficina_id=datos["oficina"], tramite_id=datos["tramite"],
        )
        return reverse("usuarios:recepcion_confirmacion", args=[resultado.folio_id])

    def assert_sin_registros(self):
        self.assertEqual((Folio.objects.count(), EventoFolio.objects.count()), (0, 0))

    def test_pantalla_etiquetas_y_salida_sin_acciones_pendientes(self):
        response = self.client.get(self.url)
        self.assertContains(response, "Nueva atención")
        self.assertContains(response, 'method="post" action="/salir/"')
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        for campo in ("nombre_completo", "correo", "telefono", "oficina", "tramite"):
            self.assertContains(response, f'for="id_{campo}"')
        for texto in ("Llamar", "Reservar", "Trasladar", "Status", "Atenciones del día"):
            self.assertNotContains(response, texto)
        self.assert_sin_registros()

    def test_anonimos_no_acceden_a_formulario_catalogos_ni_confirmacion(self):
        confirmacion = self.registrar()
        client = Client()
        for url in (self.url, self.url_tramites, confirmacion):
            self.assertRedirects(client.get(url), "/acceso/")
        self.assertRedirects(client.post(self.url, self.datos()), "/acceso/")
        self.assertEqual(Folio.objects.count(), 1)

    def test_roles_ajenos_no_acceden_incluso_con_flags_tecnicos(self):
        confirmacion = self.registrar()
        for rol in (Usuario.Rol.ADMINISTRADOR, Usuario.Rol.OPERADOR):
            cuenta = Usuario.objects.create_user(
                username=f"ajeno_{rol}", rol=rol, is_staff=True, is_superuser=True,
            )
            self.client.force_login(cuenta)
            for url in (self.url, self.url_tramites, confirmacion):
                self.assertEqual(self.client.get(url).status_code, 403)
            self.assertEqual(self.client.post(self.url, self.datos()).status_code, 403)
        self.assertEqual((Folio.objects.count(), EventoFolio.objects.count()), (1, 1))

    def test_recepcion_admite_todas_las_combinaciones_de_flags(self):
        for staff, superuser in ((False, False), (False, True), (True, False), (True, True)):
            self.actor.is_staff, self.actor.is_superuser = staff, superuser
            self.actor.save(update_fields=["is_staff", "is_superuser"])
            self.assertEqual(self.client.post(self.url, self.datos()).status_code, 302)
        self.assertEqual((Folio.objects.count(), EventoFolio.objects.count()), (4, 4))

    def test_cambio_de_rol_con_sesion_existente_bloquea_todas_las_rutas(self):
        confirmacion = self.registrar()
        self.actor.rol = Usuario.Rol.ADMINISTRADOR
        self.actor.save(update_fields=["rol"])
        for url in (self.url, self.url_tramites, confirmacion):
            self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(self.url, self.datos()).status_code, 403)
        self.assertEqual(Folio.objects.count(), 1)

    def test_desactivacion_con_sesion_existente_exige_autenticacion(self):
        confirmacion = self.registrar()
        self.actor.is_active = False
        self.actor.save(update_fields=["is_active"])
        for url in (self.url, self.url_tramites, confirmacion):
            self.assertRedirects(self.client.get(url), "/acceso/")
        self.assertRedirects(self.client.post(self.url, self.datos()), "/acceso/")
        self.assertEqual(Folio.objects.count(), 1)

    def test_catalogos_muestran_solo_opciones_habilitadas(self):
        response = self.client.get(self.url)
        self.assertContains(response, self.oficina.nombre)
        self.assertContains(response, self.segunda.nombre)
        self.assertNotContains(response, self.sin_tramites.nombre)
        self.assertNotContains(response, self.inactiva.nombre)
        response = self.client.get(self.url_tramites, {"oficina": self.oficina.pk})
        self.assertEqual(response.json(), {"tramites": [{"id": self.tramite.pk, "nombre": self.tramite.nombre}]})
        self.assert_sin_registros()

    def test_cargar_sin_javascript_conserva_captura_incompleta_o_invalida(self):
        for nombre in ("", " \t ", '<script>alert("captura")</script>'):
            response = self.client.post(self.url, self.datos(
                accion="cargar_tramites", nombre_completo=nombre,
                correo="no-es-correo", telefono="extensión / sin formato", tramite="",
            ))
            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.context["form"].is_bound)
            self.assertFalse(response.context["form"].errors)
            self.assertFalse(response.context["carga"].errors)
            for campo, valor in (("nombre_completo", nombre), ("correo", "no-es-correo"), ("telefono", "extensión / sin formato")):
                self.assertEqual(response.context["form"][campo].value(), valor)
            self.assertContains(response, self.tramite.nombre)
            self.assertContains(response, "formnovalidate")
            self.assertNotContains(response, self.otro_tramite.nombre)
        self.assert_sin_registros()

    def test_cargar_oficina_invalida_conserva_datos_y_no_registra(self):
        for oficina in ("", "abc", 9999999, self.inactiva.pk, self.sin_tramites.pk):
            response = self.client.post(self.url, self.datos(accion="cargar_tramites", oficina=oficina))
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["carga"].errors)
            self.assertEqual(response.context["form"]["nombre_completo"].value(), self.datos()["nombre_completo"])
            self.assertEqual(self.client.get(self.url_tramites, {"oficina": oficina}).status_code, 400)
        self.assert_sin_registros()

    def test_cambiar_oficina_no_ofrece_tramite_anterior(self):
        response = self.client.post(self.url, self.datos(accion="cargar_tramites", oficina=self.segunda.pk))
        self.assertContains(response, self.otro_tramite.nombre)
        self.assertNotContains(response, self.tramite.nombre)
        self.assert_sin_registros()

    def test_campos_invalidos_no_escriben_y_conservan_datos(self):
        for extra, campo in (
            ({"nombre_completo": ""}, "nombre_completo"),
            ({"nombre_completo": " \t\n "}, "nombre_completo"),
            ({"correo": "no-es-correo"}, "correo"),
            ({"correo": "x" * 255 + "@example.test"}, "correo"),
            ({"oficina": ""}, "oficina"), ({"tramite": ""}, "tramite"),
        ):
            with self.subTest(extra=extra):
                response = self.client.post(self.url, self.datos(**extra))
                self.assertEqual(response.status_code, 200)
                self.assertIn(campo, response.context["form"].errors)
                self.assertContains(response, 'aria-invalid="true"')
                self.assertEqual(response.context["form"]["telefono"].value(), "")
                self.assert_sin_registros()

    def test_referencias_manipuladas_o_inactivas_no_escriben(self):
        for extra in (
            {"oficina": 9999999}, {"oficina": "abc"}, {"tramite": 9999999},
            {"tramite": self.otro_tramite.pk}, {"tramite": self.tramite_inactivo.pk},
            {"oficina": self.inactiva.pk, "tramite": self.tramite_oficina_inactiva.pk},
        ):
            with self.subTest(extra=extra):
                response = self.client.post(self.url, self.datos(**extra))
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["form"].errors)
                self.assert_sin_registros()

    def test_desactivar_catalogos_entre_mostrar_y_enviar_no_escribe(self):
        self.client.post(self.url, self.datos(accion="cargar_tramites"))
        self.tramite.activo = False
        self.tramite.save(update_fields=["activo"])
        self.assertTrue(self.client.post(self.url, self.datos()).context["form"].errors)
        self.tramite.activo = True
        self.tramite.save(update_fields=["activo"])
        self.oficina.activo = False
        self.oficina.save(update_fields=["activo"])
        self.assertTrue(self.client.post(self.url, self.datos()).context["form"].errors)
        self.assert_sin_registros()

    def test_servicio_revalida_catalogo_despues_del_formulario(self):
        def desactivar_y_registrar(**kwargs):
            Tramite.objects.filter(pk=self.tramite.pk).update(activo=False)
            return registrar_folio(**kwargs)
        with patch("folios.views.registrar_folio", side_effect=desactivar_y_registrar):
            response = self.client.post(self.url, self.datos())
        self.assertEqual(response.status_code, 200)
        self.assertIn("tramite", response.context["form"].errors)
        self.assertContains(response, "Se requiere un trámite activo")
        self.assert_sin_registros()

    def test_servicio_revalida_rol_despues_del_formulario(self):
        def cambiar_y_registrar(**kwargs):
            self.actor.rol = Usuario.Rol.ADMINISTRADOR
            self.actor.save(update_fields=["rol"])
            return registrar_folio(**kwargs)
        with patch("folios.views.registrar_folio", side_effect=cambiar_y_registrar):
            response = self.client.post(self.url, self.datos())
        self.assertEqual(response.status_code, 403)
        self.assert_sin_registros()

    def test_fallo_del_evento_revierte_el_registro_desde_la_vista(self):
        with patch("folios.services._crear_evento", side_effect=RuntimeError("fallo simulado")):
            with self.assertRaisesMessage(RuntimeError, "fallo simulado"):
                self.client.post(self.url, self.datos())
        self.assert_sin_registros()

    def test_registro_sin_javascript_preserva_servicio_y_confirmacion(self):
        datos = self.datos(telefono="extensión A / sin formato", correo="persona@example.test")
        self.client.post(self.url, {**datos, "accion": "cargar_tramites"})
        with patch("folios.views.registrar_folio", wraps=registrar_folio) as servicio:
            response = self.client.post(self.url, datos)
        servicio.assert_called_once()
        folio = Folio.objects.get()
        evento = EventoFolio.objects.get()
        self.assertEqual((folio.nombre_completo, folio.correo, folio.telefono), (datos["nombre_completo"], datos["correo"], datos["telefono"]))
        self.assertEqual((folio.estado, folio.operador_responsable_id), ("EN_ESPERA", None))
        self.assertEqual((folio.registrado_por_id, evento.actor_id, evento.folio_id), (self.actor.pk, self.actor.pk, folio.pk))
        self.assertEqual(evento.fecha, folio.llegada_original)
        self.assertEqual(evento.operacion, "CREACION")
        self.assertEqual(evento.datos_iniciales["telefono"], datos["telefono"])
        self.assertRedirects(response, reverse("usuarios:recepcion_confirmacion", args=[folio.pk]))
        confirmacion = self.client.get(response.url)
        for texto in (datos["nombre_completo"], self.oficina.nombre, self.tramite.nombre, "En espera", "Fecha y hora de llegada"):
            self.assertContains(confirmacion, texto)
        self.assertNotContains(confirmacion, str(folio.pk))

    def test_opcionales_omitidos_y_campos_del_servidor_no_se_sustituyen(self):
        datos = self.datos(estado="LLAMADO", operador_responsable=self.otra.pk, registrado_por=self.otra.pk, llegada_original="2000-01-01", id=str(uuid4()))
        datos.pop("correo")
        datos.pop("telefono")
        self.assertEqual(self.client.post(self.url, datos).status_code, 302)
        folio = Folio.objects.get()
        self.assertEqual((folio.correo, folio.telefono), ("", ""))
        self.assertEqual((folio.estado, folio.operador_responsable_id, folio.registrado_por_id), ("EN_ESPERA", None, self.actor.pk))
        self.assertNotEqual(str(folio.pk), datos["id"])

    def test_confirmacion_es_propia_y_no_requiere_catalogos_aun_activos(self):
        url = self.registrar()
        self.oficina.activo = False
        self.oficina.save(update_fields=["activo"])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.client.force_login(self.otra)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.get(reverse("usuarios:recepcion_confirmacion", args=[uuid4()])).status_code, 404)

    def test_recargar_confirmacion_y_cargar_catalogos_no_escribe(self):
        url = self.registrar()
        for _ in range(2):
            self.assertEqual(self.client.get(url).status_code, 200)
            self.client.get(self.url)
            self.client.get(self.url_tramites, {"oficina": self.oficina.pk})
            self.client.post(self.url, self.datos(accion="cargar_tramites"))
        self.assertEqual((Folio.objects.count(), EventoFolio.objects.count()), (1, 1))

    def test_dos_post_validos_crean_atenciones_independientes(self):
        primera = self.client.post(self.url, self.datos())
        segunda = self.client.post(self.url, self.datos())
        self.assertNotEqual(primera.url, segunda.url)
        self.assertEqual((Folio.objects.count(), EventoFolio.objects.count()), (2, 2))

    def test_escape_en_captura_catalogos_y_confirmacion(self):
        nombre = '<script>alert("nombre")</script>'
        oficina = Oficina.objects.create(nombre="<img src=x onerror=alert(1)>")
        tramite = Tramite.objects.create(nombre="<script>trámite</script>", oficina=oficina)
        response = self.client.post(self.url, self.datos(nombre_completo=nombre, correo="invalido", oficina=oficina.pk, tramite=tramite.pk))
        for texto in (nombre, oficina.nombre, tramite.nombre):
            self.assertContains(response, escape(texto))
            self.assertNotContains(response, texto)
        response = self.client.post(self.url, self.datos(nombre_completo=nombre, oficina=oficina.pk, tramite=tramite.pk))
        confirmacion = self.client.get(response.url)
        for texto in (nombre, oficina.nombre, tramite.nombre):
            self.assertContains(confirmacion, escape(texto))
            self.assertNotContains(confirmacion, texto)

    def test_csrf_para_carga_registro_y_logout(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.actor)
        client.get(self.url)
        token = client.cookies[settings.CSRF_COOKIE_NAME].value
        otro = Client(enforce_csrf_checks=True)
        otro.get("/acceso/")
        ajeno = otro.cookies[settings.CSRF_COOKIE_NAME].value
        for accion in ("cargar_tramites", "registrar"):
            self.assertEqual(client.post(self.url, self.datos(accion=accion)).status_code, 403)
            self.assertEqual(client.post(self.url, self.datos(accion=accion, csrfmiddlewaretoken=ajeno)).status_code, 403)
            self.assertEqual(client.post(self.url, self.datos(accion=accion, csrfmiddlewaretoken=token), HTTP_ORIGIN="https://ajeno.invalid").status_code, 403)
        self.assert_sin_registros()
        self.assertEqual(client.post(self.url, self.datos(accion="cargar_tramites", csrfmiddlewaretoken=token)).status_code, 200)
        self.assert_sin_registros()
        self.assertEqual(client.post(self.url, self.datos(csrfmiddlewaretoken=token)).status_code, 302)
        self.assertEqual(client.post("/salir/").status_code, 403)
        self.assertRedirects(client.post("/salir/", {"csrfmiddlewaretoken": token}), "/acceso/")

    def test_metodos_y_acciones_invalidas_no_escriben(self):
        for datos in ({}, self.datos(accion="otra")):
            self.assertEqual(self.client.post(self.url, datos).status_code, 400)
        for url in (self.url_tramites, reverse("usuarios:recepcion_confirmacion", args=[uuid4()])):
            self.assertEqual(self.client.post(url, self.datos()).status_code, 405)
        self.assertEqual(self.client.put(self.url).status_code, 405)
        self.assert_sin_registros()

    def test_sin_catalogos_muestra_estado_vacio_y_deshabilita_registro(self):
        Oficina.objects.all().update(activo=False)
        response = self.client.get(self.url)
        self.assertContains(response, "No hay oficinas con trámites disponibles")
        self.assertContains(response, 'id="registrar" disabled')
        self.assert_sin_registros()

    def test_respuestas_privadas_no_se_almacenan_en_cache(self):
        url = self.registrar()
        for ruta in (self.url, self.url_tramites + f"?oficina={self.oficina.pk}", url):
            self.assertIn("no-store", self.client.get(ruta).headers["Cache-Control"])
