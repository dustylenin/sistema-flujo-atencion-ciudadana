"""Bloqueo provisional del cambio de rol, sin simular el modelo de folios."""

from concurrent.futures import ThreadPoolExecutor

from asgiref.sync import async_to_sync
from django.core.exceptions import ValidationError
from django.db import connection, connections, DatabaseError, models, NotSupportedError, transaction
from django.test import SimpleTestCase

from oficinas.testing import CatalogosPostgreSQLTestCase, CatalogosPostgreSQLTransactionTestCase
from .models import Usuario


class UsuariosEscriturasSinBaseTests(SimpleTestCase):
    def test_managers_y_variantes_asincronas_rechazan_actualizacion_masiva_rol(self):
        for manager in (Usuario.objects, Usuario._base_manager, Usuario._default_manager):
            for operation in (
                lambda: manager.update(rol="ADMINISTRADOR"),
                lambda: manager.bulk_update([], ["rol"]),
                lambda: manager.bulk_create([], update_conflicts=True, update_fields=["rol"], unique_fields=["pk"]),
                lambda: async_to_sync(manager.aupdate)(rol="ADMINISTRADOR"),
                lambda: async_to_sync(manager.abulk_update)([], ["rol"]),
                lambda: async_to_sync(manager.abulk_create)([], update_conflicts=True, update_fields=["rol"], unique_fields=["pk"]),
            ):
                with self.assertRaises(NotSupportedError):
                    operation()

    def test_creacion_asincrona_exige_rol_explicito_valido(self):
        for method in (Usuario.objects.acreate_user, Usuario.objects.acreate_superuser):
            with self.assertRaises(TypeError):
                async_to_sync(method)(username="nuevo")
            for role in (None, "", "OTRO"):
                with self.assertRaises(ValidationError):
                    async_to_sync(method)(username="nuevo", rol=role)

    def test_opciones_de_guardado_sin_escritura(self):
        user = Usuario(pk=1, username="nuevo", rol=Usuario.Rol.OPERADOR)
        for options in ({}, {"force_insert": True}, {"force_update": True}):
            self.assertIsNone(user.save(update_fields=[], **options))
        for options in (
            {"force_insert": True, "force_update": True},
            {"force_insert": True, "update_fields": ["rol"]},
            {"update_fields": ["id"]}, {"update_fields": ["inexistente"]},
        ):
            with self.assertRaises(ValueError):
                user.save(**options)


class UsuarioProteccionesPostgreSQLTests(CatalogosPostgreSQLTestCase):
    def setUp(self):
        self.operador = Usuario.objects.create_user(username="operador", rol=Usuario.Rol.OPERADOR)

    def test_cambio_efectivo_bloqueado_incluso_sin_asignaciones(self):
        for role in (Usuario.Rol.RECEPCION, Usuario.Rol.ADMINISTRADOR):
            for options in ({}, {"force_update": True}, {"update_fields": ["rol"]}):
                with self.subTest(role=role, options=options):
                    self.operador.rol = role
                    with self.assertRaises(ValidationError):
                        self.operador.save(**options)
                    self.assertEqual(Usuario.objects.get(pk=self.operador.pk).rol, Usuario.Rol.OPERADOR)

    def test_instancia_reconstruida_y_diferida_no_omiten_bloqueo(self):
        rebuilt = Usuario(pk=self.operador.pk, username="reconstruida", rol=Usuario.Rol.ADMINISTRADOR)
        with self.assertRaises(ValidationError):
            rebuilt.save()
        deferred = Usuario.objects.only("id", "username").get(pk=self.operador.pk)
        deferred.rol = Usuario.Rol.RECEPCION
        with self.assertRaises(ValidationError):
            deferred.save()
        self.assertEqual(Usuario.objects.get(pk=self.operador.pk).username, "operador")

    def test_update_fields_y_diferidos_conservan_password_y_actividad(self):
        self.operador.rol = Usuario.Rol.ADMINISTRADOR  # Solo en memoria.
        self.operador.is_active = False
        self.operador.set_password("clave-prueba")
        self.operador.save(update_fields=["is_active", "password"])
        self.operador.refresh_from_db()
        self.assertEqual(self.operador.rol, Usuario.Rol.OPERADOR)
        self.assertFalse(self.operador.is_active)
        self.assertTrue(self.operador.check_password("clave-prueba"))
        deferred = Usuario.objects.only("id", "is_active").get(pk=self.operador.pk)
        deferred.is_active = True
        deferred.save()
        self.operador.refresh_from_db()
        self.assertTrue(self.operador.is_active)
        self.assertTrue(self.operador.check_password("clave-prueba"))
        self.assertEqual(self.operador.rol, Usuario.Rol.OPERADOR)

    def test_queryset_conserva_escrituras_de_actividad_y_password(self):
        Usuario.objects.filter(pk=self.operador.pk).update(is_active=False)
        self.operador.refresh_from_db()
        self.assertFalse(self.operador.is_active)
        self.operador.is_active = True
        Usuario.objects.bulk_update([self.operador], ["is_active"])
        self.operador.refresh_from_db()
        self.assertTrue(self.operador.is_active)

    def test_create_y_metodos_mixtos_no_sobrescriben_rol(self):
        for operation in (
            lambda: Usuario.objects.create(pk=self.operador.pk, username="nuevo", rol="ADMINISTRADOR"),
            lambda: Usuario.objects.create_user(id=self.operador.pk, username="nuevo", rol="ADMINISTRADOR"),
            lambda: Usuario.objects.create_superuser(id=self.operador.pk, username="nuevo", rol="ADMINISTRADOR"),
            lambda: Usuario.objects.update_or_create(pk=self.operador.pk, defaults={"rol": "ADMINISTRADOR"}),
        ):
            with self.assertRaises((ValidationError, DatabaseError)):
                with transaction.atomic():
                    operation()
        saved, created = Usuario.objects.get_or_create(pk=self.operador.pk, defaults={"rol": "ADMINISTRADOR"})
        self.assertFalse(created)
        self.assertEqual(saved.rol, Usuario.Rol.OPERADOR)
        saved, created = Usuario.objects.update_or_create(pk=self.operador.pk, defaults={"is_active": False})
        self.assertFalse(created)
        self.assertFalse(saved.is_active)
        self.assertEqual(saved.rol, Usuario.Rol.OPERADOR)

    def test_otros_roles_creacion_y_forzado_conservan_semantica(self):
        reception = Usuario.objects.create_user(username="recepcion", rol="RECEPCION")
        reception.rol = Usuario.Rol.ADMINISTRADOR
        reception.save(update_fields=["rol"])
        reception.refresh_from_db()
        self.assertEqual(reception.rol, Usuario.Rol.ADMINISTRADOR)
        explicit = Usuario(pk=900001, username="explicita", rol="OPERADOR")
        for options in ({"force_update": True}, {"update_fields": ["rol"]}):
            with self.assertRaises(DatabaseError):
                with transaction.atomic():
                    explicit.save(**options)
        explicit.save(force_insert=True)
        explicit.is_active = False
        explicit.save(force_update=True, update_fields=["is_active"])
        explicit.refresh_from_db()
        self.assertFalse(explicit.is_active)
        self.assert_rechazo_postgresql(lambda: explicit.save(force_insert=True), "23505")


class UsuarioConcurrenciaPostgreSQLTests(CatalogosPostgreSQLTransactionTestCase):
    def test_pk_ausente_no_sobrescribe_operador_creado_en_otra_conexion(self):
        pk = 900002
        candidate = Usuario(pk=pk, username="candidato", rol=Usuario.Rol.ADMINISTRADOR)
        self.assertFalse(Usuario.objects.filter(pk=pk).exists())
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_backend_pid()")
            main_pid = cursor.fetchone()[0]
        def insert():
            try:
                original = Usuario.objects.create_user(id=pk, username="original", rol=Usuario.Rol.OPERADOR)
                with connections["default"].cursor() as cursor:
                    cursor.execute("SELECT pg_backend_pid()")
                    return original.pk, cursor.fetchone()[0]
            finally:
                connections["default"].close()
        interleaved = False
        with ThreadPoolExecutor(max_workers=1) as pool:
            def after_missing(execute, sql, params, many, context):
                nonlocal interleaved
                result = execute(sql, params, many, context)
                if not interleaved and "FOR UPDATE" in sql.upper() and '"usuarios_usuario"' in sql and pk in (params or ()):
                    interleaved = True
                    _, other_pid = pool.submit(insert).result(timeout=10)
                    self.assertNotEqual(main_pid, other_pid)
                return result
            with connection.execute_wrapper(after_missing):
                self.assert_rechazo_postgresql(candidate.save, "23505", "usuarios_usuario_pkey")
        self.assertTrue(interleaved)
        original = Usuario.objects.get(pk=pk)
        self.assertEqual((original.username, original.rol), ("original", Usuario.Rol.OPERADOR))

    def test_variantes_asincronas_guardan_o_rechazan_transiciones(self):
        async def create_user():
            return await Usuario.objects.acreate_user(username="async", rol="OPERADOR", password="clave")
        user = async_to_sync(create_user)()
        self.assertTrue(user.check_password("clave"))
        user.rol = Usuario.Rol.ADMINISTRADOR
        with self.assertRaises(ValidationError):
            async_to_sync(user.asave)()
        async def update_role():
            return await Usuario.objects.aupdate_or_create(pk=user.pk, defaults={"rol": "RECEPCION"})
        with self.assertRaises(ValidationError):
            async_to_sync(update_role)()
        user.is_active = False
        async_to_sync(user.asave)(update_fields=["is_active"])
        user.refresh_from_db()
        self.assertEqual((user.rol, user.is_active), (Usuario.Rol.OPERADOR, False))
        async def create_superuser():
            return await Usuario.objects.acreate_superuser(username="tecnico", rol="RECEPCION")
        superuser = async_to_sync(create_superuser)()
        self.assertEqual(superuser.rol, Usuario.Rol.RECEPCION)
        self.assertTrue(superuser.is_superuser)
