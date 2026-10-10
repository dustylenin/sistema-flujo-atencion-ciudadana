# 003 — Verificación de migraciones reales en PostgreSQL

Fecha de ejecución y registro: 10 de octubre de 2026.

Este documento registra la ejecución ya completada con `config.settings_test_migrations`. Documentarla no repite pruebas ni modifica bases. La [validación anterior con `MIGRATE=False`](002-oficinas-tramites-postgresql.md) se conserva como evidencia de una etapa distinta: comprobó modelos y restricciones, pero no los archivos de migración. El estado de implementación se recoge en la [decisión 002](../decisiones/002-oficinas-tramites-y-asignaciones.md).

## Conexión previa e aislamiento

Antes de ejecutar la suite, una conexión real confirmó:

- Base: `test_atencion_catalogos_migraciones`, creada previamente por el usuario.
- Usuario conectado, usuario de sesión y propietario de la base: `atencion_test`.
- Base inicial vacía: sin relaciones de usuario, tablas de aplicación ni tabla `django_migrations`.

La comprobación consultó `current_database()`, `current_user`, `session_user`, el propietario en `pg_database` y las relaciones en `pg_class`/`pg_namespace`, con la conexión en modo de solo lectura. La condición previa exigía detenerse sin borrar si la base no estaba vacía; se cumplió la condición de vacío.

La configuración fija `NAME` y `TEST.NAME` a `test_atencion_catalogos_migraciones`, exige `atencion_test` y una contraseña local `TEST_POSTGRES_PASSWORD` no vacía, sin recurrir a las credenciales de la aplicación. `TEST.MIGRATE=True` y `MIGRATION_MODULES={}` mantienen habilitado el descubrimiento y la ejecución de los archivos reales. `TEST_POSTGRES_DB` pertenece a la configuración anterior y no redirige esta base de nombre fijo.

`config.settings_test` conserva su funcionamiento y `MIGRATE=False`. El auxiliar de PostgreSQL admite únicamente `test_atencion_catalogos_revision` y `test_atencion_catalogos_migraciones`, comprueba que `NAME` y `TEST.NAME` coincidan y verifica la identidad real de conexión. No autoriza cualquier nombre con prefijo `test_`.

El acceso al PostgreSQL local requirió ejecución fuera del sandbox. No se modificaron `atencion_ciudadana`, la primera base de pruebas ni los permisos de los usuarios. No se cambiaron modelos ni archivos de migración y no se publicaron secretos.

## Comando ejecutado y resultado

Desde la raíz del repositorio se ejecutó exactamente:

```bash
.venv/bin/python -B manage.py test usuarios config.tests oficinas tramites --settings=config.settings_test_migrations --keepdb --parallel 1 --noinput --verbosity 2
```

Resultado: **42 pruebas satisfactorias, sin errores ni fallos**, con salida `Ran 42 tests in 7.227s` y `OK`. Django informó `System check identified no issues (0 silenced).`

| Grupo | Tipo | Cantidad | Resultado |
| --- | --- | --- | --- |
| `OficinaPostgreSQLTests` | PostgreSQL, `TestCase` | 6 | Satisfactorias. |
| `TramitePostgreSQLTests` | PostgreSQL, `TestCase` | 12 | Satisfactorias. |
| `TramiteConcurrenciaPostgreSQLTests` | PostgreSQL, `TransactionTestCase` | 1 | Satisfactoria, con dos conexiones reales. |
| `usuarios.tests.UsuarioTests` | Sin base, `SimpleTestCase` | 8 | Satisfactorias. |
| `config.tests.ConfiguracionPruebasTests` | Sin base, `SimpleTestCase` | 4 | Satisfactorias; conserva la configuración anterior. |
| `config.tests.ConfiguracionMigracionesTests` | Sin base, `SimpleTestCase` | 5 | Satisfactorias; aislamiento y migraciones habilitadas. |
| `CatalogosSinBaseTests` | Sin base, `SimpleTestCase` | 6 | Satisfactorias. |
| **Total** | **19 con PostgreSQL y 23 sin base** | **42** | **Todas satisfactorias.** |

`--keepdb` reutilizó y conservó la base preparada; `--parallel 1` evitó bases adicionales. El ejecutor aplicó los archivos reales de migración, sin `--fake`, `--fake-initial` ni desactivar migraciones. La sincronización anunciada para `messages` y `staticfiles` corresponde a aplicaciones sin modelos persistentes; las aplicaciones con tablas usaron sus migraciones.

## Migraciones aplicadas

Se aplicaron y registraron **18 migraciones reales**, todas con resultado `OK`:

| Aplicación | Migraciones | Cantidad |
| --- | --- | --- |
| `auth` | `0001_initial` hasta `0012_alter_user_first_name_max_length`, inclusive. | 12 |
| `contenttypes` | `0001_initial`, `0002_remove_content_type_name`. | 2 |
| `oficinas` | `0001_initial`. | 1 |
| `sessions` | `0001_initial`. | 1 |
| `tramites` | `0001_initial`, dependiente de `oficinas.0001_initial`. | 1 |
| `usuarios` | `0001_initial`. | 1 |
| **Total** | | **18** |

Después de la suite, con la misma configuración:

```bash
.venv/bin/python -B manage.py showmigrations --settings=config.settings_test_migrations --verbosity 2
.venv/bin/python -B manage.py migrate --plan --settings=config.settings_test_migrations --verbosity 2
```

`showmigrations` mostró `[X]` en las 18 migraciones. `migrate --plan` informó `No planned migration operations.` La inspección adicional mediante `MigrationExecutor` confirmó un plan vacío y la coincidencia exacta entre las migraciones registradas y las presentes en los archivos.

## Esquema y datos finales

Una conexión de solo lectura con `config.settings_test_migrations` volvió a confirmar base, usuario, sesión y propietario. La introspección contrastó el esquema con el estado final de los archivos de migración y verificó columnas, nulabilidad, claves primarias, claves foráneas, restricciones `CHECK`, unicidades e índices esperados.

Se verificaron **11 tablas**: `auth_group`, `auth_group_permissions`, `auth_permission`, `django_content_type`, `django_migrations`, `django_session`, `oficinas_oficina`, `tramites_tramite`, `usuarios_usuario`, `usuarios_usuario_groups` y `usuarios_usuario_user_permissions`.

Se inspeccionaron **29 restricciones en `pg_constraint`**, todas validadas, y **32 índices**, todos válidos y preparados. Los índices únicos de expresión se cuentan entre los índices. Entre las comprobaciones estuvieron:

- `usuarios_usuario_rol_valido`, `NOT NULL` del rol y unicidad de `username`.
- `oficinas_oficina_nombre_con_contenido` y el índice único `oficinas_oficina_nombre_unico` sobre `lower(TRIM(BOTH FROM nombre))`.
- `tramites_tramite_nombre_con_contenido` y el índice único `tramites_tramite_nombre_por_oficina_unico` sobre el nombre normalizado y `oficina_id`.
- Clave foránea de `tramites_tramite.oficina_id` a `oficinas_oficina.id`, diferible e inicialmente diferida, e índice de `oficina_id`.
- Claves primarias, referencias e índices de las tablas de infraestructura y relaciones muchos a muchos de usuarios.

Los conteos finales fueron **cero filas** en `usuarios_usuario`, `oficinas_oficina` y `tramites_tramite`: no quedaron datos residuales de esas aplicaciones. La base conservó el esquema y el historial de las 18 migraciones.

## Alcance y pendientes

Los archivos de migración de oficinas y trámites quedaron verificados mediante su aplicación real en la segunda base exclusiva de pruebas. **Su aplicación en `atencion_ciudadana` todavía está pendiente.** Esta ejecución no prepara esos catálogos en la base de la aplicación.

Se mantienen los límites documentados de las protecciones del ORM frente a SQL directo, APIs internas y deserializadores. Esta etapa no implementa asignaciones, folios, pantallas, permisos funcionales ni historial de actividad y no amplía las reglas de negocio aprobadas.
