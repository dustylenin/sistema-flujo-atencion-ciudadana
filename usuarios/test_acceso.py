"""Acceso HTTP real con sesiones y CSRF sobre PostgreSQL aislado."""

from django.conf import settings
from django.contrib.auth import BACKEND_SESSION_KEY, SESSION_KEY
from django.contrib.sessions.models import Session
from django.db import connection
from django.test import Client
from django.urls import reverse

from oficinas.testing import CatalogosPostgreSQLTestCase

from .forms import ERROR_ACCESO
from .models import Usuario


class AccesoTests(CatalogosPostgreSQLTestCase):
    password = "clave-ficticia-exclusiva-de-las-pruebas"
    destinos = {
        Usuario.Rol.RECEPCION: "/recepcion/",
        Usuario.Rol.OPERADOR: "/operacion/",
        Usuario.Rol.ADMINISTRADOR: "/administracion/",
    }

    @classmethod
    def setUpClass(cls):
        if (
            settings.SETTINGS_MODULE != "config.settings_test_migrations"
            or connection.settings_dict["NAME"] != "test_atencion_catalogos_migraciones"
        ):
            raise RuntimeError("Use exclusivamente config.settings_test_migrations.")
        # Verifica identidad real antes de las escrituras de setUpTestData.
        super().setUpClass()

    @classmethod
    def setUpTestData(cls):
        cls.cuentas = {
            rol: Usuario.objects.create_user(
                username=f"acceso_{rol.lower()}", password=cls.password, rol=rol,
            )
            for rol in cls.destinos
        }

    def entrar(self, rol=Usuario.Rol.RECEPCION, client=None, **extra):
        client = client or self.client
        return client.post("/acceso/", {
            "username": self.cuentas[rol].username, "password": self.password, **extra,
        })

    def csrf_client(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.get("/acceso/").status_code, 200)
        return client, client.cookies[settings.CSRF_COOKIE_NAME].value

    def test_login_ofrece_etiquetas_csrf_y_orientacion_sin_acciones_extra(self):
        response = self.client.get("/acceso/")
        self.assertContains(response, '<label for="id_username">Usuario</label>', html=True)
        self.assertContains(response, '<label for="id_password">Contraseña</label>', html=True)
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        self.assertContains(response, 'autocomplete="current-password"')
        self.assertContains(response, 'autocomplete="username"')
        self.assertContains(response, "Mostrar contraseña")
        self.assertContains(response, "contacta al administrador")
        self.assertContains(response, 'method="post" action="/acceso/"')
        self.assertNotContains(response, 'name="next"')
        self.assertNotContains(response, "Recuperar contraseña")

    def test_login_autentica_con_backend_estandar_y_destino_de_cada_rol(self):
        self.assertEqual(settings.AUTHENTICATION_BACKENDS, ["django.contrib.auth.backends.ModelBackend"])
        for rol, destino in self.destinos.items():
            with self.subTest(rol=rol):
                client = Client()
                self.assertRedirects(self.entrar(rol, client), destino)
                self.assertEqual(client.session[SESSION_KEY], str(self.cuentas[rol].pk))
                self.assertEqual(client.session[BACKEND_SESSION_KEY], settings.AUTHENTICATION_BACKENDS[0])
                self.cuentas[rol].refresh_from_db()
                self.assertIsNotNone(self.cuentas[rol].last_login)

    def test_next_en_query_y_post_se_ignora_incluso_interno(self):
        for destino in ("/administracion/", "https://externo.invalid/", "//externo.invalid/", "/salir/"):
            with self.subTest(next=destino):
                client = Client()
                response = client.post("/acceso/?next=" + destino, {
                    "username": self.cuentas[Usuario.Rol.RECEPCION].username,
                    "password": self.password, "next": destino,
                })
                self.assertRedirects(response, "/recepcion/")

    def test_autenticado_en_login_y_raiz_va_a_su_rol_sin_next(self):
        for rol, destino in self.destinos.items():
            with self.subTest(rol=rol):
                client = Client()
                self.entrar(rol, client)
                self.assertRedirects(client.get("/acceso/?next=/salir/"), destino)
                self.assertRedirects(client.get("/?next=/salir/"), destino)

    def test_get_con_credenciales_no_autentica_ni_muestra_contrasena(self):
        response = self.client.get("/acceso/", {
            "username": self.cuentas[Usuario.Rol.RECEPCION].username,
            "password": self.password,
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertNotContains(response, self.password)

    def test_error_generico_igualmente_para_usuario_inexistente_clave_mala_e_inactivo(self):
        cuenta = self.cuentas[Usuario.Rol.ADMINISTRADOR]
        cuenta.is_active = False
        cuenta.save(update_fields=["is_active"])
        casos = [
            ("no_existe", self.password),
            (self.cuentas[Usuario.Rol.RECEPCION].username, "incorrecta"),
            (cuenta.username, self.password),
        ]
        for username, password in casos:
            with self.subTest(username=username):
                response = self.client.post("/acceso/", {"username": username, "password": password})
                self.assertContains(response, ERROR_ACCESO)
                self.assertEqual(list(response.context["form"].non_field_errors()), [ERROR_ACCESO])
                self.assertNotIn(SESSION_KEY, self.client.session)
                self.assertNotContains(response, 'value="' + password + '"')

    def test_contrasena_nunca_se_repuebla_y_usuario_se_escapa(self):
        response = self.client.post("/acceso/", {
            "username": '<script>alert("x")</script>', "password": self.password,
        })
        self.assertNotContains(response, self.password)
        self.assertNotContains(response, '<script>alert("x")</script>')
        self.assertContains(response, "&lt;script&gt;")
        self.assertContains(response, 'aria-describedby="error-acceso"')
        self.assertContains(response, 'aria-invalid="true"')
        self.assertContains(response, 'role="alert"')

    def test_campos_obligatorios_no_crean_sesion(self):
        response = self.client.post("/acceso/", {})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.context["form"].errors), {"username", "password"})
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_anonimo_no_accede_a_ningun_destino_ni_raiz(self):
        for url in ("/", *self.destinos.values()):
            with self.subTest(url=url):
                self.assertRedirects(self.client.get(url), "/acceso/")

    def test_cada_rol_solo_accede_a_su_destino(self):
        for rol, destino in self.destinos.items():
            client = Client()
            self.entrar(rol, client)
            for url in self.destinos.values():
                with self.subTest(rol=rol, url=url):
                    self.assertEqual(client.get(url).status_code, 200 if url == destino else 403)

    def test_flags_tecnicos_no_conceden_ni_restringen_permisos_funcionales(self):
        for rol, cuenta in self.cuentas.items():
            for staff, superuser in ((False, False), (True, False), (False, True), (True, True)):
                with self.subTest(rol=rol, staff=staff, superuser=superuser):
                    cuenta.is_staff, cuenta.is_superuser = staff, superuser
                    cuenta.save(update_fields=["is_staff", "is_superuser"])
                    client = Client()
                    self.assertRedirects(self.entrar(rol, client), self.destinos[rol])
                    for otro_rol, url in self.destinos.items():
                        self.assertEqual(client.get(url).status_code, 200 if otro_rol == rol else 403)

    def test_desactivacion_bloquea_sesion_existente_aun_con_flags_tecnicos(self):
        cuenta = self.cuentas[Usuario.Rol.RECEPCION]
        cuenta.is_staff = cuenta.is_superuser = True
        cuenta.save(update_fields=["is_staff", "is_superuser"])
        self.entrar()
        cuenta.is_active = False
        cuenta.save(update_fields=["is_active"])
        for url in ("/", *self.destinos.values()):
            with self.subTest(url=url):
                self.assertRedirects(self.client.get(url), "/acceso/")
        response = self.client.get("/acceso/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["user"].is_anonymous)

    def test_cambio_de_rol_revalida_sesion_y_redirecciones(self):
        self.entrar()
        cuenta = self.cuentas[Usuario.Rol.RECEPCION]
        cuenta.rol = Usuario.Rol.ADMINISTRADOR
        cuenta.save(update_fields=["rol"])
        self.assertEqual(self.client.get("/recepcion/").status_code, 403)
        self.assertEqual(self.client.get("/administracion/").status_code, 200)
        self.assertEqual(self.client.get("/operacion/").status_code, 403)
        self.assertRedirects(self.client.get("/acceso/"), "/administracion/")
        self.assertRedirects(self.client.get("/"), "/administracion/")

    def test_rol_inyectado_en_sesion_no_otorga_acceso(self):
        self.entrar()
        session = self.client.session
        session["rol"] = Usuario.Rol.ADMINISTRADOR
        session["is_superuser"] = True
        session.save()
        self.assertEqual(self.client.get("/administracion/").status_code, 403)
        self.assertEqual(self.client.get("/recepcion/").status_code, 200)

    def test_login_rota_la_sesion_anonima(self):
        session = self.client.session
        session["dato_anonimo"] = "conservado"
        session.save()
        original = session.session_key
        self.entrar()
        self.assertNotEqual(self.client.session.session_key, original)
        self.assertFalse(Session.objects.filter(session_key=original).exists())
        self.assertEqual(self.client.session["dato_anonimo"], "conservado")

    def test_login_rechaza_post_sin_csrf(self):
        client, _ = self.csrf_client()
        self.assertEqual(self.entrar(client=client).status_code, 403)
        self.assertNotIn(SESSION_KEY, client.session)

    def test_login_rechaza_csrf_de_otro_navegador(self):
        client, _ = self.csrf_client()
        _, otro_token = self.csrf_client()
        self.assertEqual(self.entrar(client=client, csrfmiddlewaretoken=otro_token).status_code, 403)
        self.assertNotIn(SESSION_KEY, client.session)

    def test_login_rechaza_origen_ajeno_aun_con_token_valido(self):
        client, token = self.csrf_client()
        response = client.post("/acceso/", {
            "username": self.cuentas[Usuario.Rol.RECEPCION].username,
            "password": self.password, "csrfmiddlewaretoken": token,
        }, HTTP_ORIGIN="https://externo.invalid")
        self.assertEqual(response.status_code, 403)
        self.assertNotIn(SESSION_KEY, client.session)

    def test_login_y_logout_con_csrf_sin_ejecutar_javascript(self):
        client, token = self.csrf_client()
        self.assertRedirects(self.entrar(client=client, csrfmiddlewaretoken=token), "/recepcion/")
        nuevo_token = client.cookies[settings.CSRF_COOKIE_NAME].value
        self.assertNotEqual(nuevo_token, token)
        self.assertRedirects(client.post("/salir/", {"csrfmiddlewaretoken": nuevo_token}), "/acceso/")
        self.assertNotIn(SESSION_KEY, client.session)
        self.assertRedirects(client.get("/recepcion/"), "/acceso/")

    def test_logout_get_no_cierra_sesion_y_solo_post_esta_permitido(self):
        self.entrar()
        for metodo in ("get", "head", "put", "delete", "options"):
            with self.subTest(metodo=metodo):
                response = getattr(self.client, metodo)("/salir/")
                self.assertEqual(response.status_code, 405)
                self.assertEqual(response.headers["Allow"], "POST")
                self.assertIn(SESSION_KEY, self.client.session)

    def test_logout_rechaza_csrf_ausente_y_token_anterior_al_login(self):
        client, token = self.csrf_client()
        self.entrar(client=client, csrfmiddlewaretoken=token)
        for data in ({}, {"csrfmiddlewaretoken": token}):
            with self.subTest(data_presente=bool(data)):
                self.assertEqual(client.post("/salir/", data).status_code, 403)
                self.assertIn(SESSION_KEY, client.session)

    def test_logout_destruye_sesion_e_ignora_next(self):
        self.entrar()
        original = self.client.session.session_key
        response = self.client.post("/salir/?next=https://externo.invalid/", {"next": "/administracion/"})
        self.assertRedirects(response, "/acceso/")
        self.assertFalse(Session.objects.filter(session_key=original).exists())
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_destinos_muestran_solo_identidad_y_salida(self):
        self.entrar()
        response = self.client.get("/recepcion/")
        self.assertContains(response, self.cuentas[Usuario.Rol.RECEPCION].username)
        self.assertContains(response, 'method="post" action="/salir/"')
        self.assertNotContains(response, self.cuentas[Usuario.Rol.ADMINISTRADOR].username)
        self.assertNotContains(response, "Registrar folio")
        self.assertNotContains(response, "Llamar siguiente")

    def test_respuestas_de_acceso_y_destino_no_se_almacenan_en_cache(self):
        self.assertIn("no-store", self.client.get("/acceso/").headers["Cache-Control"])
        self.entrar()
        for url in ("/", "/recepcion/", "/acceso/"):
            with self.subTest(url=url):
                self.assertIn("no-store", self.client.get(url).headers["Cache-Control"])

    def test_no_hay_rutas_de_registro_contrasenas_ni_admin_tecnico(self):
        antes = Usuario.objects.count()
        for url in ("/admin/", "/registro/", "/password_reset/", "/password_change/", "/accounts/login/"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)
                self.assertEqual(self.client.post(url, {"username": "nuevo"}).status_code, 404)
        self.assertEqual(Usuario.objects.count(), antes)
        self.assertEqual(reverse("usuarios:login"), "/acceso/")
