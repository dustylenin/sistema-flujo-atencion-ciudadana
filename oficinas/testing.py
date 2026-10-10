from django.db import connection, transaction, IntegrityError
from django.test import TestCase, TransactionTestCase


BASES_PRUEBAS_AUTORIZADAS = frozenset({
    "test_atencion_catalogos_revision",
    "test_atencion_catalogos_migraciones",
})


class CatalogosPostgreSQLMixin:
    """Estas pruebas nunca deben ejecutar casos contra la base del proyecto."""

    @classmethod
    def setUpClass(cls):
        name = connection.settings_dict["NAME"]
        if (
            connection.vendor != "postgresql"
            or name not in BASES_PRUEBAS_AUTORIZADAS
            or connection.settings_dict["TEST"]["NAME"] != name
            or connection.settings_dict["USER"] != "atencion_test"
        ):
            raise RuntimeError(
                "Use una base exclusiva de config.settings_test o config.settings_test_migrations."
            )
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database(), current_user")
            if cursor.fetchone() != (name, "atencion_test"):
                raise RuntimeError("La conexión no apunta a la base exclusiva de pruebas.")
        super().setUpClass()

    def assert_rechazo_postgresql(self, operation, sqlstate, constraint=None):
        with self.assertRaises(IntegrityError) as captured:
            with transaction.atomic():
                operation()
        cause = captured.exception.__cause__
        self.assertEqual(cause.sqlstate, sqlstate)
        if constraint:
            self.assertEqual(cause.diag.constraint_name, constraint)


class CatalogosPostgreSQLTestCase(CatalogosPostgreSQLMixin, TestCase):
    pass


class CatalogosPostgreSQLTransactionTestCase(CatalogosPostgreSQLMixin, TransactionTestCase):
    pass
