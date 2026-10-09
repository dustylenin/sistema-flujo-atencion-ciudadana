from django.db import connection, transaction, IntegrityError
from django.test import TestCase, TransactionTestCase


class CatalogosPostgreSQLMixin:
    """Estas pruebas nunca deben ejecutar casos contra la base del proyecto."""

    @classmethod
    def setUpClass(cls):
        name = connection.settings_dict["NAME"]
        if (
            connection.vendor != "postgresql"
            or name != "test_atencion_catalogos_revision"
            or connection.settings_dict["USER"] != "atencion_test"
        ):
            raise RuntimeError("Use la base exclusiva de config.settings_test.")
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
