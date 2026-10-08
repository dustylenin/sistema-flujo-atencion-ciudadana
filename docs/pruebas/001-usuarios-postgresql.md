# 001 — Validación de usuarios en PostgreSQL

Fecha del registro: 8 de octubre de 2026.

La migración inicial de usuarios del commit `ca6836e` estaba revisada y su aplicación autorizada. Este documento registra la aplicación y las comprobaciones realizadas en PostgreSQL local. La elaboración del registro no repite las pruebas ni modifica la base de datos.

## Entorno utilizado

- Linux Mint 22.3; Python 3.12.3 del entorno virtual `.venv`.
- Django 5.2.17, Psycopg 3.3.6 y python-dotenv 1.2.4, según las dependencias fijadas del proyecto.
- PostgreSQL local 16.15, versión consignada en el README del entorno verificado.
- Conexión confirmada desde Django: base `atencion_ciudadana`, usuario `atencion_app`, servidor `127.0.0.1`, puerto `5432`; `SELECT 1` devolvió `1`.
- Configuración confirmada: `AUTH_USER_MODEL="usuarios.Usuario"`; `get_user_model()` devolvió `Usuario`, con `UsuarioManager`.
- Estado previo: Git limpio en `main`, commit `ca6836e`; base sin tablas ni migraciones aplicadas. El estado y el plan coincidían con la preparación revisada.

No se registran contraseñas, hashes ni la clave de Django.

## Migraciones aplicadas

Antes de la aplicación se comprobaron el historial y el plan:

```bash
.venv/bin/python manage.py showmigrations
.venv/bin/python manage.py migrate --plan
```

Todas las migraciones figuraban sin aplicar y el plan contenía 16 operaciones de migración hacia adelante. Se ejecutó:

```bash
.venv/bin/python manage.py migrate
```

Las siguientes 16 migraciones terminaron con resultado `OK`:

| Aplicación | Migraciones |
| --- | --- |
| `contenttypes` | `0001_initial`, `0002_remove_content_type_name` |
| `auth` | `0001_initial`, `0002_alter_permission_name_max_length`, `0003_alter_user_email_max_length`, `0004_alter_user_username_opts`, `0005_alter_user_last_login_null`, `0006_require_contenttypes_0002`, `0007_alter_validators_add_error_messages`, `0008_alter_user_username_max_length`, `0009_alter_user_last_name_max_length`, `0010_alter_group_name_max_length`, `0011_update_proxy_permissions`, `0012_alter_user_first_name_max_length` |
| `sessions` | `0001_initial` |
| `usuarios` | `0001_initial` |

No se utilizó `--fake`, no se borraron tablas y no se reinició la base.

## Comprobaciones posteriores

| Comando | Resultado observado |
| --- | --- |
| `.venv/bin/python manage.py check` | `System check identified no issues (0 silenced).` |
| `.venv/bin/python manage.py showmigrations` | Las 16 migraciones marcadas con `[X]`. |
| `.venv/bin/python manage.py migrate --plan` | `No planned migration operations.` |
| `.venv/bin/python manage.py makemigrations --check --dry-run` | `No changes detected`. |

Los cuatro comandos terminaron correctamente. No quedaron migraciones ni cambios de modelos pendientes.

La inspección de los catálogos de PostgreSQL, mediante la conexión de Django, confirmó:

- Existencia de `usuarios_usuario` y ausencia de `auth_user`, correspondiente al modelo de usuario sustituido.
- Columnas `username` y `rol` con `NOT NULL`.
- Restricción única validada `usuarios_usuario_username_key`: `UNIQUE (username)`.
- Restricción validada `usuarios_usuario_rol_valido`: `CHECK` que admite exactamente `ADMINISTRADOR`, `RECEPCION` y `OPERADOR`.
- Modelo personalizado `usuarios.Usuario` activo mediante `get_user_model()`.

## Pruebas puntuales de lectura y escritura

Se ejecutó un script mediante `.venv/bin/python manage.py shell`, sin añadir archivos de pruebas. Se usaron nombres ficticios con un prefijo aleatorio y se dirigieron las modificaciones únicamente a los registros creados durante la prueba.

| Caso | Resultado observado |
| --- | --- |
| Crear mediante `create_user()` y recuperar mediante el manager un usuario `ADMINISTRADOR`. | Identificador y rol coincidentes; cuenta inicialmente activa. |
| Crear y recuperar del mismo modo un usuario `RECEPCION`. | Identificador y rol coincidentes; cuenta inicialmente activa. |
| Crear y recuperar del mismo modo un usuario `OPERADOR`. | Identificador y rol coincidentes; cuenta inicialmente activa. |
| Ejecutar `check_password` para cada uno de los tres usuarios. | La contraseña utilizada al crear la cuenta fue aceptada y otra contraseña fue rechazada; el valor almacenado era distinto del texto original. |
| Desactivar el usuario ficticio `OPERADOR` mediante `is_active=False`. | La consulta posterior recuperó el mismo registro, username y rol, con `is_active=False`; seguían existiendo los tres usuarios ficticios. |

Estas comprobaciones verificaron lectura y escritura reales del modelo en PostgreSQL dentro de la transacción de prueba.

## Rechazos de integridad en PostgreSQL

Los casos siguientes produjeron `IntegrityError` originado en PostgreSQL, con el SQLSTATE y la restricción o columna indicados:

| Dato rechazado | Operaciones probadas | Restricción o columna | SQLSTATE |
| --- | --- | --- | --- |
| `username` duplicado | `create_user()` y `QuerySet.update(username=...)` sobre otro usuario ficticio. | `usuarios_usuario_username_key` | `23505` |
| Rol inválido (`INVALIDO`) | Inserción mediante `bulk_create()` y `QuerySet.update(rol=...)`. | `usuarios_usuario_rol_valido` (`CHECK`) | `23514` |
| Rol vacío (`""`) | Inserción mediante `bulk_create()` y `QuerySet.update(rol=...)`. | `usuarios_usuario_rol_valido` (`CHECK`) | `23514` |
| Rol `NULL` (`None`) | Inserción mediante `bulk_create()` y `QuerySet.update(rol=...)`. | `NOT NULL` de la columna `rol` | `23502` |

`bulk_create()` y `update()` omiten la validación de `save()`, por lo que estos rechazos comprobaron las restricciones del servidor. Después de los intentos de modificar el rol, el usuario ficticio conservó su valor válido `ADMINISTRADOR`.

## Transacciones y estado final

Todas las operaciones con usuarios ficticios se ejecutaron dentro de un bloque externo `transaction.atomic()`. Un bloque `finally` marcó siempre esa transacción para rollback mediante `transaction.set_rollback(True)`.

Cada error de integridad esperado se provocó dentro de un bloque `atomic` interno y se capturó fuera de él, permitiendo revertir su savepoint y continuar usando la transacción externa. También se comprobó que la conexión no quedara marcada como necesitada de rollback después de cada captura.

Antes de las pruebas había **cero usuarios**. Después del rollback, las consultas por el prefijo y los identificadores de los usuarios ficticios devolvieron **cero registros**, y el total de usuarios siguió siendo **cero**. No se creó ninguna cuenta permanente ni se modificaron registros preexistentes.

La aplicación de migraciones y su validación dejaron Git limpio en `ca6836e`, sin cambios de código, migraciones, permisos de PostgreSQL ni reglas de negocio.

## Alcance y pendientes

Fueron **pruebas puntuales**; no se añadió una suite automática de integración. Las pruebas existentes con `SimpleTestCase` siguen siendo pruebas sin acceso a la base de datos.

No se probó el inicio de sesión, el flujo de acceso mediante pantallas ni la fortaleza de las contraseñas. `check_password` solo comprobó la correspondencia entre la contraseña suministrada y el valor almacenado.

Siguen pendientes:

- Acceso mediante pantallas y flujos de autenticación de la aplicación.
- Permisos funcionales y autorización de acciones según rol.
- Oficinas y asignaciones de operadores a oficinas.

Las reglas aprobadas continúan en [acuerdos vigentes](../acuerdos-vigentes.md) y en la [decisión de usuarios y asignaciones](../decisiones/001-usuarios-y-asignaciones.md).
