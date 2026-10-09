# 002 — Validación de oficinas y trámites en PostgreSQL

Fecha del registro: 8 de octubre de 2026.

Se implementó y verificó la base de oficinas y trámites conforme a los [acuerdos vigentes](../acuerdos-vigentes.md) y a la [decisión 002](../decisiones/002-oficinas-tramites-y-asignaciones.md). Este documento registra la ejecución ya completada; su elaboración no repite pruebas ni modifica código o bases de datos.

## Entorno y aislamiento

- Python 3.12.3 del entorno virtual `.venv`; Django 5.2.17 y Psycopg 3.3.6.
- PostgreSQL local 16.15, versión consignada en el entorno del proyecto.
- Base exclusiva `test_atencion_catalogos_revision`, preparada previamente por el usuario, con `atencion_test` como usuario y propietario, en `127.0.0.1:5432`.
- Se confirmó la identidad real mediante `current_database()`, `current_user` y el propietario de la base. La consulta de `pg_roles` confirmó `rolsuper=False`, `rolcreatedb=False` y `rolcreaterole=False`.
- `config.settings_test` usa el mismo nombre exclusivo en `NAME` y `TEST.NAME`. Rechaza otros nombres, una coincidencia con la base configurada del proyecto, usuarios distintos de `atencion_test` y una contraseña de pruebas vacía. Lee `TEST_POSTGRES_PASSWORD` sin alternativa a las credenciales de la aplicación.
- Las variables locales de pruebas que faltaban se completaron sin modificar las variables normales, la contraseña existente ni los permisos de `.env`. Los secretos permanecen en el archivo local ignorado por Git y no se incluyen aquí.

La ejecución se realizó fuera del sandbox, necesario para acceder al servicio local de PostgreSQL. No se modificaron `atencion_ciudadana` ni los permisos de `atencion_app`.

## Comportamiento implementado

`oficinas` y `tramites` están registradas en `INSTALLED_APPS`.

| Modelo | Campos y relaciones |
| --- | --- |
| `Oficina` | Identificador `BigAutoField`, nombre obligatorio de hasta 150 caracteres y `activo` booleano, inicialmente `True`. |
| `Tramite` | Los mismos campos y una oficina obligatoria mediante clave foránea con `PROTECT`; relación inversa `Oficina.tramites`. |

Se conserva la grafía del nombre almacenado. La comparación de unicidad usa `Lower(Trim(nombre))`: oficinas únicas globalmente y trámites únicos dentro de su oficina, incluyendo activos e inactivos. Un nombre de trámite puede repetirse en otras oficinas. El guardado rechaza nombres vacíos o compuestos solo por espacios; un `CHECK` exige contenido en PostgreSQL.

La oficina del trámite se comprueba al guardar mediante una consulta con bloqueo transaccional de la fila existente. Si la PK no existe, el guardado normal exige `INSERT`, evitando actualizar una fila creada después de la comprobación. `force_update` y un `update_fields` no vacío rechazan una PK ausente, conservando la operación solicitada; un `update_fields` vacío no escribe.

El borrado individual y por `QuerySet` se rechaza. `bulk_create()` y `bulk_update()` no están admitidos, incluidos intentos de actualización por conflicto. `update()` solo admite `activo=True` o `activo=False` como booleanos literales; rechaza otras columnas y expresiones. Las variantes asíncronas conservan estos bloqueos. Desactivar y reactivar conserva los registros y no cambia automáticamente otras entidades.

## Comando ejecutado y resultado

Desde la raíz del repositorio se ejecutó exactamente:

```bash
.venv/bin/python -B manage.py test usuarios config.tests oficinas tramites --settings=config.settings_test --keepdb --parallel 1 --noinput --verbosity 2
```

Resultado: **37 pruebas satisfactorias, sin errores ni fallos**, con salida `Ran 37 tests` y `OK`. Las comprobaciones de Django incluidas en el comando mostraron `System check identified no issues (0 silenced).`

| Grupo | Tipo | Cantidad | Resultado |
| --- | --- | --- | --- |
| `OficinaPostgreSQLTests` | PostgreSQL, `TestCase` | 6 | Satisfactorias. |
| `TramitePostgreSQLTests` | PostgreSQL, `TestCase` | 12 | Satisfactorias. |
| `TramiteConcurrenciaPostgreSQLTests` | PostgreSQL, `TransactionTestCase` | 1 | Satisfactoria. |
| `usuarios.tests.UsuarioTests` | Sin base, `SimpleTestCase` | 8 | Satisfactorias. |
| `config.tests.ConfiguracionPruebasTests` | Sin base, `SimpleTestCase` | 4 | Satisfactorias. |
| `CatalogosSinBaseTests` | Sin base, `SimpleTestCase` | 6 | Satisfactorias. |
| **Total** | **19 con PostgreSQL y 18 sin base** | **37** | **Todas satisfactorias.** |

## Casos y resultados observados

| Caso | Resultado |
| --- | --- |
| Crear y recuperar oficinas y trámites. | Se conservaron nombres, estado y oficina correspondientes. |
| Unicidad global de oficinas, incluyendo inactivas y variantes de mayúsculas y espacios exteriores. | PostgreSQL rechazó los duplicados; se conservó un único registro. `full_clean()` también detectó el conflicto probado. |
| Unicidad de trámites dentro de la oficina, incluyendo inactivos y las mismas variantes. | PostgreSQL rechazó los duplicados en la misma oficina y permitió el nombre equivalente en otra. |
| Nombres obligatorios, con contenido y longitud admitida. | Las validaciones rechazaron `None`, nombres vacíos, solo espacios, tabulación/salto de línea y más de 150 caracteres antes de guardar. Los casos SQL de contenido se rechazaron en PostgreSQL. |
| Oficina obligatoria y existente. | El guardado sin oficina se rechazó; PostgreSQL rechazó la referencia inexistente probada. |
| Cambio de oficina al guardar. | Se rechazó mediante `oficina`, `oficina_id`, `update_fields`, instancias reconstruidas y diferidas, y `update_or_create()`. La recarga confirmó la oficina original y el estado conservado. |
| `force_insert`, `force_update` y `update_fields`. | La inserción y actualización explícitas válidas persistieron; la PK repetida se rechazó y las actualizaciones explícitas de una PK ausente no crearon filas. Las opciones incompatibles o campos inválidos se rechazaron; el conjunto vacío no escribió. |
| Desactivación y reactivación. | Persistieron sobre los mismos registros; recargas y consultas comprobaron la conservación de oficina y trámites sin cambios automáticos en otros registros. |
| Borrado individual y por `QuerySet`, con y sin referencias. | Se rechazó y se conservaron los registros y referencias comprobados. |
| Operaciones masivas que omitirían validaciones. | Se rechazaron los intentos de cambio de oficina, `bulk_update()` y `bulk_create()` con actualización por conflicto; la oficina persistida permaneció intacta. |
| Variantes asíncronas de borrado y escritura masiva no admitida. | Se rechazaron sin consultas a la base. Esta cobertura no equivale a probar todas las operaciones asíncronas válidas con persistencia. |
| Aislamiento de configuración de pruebas. | Se aceptaron los nombres exclusivos y `MIGRATE=False`; se rechazaron bases o usuarios distintos y la contraseña de pruebas vacía, sin recurrir a la del proyecto. |
| Cambio de oficina mediante SQL directo, solo en la base de pruebas. | La modificación fue posible: el caso confirma el límite de protección del ORM, sin afirmar inmutabilidad garantizada por PostgreSQL. |

### Regresión con dos conexiones reales

`test_pk_creada_tras_consulta_ausente_no_se_sobrescribe` utilizó `TransactionTestCase` y dos conexiones reales, con identificadores de proceso PostgreSQL distintos comprobados mediante `pg_backend_pid()`.

La conexión principal consultó una PK ausente con `SELECT ... FOR UPDATE`. Después de ejecutar esa consulta y antes de continuar el guardado, un `execute_wrapper` coordinó una inserción real desde otro hilo y otra conexión. Esa conexión creó y confirmó un trámite con la misma PK y otra oficina, y se cerró al terminar. No se simularon consultas ni resultados.

El guardado principal exigió `INSERT` y PostgreSQL lo rechazó por PK duplicada (`23505`, `tramites_tramite_pkey`). La consulta y recarga posteriores confirmaron que el registro de la segunda conexión conservó nombre `Original`, su oficina y `activo=False`; seguía habiendo un único trámite y las dos oficinas. La prueba pasó.

### Rechazos de integridad comprobados

| Caso | Restricción o columna | SQLSTATE |
| --- | --- | --- |
| Nombre de oficina duplicado. | `oficinas_oficina_nombre_unico` | `23505` |
| Nombre de trámite duplicado dentro de su oficina. | `tramites_tramite_nombre_por_oficina_unico` | `23505` |
| PK de trámite duplicada, incluida la regresión entre conexiones. | `tramites_tramite_pkey` | `23505` |
| Nombre de oficina vacío o solo espacios. | `oficinas_oficina_nombre_con_contenido` | `23514` |
| Nombre de trámite solo espacios. | `tramites_tramite_nombre_con_contenido` | `23514` |
| Nombre de oficina `NULL`. | `NOT NULL` de `nombre` | `23502` |
| Oficina inexistente en el trámite. | Clave foránea; se forzó la evaluación de la restricción diferida dentro del savepoint. | `23503` |

Los errores esperados de PostgreSQL se provocaron dentro de bloques `atomic` y se capturaron fuera de ellos, comprobando SQLSTATE y, cuando correspondía, el nombre de la restricción. Las pruebas `TestCase` usan transacciones revertidas; la regresión `TransactionTestCase` permite confirmar la inserción de la segunda conexión y el ejecutor limpia sus datos al terminar.

## Esquema de pruebas y límites

`NAME` y `TEST.NAME` fueron `test_atencion_catalogos_revision`. `--keepdb` reutilizó y conservó esa base; `--parallel 1` evitó bases adicionales. El ejecutor informó que sincronizó aplicaciones sin migraciones, creó las tablas de infraestructura, usuarios, oficinas y trámites y no tenía migraciones que aplicar.

**`TEST.MIGRATE=False`: se verificaron los modelos y sus restricciones en PostgreSQL de pruebas, no los archivos de migración del proyecto.** No se generaron ni aplicaron migraciones de oficinas o trámites y no se preparó su esquema en `atencion_ciudadana`.

Las restricciones de unicidad, contenido y referencia se comprobaron en PostgreSQL. La prohibición de borrado y la oficina fija dependen de las vías públicas admitidas del ORM: SQL directo, APIs internas y deserializadores pueden omitirlas. `PROTECT` evita cascadas en las relaciones, pero no constituye por sí solo una prohibición general de borrar filas sin referencias. No hay disparadores SQL aprobados ni una garantía de inmutabilidad o conservación frente a escrituras directas.

Estas pruebas no verifican pantallas, inicio de sesión, fortaleza de contraseñas, permisos funcionales, folios ni historial de actividad. Los nombres, oficinas y trámites utilizados son datos de pruebas, no un catálogo permanente de la base del proyecto.

## Pendientes

- Generar, revisar, verificar y aplicar las migraciones del proyecto para oficinas y trámites en una etapa posterior autorizada.
- Asignaciones de operadores, creación y reactivación con las condiciones aprobadas, y conservación de asignaciones históricas.
- Folios y sus protecciones reales al retirar asignaciones y cambiar una cuenta de rol `OPERADOR`. Las operaciones dependientes no deben habilitarse antes de implementar y verificar los bloqueos.
- Pantallas, autenticación y autorización funcional; edición funcional de nombres.
- Historial de actividad: `activo` representa el estado actual y no sustituye la trazabilidad de cambios.

La documentación conserva los acuerdos y no añade efectos automáticos ni reglas nuevas de negocio.
