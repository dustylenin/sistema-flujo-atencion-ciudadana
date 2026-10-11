# 010 — Aplicación local de la migración de pausas y disponibilidad

Fecha local de ejecución: **11 de octubre de 2026**.

Commit de código: **`04659c8`** (`04659c8b44fcdd225962cac62ead580ee5242681`).

Estado: **primera entrega implementada, revisada en pruebas y con su migración aplicada y verificada en PostgreSQL local**.

Este registro documenta la aplicación ya completada de `folios.0002_pausaoperador_eventodisponibilidad_solicitudoperador_and_more`, conforme al [diseño 007](../decisiones/007-diseno-pausas-y-disponibilidad.md), después de la [verificación en PostgreSQL de pruebas](009-pausas-disponibilidad-postgresql.md). Su elaboración no repite comandos de Django, no conecta ni modifica bases y conserva las evidencias anteriores.

## Comprobaciones previas y conexión

Se leyeron README, la decisión 007 y el registro 009. Git estaba limpio en `04659c8`, en `main`, sincronizada con `origin/main`.

Se utilizó exclusivamente **`config.settings`**. La conexión real confirmó **base `atencion_ciudadana` y usuario `atencion_app`**, mediante `SELECT current_database(), current_user`, sin mostrar credenciales ni contenido de `.env`. El primer intento de conexión falló por el aislamiento del entorno; el mismo comando, con acceso autorizado, confirmó la identidad correcta:

```bash
.venv/bin/python -B manage.py shell --settings=config.settings -c 'from django.db import connection; assert connection.settings_dict["NAME"] == "atencion_ciudadana"; assert connection.settings_dict["USER"] == "atencion_app"; cursor = connection.cursor(); cursor.execute("SELECT current_database(), current_user"); identity = cursor.fetchone(); assert identity == ("atencion_ciudadana", "atencion_app"), identity; print(identity); cursor.close(); connection.close()'
```

Resultado: `('atencion_ciudadana', 'atencion_app')`. El fallo inicial no fue un fallo de la migración ni requirió cambiar credenciales o permisos.

Desde la raíz del repositorio se ejecutaron:

```bash
.venv/bin/python -B manage.py check --settings=config.settings
.venv/bin/python -B manage.py makemigrations --check --dry-run --settings=config.settings
.venv/bin/python -B manage.py migrate --plan --settings=config.settings
.venv/bin/python -B manage.py sqlmigrate folios 0002 --settings=config.settings
```

Resultados:

- `check`: `System check identified no issues (0 silenced).`
- Correspondencia modelos/migraciones: `No changes detected`.
- Historial: **21 migraciones aplicadas**, confirmado mediante `django_migrations` y `MigrationExecutor`, con historial consistente.
- Única pendiente: **`folios.0002_pausaoperador_eventodisponibilidad_solicitudoperador_and_more`**, tanto en el plan completo como en la inspección del ejecutor.
- Las tres tablas nuevas todavía no existían.

La inspección previa del historial y del esquema se realizó en una transacción con `SET TRANSACTION READ ONLY`. Se capturó en memoria el esquema de Folio y EventoFolio para contrastarlo después.

Se revisaron el plan y el SQL: tres `CreateModel` y ocho `AddConstraint`, exclusivamente sobre los modelos nuevos. El SQL crea sus tablas, claves foráneas e índices, cinco CHECK, dos restricciones UNIQUE y el índice único condicional `folios_pausa_abierta_unica`, sobre `operador_id` cuando `fin IS NULL`. No altera Folio, EventoFolio ni otras tablas existentes. Se continuó únicamente al coincidir las condiciones previas.

## Aplicación ejecutada

```bash
.venv/bin/python -B manage.py migrate folios 0002 --settings=config.settings --noinput
```

La ejecución terminó satisfactoriamente:

```text
Applying folios.0002_pausaoperador_eventodisponibilidad_solicitudoperador_and_more... OK
```

Se aplicó únicamente la migración real indicada, sin `--fake`, `--fake-initial` ni desactivar migraciones.

## Comprobaciones posteriores

Con la misma configuración se ejecutaron:

```bash
.venv/bin/python -B manage.py check --settings=config.settings
.venv/bin/python -B manage.py migrate --plan --settings=config.settings
.venv/bin/python -B manage.py showmigrations --settings=config.settings
```

- `check`: `System check identified no issues (0 silenced).`
- `migrate --plan`: `No planned migration operations.`
- `showmigrations`: **22 migraciones aplicadas**, todas con `[X]`, incluida `folios.0002`.
- La consulta de `django_migrations` y `MigrationExecutor` confirmaron **22 aplicadas y ninguna pendiente**, con historial consistente.

La comprobación `makemigrations --check --dry-run` se hizo antes de aplicar y no detectó diferencias. No hubo cambios de archivos durante la aplicación.

## Inspección de lectura del esquema y las filas

La inspección posterior volvió a confirmar `atencion_ciudadana / atencion_app`. Se ejecutó mediante `manage.py shell --settings=config.settings`, con código recibido por entrada estándar y una transacción con `SET TRANSACTION READ ONLY`. Consultó `pg_attribute`, `pg_attrdef`, `pg_constraint`, `pg_index` y `pg_class`, con `format_type`, `pg_get_constraintdef` y `pg_get_indexdef`, y contó filas mediante `SELECT count(*)`.

| Modelo / tabla nueva | Columnas | Restricciones | Índices | Registros |
| --- | ---: | ---: | ---: | ---: |
| PausaOperador / `folios_pausaoperador` | 7 | 7 | 5 | **0** |
| EventoDisponibilidad / `folios_eventodisponibilidad` | 5 | 5 | 4 | **0** |
| SolicitudOperador / `folios_solicitudoperador` | 10 | 7 | 6 | **0** |
| **Total** | **22** | **19** | **15** | **0** |

Los resultados coinciden con el diseño 007 y la evidencia del registro 009, sin diferencias de esquema:

- Tipos y nulabilidad coinciden con los modelos actuales y el estado de migraciones, comparados por nombre de columna. Se normalizó el alias equivalente `varchar(n)` / `character varying(n)` en la lectura.
- Las PK son bigint con identidad `BY DEFAULT`; las fechas son `timestamp with time zone`; las claves de solicitud y el contexto de folio son UUID; los demás tipos y longitudes coinciden con el diseño.
- En PausaOperador admiten NULL `fin`, `folio_contexto_id` y `oficina_contexto_id`; en SolicitudOperador, `motivo_solicitado`, `pausa_objetivo_id` y `evento_resultado_id`. EventoDisponibilidad no tiene columnas anulables. Las demás columnas son NOT NULL.
- Las **19 restricciones** son tres PK, nueve FK, cinco CHECK y dos UNIQUE; todas están validadas. Los CHECK conservan las condiciones explícitas de NULL, contenido del motivo, orden temporal, contexto conjunto, operaciones y coherencia del comprobante.
- Las nueve referencias apuntan a las tablas y columnas previstas: Usuario, Oficina, Folio, PausaOperador y EventoDisponibilidad. Son diferibles e inicialmente diferidas, con `NO ACTION` en actualización y borrado; los modelos conservan `PROTECT` en el ORM.
- Los **15 índices** son tres de PK, nueve de FK y tres únicos, incluido el condicional para una sola pausa abierta. Todos están válidos y preparados.
- Las tres tablas nuevas tienen **cero registros**.

**El esquema de Folio y EventoFolio es idéntico al capturado antes**: columnas, tipos, nulabilidad, valores predeterminados, identidad, restricciones e índices. Se conservan los estados y eventos CREACION de la entrega anterior.

## Estado final y verificaciones pendientes

La primera entrega de pausa, reanudación y consultas de disponibilidad está implementada, revisada en pruebas y con `folios.0002` aplicada y verificada localmente. No se ejecutaron pruebas en `atencion_ciudadana` ni se crearon datos de ejemplo. No se cambiaron código, pruebas, migraciones, credenciales o permisos. Al finalizar la aplicación, Git seguía limpio en `04659c8`, sincronizado con `origin/main`; esa ejecución no hizo commit ni push.

Las **37 pruebas nuevas, incluidas 12 de concurrencia, y la suite completa de 140 que incluye esas 37** siguen documentadas en el registro 009. No se repitieron ni se suman los conteos. El registro 009 conserva su estado histórico previo a esta aplicación local.

La aplicación del esquema y su inspección no verifican nuevos casos funcionales. Los casos reales de **Ocupado y contexto desde Llamado** se verificarán al integrar la segunda entrega de llamado y reserva con pausa y el límite global de un folio actual. **En atención y conservación de notas** se verificarán cuando se implementen; no se simularon esos estados ni se habilitaron aquí. Inicio, notas, cierre, pantallas y correcciones administrativas siguen fuera de la primera entrega.

Se conservan los límites de las barreras del ORM ante SQL directo, deserializadores y APIs internas, así como los permisos ampliados y demás decisiones pendientes del diseño 007. Retirada de asignaciones y salida de OPERADOR continúan bloqueadas provisionalmente.
