# 006 — Aplicación de migraciones de asignaciones en PostgreSQL local

Fecha de ejecución y registro: **10 de octubre de 2026**.

Se aplicaron las dos migraciones revisadas de asignaciones a PostgreSQL local, después de la [implementación y revisión en pruebas](005-asignaciones-postgresql.md), conforme a las decisiones [002](../decisiones/002-oficinas-tramites-y-asignaciones.md) y [003](../decisiones/003-servicios-de-asignacion-y-actividad.md). Este documento registra la ejecución ya completada; su elaboración no repite comandos de Django, no conecta ni modifica bases y conserva intactas las evidencias anteriores.

## Comprobaciones previas

Se leyeron ambas decisiones y el registro 005. Git estaba limpio, en `main`, sincronizada con `origin/main`, con HEAD `e0d3207`.

Una conexión real con **`config.settings`** confirmó **base `atencion_ciudadana` y usuario `atencion_app`**, también como usuario de sesión. La consulta utilizó `current_database()`, `current_user` y `session_user`, sin mostrar contraseñas ni el contenido de `.env`. La comprobación de identidad y la inspección del historial se realizaron en modo de solo lectura.

Desde la raíz del repositorio se ejecutaron:

```bash
.venv/bin/python -B manage.py check --settings=config.settings
.venv/bin/python -B manage.py makemigrations --check --dry-run --settings=config.settings
.venv/bin/python -B manage.py showmigrations --settings=config.settings
.venv/bin/python -B manage.py migrate --plan --settings=config.settings
.venv/bin/python -B manage.py sqlmigrate oficinas 0002 --settings=config.settings
.venv/bin/python -B manage.py sqlmigrate usuarios 0002 --settings=config.settings
```

`check` informó `System check identified no issues (0 silenced).` y la correspondencia entre modelos y migraciones informó `No changes detected`.

El historial contenía **18 migraciones aplicadas y exactamente dos pendientes**. `MigrationExecutor` confirmó su consistencia, la coincidencia de las 18 anteriores con los archivos y el siguiente plan exacto, sin operaciones inversas:

| Migración pendiente | Operaciones revisadas |
| --- | --- |
| `oficinas.0002_asignacionoperadoroficina_eventoasignacion_and_more` | Crea `AsignacionOperadorOficina` y `EventoAsignacion`; añade unicidad de la pareja y CHECK de estados de eventos, con sus claves foráneas e índices. |
| `usuarios.0002_alter_usuario_options` | Cambia opciones de managers base y por defecto de `Usuario` a `objects`; sin cambios físicos de esquema. |

Se contrastaron las operaciones con las migraciones revisadas y se inspeccionó su SQL. El SQL de Usuario mostró `(no-op)`; el de oficinas correspondió a las dos tablas y sus restricciones e índices. `to_regclass` confirmó que las dos tablas nuevas todavía no existían. Se continuó únicamente al coincidir todas las condiciones previas.

## Aplicación ejecutada

```bash
.venv/bin/python -B manage.py migrate --settings=config.settings --noinput
```

La salida confirmó:

```text
Applying oficinas.0002_asignacionoperadoroficina_eventoasignacion_and_more... OK
Applying usuarios.0002_alter_usuario_options... OK
```

Se aplicaron los archivos reales, sin `--fake` ni `--fake-initial`.

## Comprobaciones posteriores

Con la misma configuración se ejecutaron:

```bash
.venv/bin/python -B manage.py showmigrations --settings=config.settings
.venv/bin/python -B manage.py migrate --plan --settings=config.settings
.venv/bin/python -B manage.py check --settings=config.settings
```

- `showmigrations`: **20 migraciones aplicadas**, todas con `[X]`.
- `migrate --plan`: `No planned migration operations.`
- `check`: `System check identified no issues (0 silenced).`
- `MigrationExecutor`: historial consistente, 20 migraciones coincidentes con los archivos y plan vacío.
- Las opciones de managers del estado final de migraciones y del modelo `Usuario` coincidieron: base y por defecto `objects`.

## Inspección de lectura del esquema y los datos

Una nueva conexión en modo de solo lectura confirmó nuevamente `atencion_ciudadana` y `atencion_app`. La introspección y las consultas a `information_schema.columns`, `pg_constraint` y `pg_index` contrastaron el esquema con los modelos y el estado final de migraciones.

| Tabla nueva | Columnas verificadas | Filas |
| --- | --- | --- |
| `oficinas_asignacionoperadoroficina` | `id` bigint con identidad `BY DEFAULT`, `activo` boolean, `oficina_id` bigint, `operador_id` bigint; todas `NOT NULL`. | **0** |
| `oficinas_eventoasignacion` | `id` bigint con identidad `BY DEFAULT`, `fecha` timestamp con zona horaria, `operacion` varchar(12), `activo_anterior` boolean, `activo_nuevo` boolean, `actor_id` bigint, `asignacion_id` bigint; solo `activo_anterior` admite `NULL`. | **0** |

La inspección fue satisfactoria: **2 tablas nuevas y 11 columnas**, con tipos, longitudes, nulabilidad e identidades correspondientes a las migraciones.

Se verificaron **8 restricciones**, todas validadas:

- Dos claves primarias.
- Cuatro claves foráneas: asignación hacia oficina y operador, evento hacia actor y asignación; diferibles e inicialmente diferidas.
- `oficinas_asignacion_operador_oficina_unica`, sobre `(operador_id, oficina_id)`, sin condición sobre actividad.
- `oficinas_eventoasignacion_estados_coherentes`: creación con anterior `NULL` y nuevo `True`; reactivación con anterior `False`, explícitamente `IS NOT NULL`, y nuevo `True`.

Se verificaron **7 índices**, todos válidos, preparados y sin condición parcial: dos de claves primarias, el índice único de pareja y cuatro sobre las claves foráneas. Asignaciones y eventos quedaron con **cero filas**.

No se ejecutaron pruebas sobre esta base ni se crearon usuarios, asignaciones, eventos o datos de ejemplo. No se usaron migraciones simuladas ni se cambiaron privilegios, código, pruebas o archivos de migración. Al finalizar la aplicación documentada, Git seguía limpio y sincronizado con `origin/main`, en HEAD `e0d3207`; no se hizo commit ni push en esa ejecución.

## Estado y pendientes

**Las dos migraciones de asignaciones ya están aplicadas y verificadas en PostgreSQL local.** Esta inspección del esquema no equivale a pruebas funcionales sobre la base local ni sustituye la evidencia del registro 005, que distingue las 74 pruebas completas anteriores del ajuste final de concurrencia y las 3 pruebas posteriores, sin repetir la suite completa.

**Retirada y salida efectiva de `OPERADOR` continúan bloqueadas provisionalmente** hasta implementar y verificar las comprobaciones completas con folios reales y el protocolo compartido de bloqueos. Folios, pantallas y auditoría global siguen pendientes; los eventos actuales cubren únicamente creación y reactivación de asignaciones.

Las protecciones del ORM mantienen sus límites ante SQL directo, deserialización y APIs internas. Las restricciones verificadas no garantizan autorización ni un evento obligatorio para toda escritura; no se implementaron disparadores ni nuevas garantías funcionales en esta aplicación de migraciones.
