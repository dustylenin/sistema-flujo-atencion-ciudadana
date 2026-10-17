from django.urls import reverse

from tramites.models import Tramite
from usuarios.models import Usuario

from .models import AsignacionOperadorOficina, Oficina
from .services import crear_asignacion
from .testing import CatalogosPostgreSQLTestCase


class AdminOficinasViewTests(CatalogosPostgreSQLTestCase):
    def setUp(self):
        super().setUp()
        self.admin = Usuario.objects.create_user(
            username="admin_user",
            password="admin_password123",
            rol=Usuario.Rol.ADMINISTRADOR,
        )
        self.operador = Usuario.objects.create_user(
            username="operador_user",
            password="operador_password123",
            rol=Usuario.Rol.OPERADOR,
        )
        self.recepcion = Usuario.objects.create_user(
            username="recepcion_user",
            password="recepcion_password123",
            rol=Usuario.Rol.RECEPCION,
        )
        self.url = reverse("oficinas:gestion_oficinas")

    def test_url_resolucion(self):
        self.assertEqual(self.url, "/administracion/oficinas/")
        self.assertEqual(reverse("usuarios:admin_oficinas"), "/administracion/oficinas/")

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

    def test_administrador_get_lista_oficinas_y_elementos_ui(self):
        oficina1 = Oficina.objects.create(nombre="Registro Civil", activo=True)
        oficina2 = Oficina.objects.create(nombre="Desarrollo Urbano", activo=False)

        Tramite.objects.create(nombre="Acta de Nacimiento", oficina=oficina1, activo=True)
        Tramite.objects.create(nombre="Acta de Matrimonio", oficina=oficina1, activo=True)

        crear_asignacion(actor=self.admin, operador_id=self.operador.pk, oficina_id=oficina1.pk)

        self.client.force_login(self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        self.assertIn("oficinas", response.context)
        oficinas_en_contexto = list(response.context["oficinas"])
        self.assertIn(oficina1, oficinas_en_contexto)
        self.assertIn(oficina2, oficinas_en_contexto)

        contenido = response.content.decode("utf-8")

        # Estructura visual de tarjeta y tabla
        self.assertIn('class="tarjeta"', contenido)
        self.assertIn("<th scope=\"col\">Oficina</th>", contenido)
        self.assertIn("<th scope=\"col\">Estado</th>", contenido)
        self.assertIn("<th scope=\"col\">Trámites compatibles</th>", contenido)
        self.assertIn("<th scope=\"col\">Operadores</th>", contenido)
        self.assertIn("<th scope=\"col\">Acciones</th>", contenido)

        # Botones requeridos
        self.assertIn('class="boton primario"', contenido)
        self.assertIn('class="boton secundario"', contenido)
        self.assertIn("Nueva oficina", contenido)
        self.assertIn("Editar", contenido)

        # Dialog modal HTML5 nativo
        self.assertIn("<dialog", contenido)
        self.assertIn('id="dialog-nueva-oficina"', contenido)

        # Enlaces requeridos en barra lateral
        for link in (
            "Resumen",
            "Usuarios",
            "Oficinas",
            "Trámites",
            "Asignaciones",
            "Historial e incidencias",
            "Registro de actividad",
        ):
            self.assertIn(link, contenido)

        # Datos de las oficinas
        self.assertIn("Registro Civil", contenido)
        self.assertIn("Desarrollo Urbano", contenido)
        self.assertIn("Activa", contenido)
        self.assertIn("Inactiva", contenido)

    def test_administrador_post_crear_oficina_exitosa(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            self.url,
            {
                "nombre": "Catastro y Predial",
                "descripcion": "Gestión de predios y pagos",
                "activo": "true",
            },
        )
        self.assertRedirects(response, self.url)

        oficina = Oficina.objects.filter(nombre="Catastro y Predial").first()
        self.assertIsNotNone(oficina)
        self.assertTrue(oficina.activo)

        # Verificación del mensaje flash tras redirección
        follow_response = self.client.get(self.url)
        self.assertContains(follow_response, "Catastro y Predial")

    def test_administrador_post_crear_oficina_inactiva(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            self.url,
            {
                "nombre": "Módulo Temporal",
                "descripcion": "Módulo temporal cerrado",
                "activo": "false",
            },
        )
        self.assertRedirects(response, self.url)

        oficina = Oficina.objects.filter(nombre="Módulo Temporal").first()
        self.assertIsNotNone(oficina)
        self.assertFalse(oficina.activo)

    def test_administrador_post_nombre_duplicado_rechazado(self):
        Oficina.objects.create(nombre="Medio Ambiente", activo=True)
        self.client.force_login(self.admin)

        # Intentar crear con el mismo nombre en minúsculas y espacios
        response = self.client.post(
            self.url,
            {
                "nombre": "  medio ambiente  ",
                "descripcion": "Duplicado",
                "activo": "true",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ya existe una oficina con este nombre")
        self.assertEqual(Oficina.objects.filter(nombre__iexact="medio ambiente").count(), 1)

    def test_administrador_post_nombre_vacio_rechazado(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            self.url,
            {
                "nombre": "   ",
                "descripcion": "Sin nombre válido",
                "activo": "true",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "El nombre debe tener contenido")
