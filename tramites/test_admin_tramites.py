from django.urls import reverse

from oficinas.models import Oficina
from oficinas.testing import CatalogosPostgreSQLTestCase
from usuarios.models import Usuario

from .models import Tramite


class AdminTramitesViewTests(CatalogosPostgreSQLTestCase):
    def setUp(self):
        super().setUp()
        self.admin = Usuario.objects.create_user(
            username="admin_tramites_user",
            password="admin_password123",
            rol=Usuario.Rol.ADMINISTRADOR,
        )
        self.operador = Usuario.objects.create_user(
            username="operador_tramites_user",
            password="operador_password123",
            rol=Usuario.Rol.OPERADOR,
        )
        self.recepcion = Usuario.objects.create_user(
            username="recepcion_tramites_user",
            password="recepcion_password123",
            rol=Usuario.Rol.RECEPCION,
        )
        self.oficina1 = Oficina.objects.create(nombre="Vialidad y Tránsito", activo=True)
        self.oficina2 = Oficina.objects.create(nombre="Registro Civil", activo=True)
        self.oficina_inactiva = Oficina.objects.create(nombre="Módulo Desactivado", activo=False)
        self.url = reverse("tramites:gestion_tramites")

    def test_url_resolucion(self):
        self.assertEqual(self.url, "/administracion/tramites/")
        self.assertEqual(reverse("usuarios:admin_tramites"), "/administracion/tramites/")

    def test_acceso_anonimo_redirige_a_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse("usuarios:login"))

    def test_acceso_roles_no_administrador_prohibido(self):
        for usuario in (self.operador, self.recepcion):
            self.client.force_login(usuario)
            response = self.client.get(self.url)
            self.assertEqual(response.status_code, 403)
            post_response = self.client.post(self.url, {"nombre": "Prueba"})
            self.assertEqual(post_response.status_code, 403)

    def test_administrador_get_lista_tramites_y_elementos_ui(self):
        tramite1 = Tramite.objects.create(nombre="Licencia de Conducir", oficina=self.oficina1, activo=True)
        tramite2 = Tramite.objects.create(nombre="Permiso de Carga", oficina=self.oficina1, activo=False)

        self.client.force_login(self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        # Contexto
        self.assertIn("tramites", response.context)
        tramites_ctx = list(response.context["tramites"])
        self.assertIn(tramite1, tramites_ctx)
        self.assertIn(tramite2, tramites_ctx)

        # Oficinas en contexto solo deben ser activas
        self.assertIn("oficinas", response.context)
        oficinas_ctx = list(response.context["oficinas"])
        self.assertIn(self.oficina1, oficinas_ctx)
        self.assertIn(self.oficina2, oficinas_ctx)
        self.assertNotIn(self.oficina_inactiva, oficinas_ctx)

        contenido = response.content.decode("utf-8")

        # Estructura visual de tarjeta y tabla
        self.assertIn('class="tarjeta"', contenido)
        self.assertIn("<th scope=\"col\">Trámite</th>", contenido)
        self.assertIn("<th scope=\"col\">Estado</th>", contenido)
        self.assertIn("<th scope=\"col\">Oficina responsable</th>", contenido)
        self.assertIn("<th scope=\"col\">Acciones</th>", contenido)

        # Botones requeridos
        self.assertIn('class="boton primario"', contenido)
        self.assertIn('class="boton secundario"', contenido)
        self.assertIn("Nuevo trámite", contenido)
        self.assertIn("Editar", contenido)

        # Dialog modal HTML5 nativo
        self.assertIn("<dialog", contenido)
        self.assertIn('id="dialog-nuevo-tramite"', contenido)

        # Enlace del menú lateral a trámites
        self.assertIn(self.url, contenido)

        # Datos de trámites mostrados en la tabla
        self.assertIn("Licencia de Conducir", contenido)
        self.assertIn("Permiso de Carga", contenido)
        self.assertIn("Vialidad y Tránsito", contenido)
        self.assertIn("Activo", contenido)
        self.assertIn("Inactivo", contenido)

    def test_administrador_post_crear_tramite_exitoso(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            self.url,
            {
                "nombre": "Renovación de Placas",
                "oficina_id": self.oficina1.pk,
                "activo": "true",
                "descripcion": "Trámite anual vehicular",
            },
        )
        self.assertRedirects(response, self.url)

        tramite = Tramite.objects.filter(nombre="Renovación de Placas").first()
        self.assertIsNotNone(tramite)
        self.assertEqual(tramite.oficina, self.oficina1)
        self.assertTrue(tramite.activo)

        # Mensaje flash mostrado tras redirección
        follow_response = self.client.get(self.url)
        self.assertContains(follow_response, "Renovación de Placas")

    def test_administrador_post_crear_tramite_inactivo(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            self.url,
            {
                "nombre": "Permiso Especial Suspendido",
                "oficina_id": self.oficina1.pk,
                "activo": "false",
                "descripcion": "Suspendido temporalmente",
            },
        )
        self.assertRedirects(response, self.url)

        tramite = Tramite.objects.filter(nombre="Permiso Especial Suspendido").first()
        self.assertIsNotNone(tramite)
        self.assertFalse(tramite.activo)

    def test_administrador_post_duplicado_misma_oficina_rechazado(self):
        Tramite.objects.create(nombre="Acta de Defunción", oficina=self.oficina2, activo=True)
        self.client.force_login(self.admin)

        # Intento de duplicar en la misma oficina (con mayúsculas/espacios)
        response = self.client.post(
            self.url,
            {
                "nombre": "  acta de defunción  ",
                "oficina_id": self.oficina2.pk,
                "activo": "true",
                "descripcion": "Duplicado",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ya existe")
        self.assertEqual(
            Tramite.objects.filter(nombre__iexact="acta de defunción", oficina=self.oficina2).count(),
            1,
        )

    def test_administrador_post_mismo_nombre_distinta_oficina_permitido(self):
        Tramite.objects.create(nombre="Constancia de Residencia", oficina=self.oficina1, activo=True)
        self.client.force_login(self.admin)

        # Crear trámite con el mismo nombre pero en oficina distinta
        response = self.client.post(
            self.url,
            {
                "nombre": "Constancia de Residencia",
                "oficina_id": self.oficina2.pk,
                "activo": "true",
            },
        )
        self.assertRedirects(response, self.url)
        self.assertEqual(
            Tramite.objects.filter(nombre="Constancia de Residencia").count(),
            2,
        )

    def test_administrador_post_nombre_vacio_rechazado(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            self.url,
            {
                "nombre": "   ",
                "oficina_id": self.oficina1.pk,
                "activo": "true",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "El nombre debe tener contenido")

    def test_administrador_post_oficina_invalida_rechazado(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            self.url,
            {
                "nombre": "Trámite Sin Oficina",
                "oficina_id": 999999,
                "activo": "true",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Revisa los campos del formulario")
