# 004 — Aplicación de migraciones de catálogos en PostgreSQL local

Fecha de ejecución y registro: 10 de octubre de 2026.

Se aplicaron las migraciones revisadas de oficinas y trámites a la base local del proyecto, después de su [verificación con migraciones reales en pruebas](003-migraciones-postgresql.md). Este registro documenta la ejecución ya completada; su elaboración no repite comandos de Django ni modifica bases. Los registros anteriores se conservan intactos como evidencia de sus respectivas etapas.

## Comprobaciones previas

Se revisaron los [acuerdos vigentes](../acuerdos-vigentes.md), README y el registro 003. Git estaba limpio, en `main`, sincronizada con `origin/main`.

Una conexión real con **`config.settings`** confirmó:

- Base: **`atencion_ciudadana`**.
- Usuario conectado y usuario de sesión: **`atencion_app`**.

La consulta de identidad utilizó `current_database()`, `current_user` y `session_user`, sin mostrar contraseñas ni el contenido de `.env`. La inspección previa se realizó con la conexión en modo de solo lectura. El acceso al PostgreSQL local requirió ejecución fuera del sandbox.

Desde la raíz del repositorio se ejecutaron:

```bash
.venv/bin/python -B manage.py check --settings=config.settings
.venv/bin/python -B manage.py makemigrations --check --dry-run --settings=config.settings
.venv/bin/python -B manage.py showmigrations --settings=config.settings
.venv/bin/python -B manage.py migrate --plan --settings=config.settings
```

Todas las comprobaciones pasaron: `check` informó `System check identified no issues (0 silenced).` y `makemigrations --check --dry-run` informó `No changes detected`.

El historial contenía exactamente **16 migraciones aplicadas**: doce de `auth`, dos de `contenttypes`, una de `sessions` y una de `usuarios`. `showmigrations` marcó esas 16 con `[X]` y únicamente las dos siguientes con `[ ]`. `MigrationExecutor` confirmó la consistencia del historial y este plan exacto, sin operaciones inversas:

| Migración pendiente | Operación |
| --- | --- |
| `oficinas.0001_initial` | `Create model Oficina`. |
| `tramites.0001_initial` | `Create model Tramite`; depende de `oficinas.0001_initial`. |

La consulta de `to_regclass` confirmó que `oficinas_oficina` y `tramites_tramite` todavía no existían. Se continuó al coincidir todas las condiciones previas solicitadas.

## Aplicación ejecutada

```bash
.venv/bin/python -B manage.py migrate --settings=config.settings --noinput
```

La salida confirmó:

```text
Applying oficinas.0001_initial... OK
Applying tramites.0001_initial... OK
```

Se aplicaron los archivos reales, sin `--fake` ni `--fake-initial`.

## Comprobaciones posteriores

Con la misma configuración se ejecutaron:

```bash
.venv/bin/python -B manage.py showmigrations --settings=config.settings
.venv/bin/python -B manage.py migrate --plan --settings=config.settings
.venv/bin/python -B manage.py check --settings=config.settings
```

- `showmigrations`: **18 migraciones aplicadas**, todas marcadas con `[X]`.
- `migrate --plan`: `No planned migration operations.`
- `check`: `System check identified no issues (0 silenced).`
- `MigrationExecutor`: historial consistente, 18 migraciones registradas coincidentes con los archivos y plan vacío.

## Inspección de lectura del esquema y los datos

Una nueva conexión de solo lectura volvió a confirmar `atencion_ciudadana` y `atencion_app`. Se contrastaron las dos tablas con el estado final de las migraciones mediante introspección y consultas a `information_schema.columns`, `pg_constraint` y `pg_index`.

| Tabla | Columnas verificadas | Filas finales |
| --- | --- | --- |
| `oficinas_oficina` | `id` bigint con identidad `BY DEFAULT`, `nombre` varchar(150), `activo` boolean; todas `NOT NULL`. | **0** |
| `tramites_tramite` | Las mismas columnas y `oficina_id` bigint, también `NOT NULL`. | **0** |

La inspección fue satisfactoria: columnas, tipos, longitud del nombre, nulabilidad e identidades corresponden a las migraciones revisadas. Se verificaron **cinco restricciones en `pg_constraint`**, todas validadas:

- Claves primarias de ambas tablas.
- `oficinas_oficina_nombre_con_contenido` y `tramites_tramite_nombre_con_contenido`, con comprobación de contenido mediante la expresión regular `\S`.
- Clave foránea de `tramites_tramite.oficina_id` a `oficinas_oficina.id`, diferible e inicialmente diferida.

Se verificaron **cinco índices**, todos válidos, preparados y sin condición parcial:

- Índices de las claves primarias de ambas tablas.
- `oficinas_oficina_nombre_unico`: único sobre `lower(TRIM(BOTH FROM nombre))`.
- `tramites_tramite_nombre_por_oficina_unico`: único sobre el nombre normalizado y `oficina_id`.
- Índice de `tramites_tramite.oficina_id`.

Las dos tablas de catálogos quedaron con **cero filas**. No se ejecutaron pruebas sobre esta base ni se crearon usuarios o datos de ejemplo. No se cambiaron permisos, código, modelos ni archivos de migración, ni se incluyeron secretos. Git continuó limpio y sincronizado con `origin/main` al finalizar la ejecución documentada.

## Estado y pendientes

**Las migraciones de oficinas y trámites ya están aplicadas y verificadas en `atencion_ciudadana`.** Se conserva el alcance de la [decisión 002](../decisiones/002-oficinas-tramites-y-asignaciones.md): asignaciones, folios, pantallas, permisos funcionales, historial de actividad y protecciones que dependen de esas partes siguen pendientes.

La inspección de esquema no equivale a ejecutar pruebas funcionales sobre la base local. Las protecciones de borrado y oficina fija por las vías admitidas del ORM mantienen los límites documentados ante SQL directo, APIs internas y deserializadores; no se implementaron disparadores ni nuevas garantías de negocio en esta etapa.
