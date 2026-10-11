# 008 — Aplicación local de la migración de folios

Fecha local de ejecución: **10 de octubre de 2026**.

Commit de código: **`2d690da`** (`2d690dae43dc99c365a34fb195e5489c086c4df8`).

Estado: **registro inicial implementado, revisado en pruebas y con su migración aplicada y verificada en PostgreSQL local**.

Este registro documenta la aplicación ya completada de `folios.0001_initial`, conforme a los [acuerdos vigentes](../acuerdos-vigentes.md) y la [decisión 005](../decisiones/005-registro-inicial-de-folios.md), después de la [verificación en PostgreSQL de pruebas](007-registro-inicial-folios-postgresql.md). Su elaboración no repite comandos de Django, no conecta ni modifica bases y conserva intactas las evidencias históricas.

## Comprobaciones previas

Se leyeron README, los acuerdos vigentes, la decisión 005 y el registro 007. Git estaba limpio, en `main`, sincronizada con `origin/main`, con HEAD `2d690da`.

Mediante **`config.settings`**, una conexión real confirmó **base `atencion_ciudadana` y usuario `atencion_app`**. Se consultaron `current_database()` y `current_user` sin mostrar credenciales ni contenido de `.env`. La identidad, el historial y la ausencia de las tablas nuevas se comprobaron en una transacción de lectura.

Desde la raíz del repositorio se ejecutaron:

```bash
.venv/bin/python -B manage.py check --settings=config.settings
.venv/bin/python -B manage.py makemigrations --check --dry-run --settings=config.settings
.venv/bin/python -B manage.py showmigrations --settings=config.settings
.venv/bin/python -B manage.py migrate --plan --settings=config.settings
.venv/bin/python -B manage.py sqlmigrate folios 0001 --settings=config.settings
```

Resultados:

- `check`: `System check identified no issues (0 silenced).`
- Correspondencia modelos/migraciones: `No changes detected`.
- Historial: **20 migraciones aplicadas**, coincidentes con todos los archivos anteriores.
- Única pendiente: **`folios.0001_initial`**, confirmada también mediante `MigrationExecutor`.
- Las tablas `folios_folio` y `folios_eventofolio` todavía no existían.

El plan y el SQL fueron revisados y coherentes con la migración: creación de Folio y EventoFolio, CHECK de contenido del nombre, CHECK de estado En espera y operador NULL, CHECK de CREACION con anterior NULL y nuevo En espera, unicidad condicional del evento de creación, claves foráneas e índices. Se continuó únicamente al coincidir las condiciones previas.

## Aplicación ejecutada

```bash
.venv/bin/python -B manage.py migrate folios 0001 --settings=config.settings --noinput
```

La ejecución terminó satisfactoriamente:

```text
Applying folios.0001_initial... OK
```

Se aplicó el archivo real, sin `--fake`, `--fake-initial` ni desactivar migraciones.

## Comprobaciones posteriores

Con la misma configuración se ejecutaron:

```bash
.venv/bin/python -B manage.py showmigrations --settings=config.settings
.venv/bin/python -B manage.py migrate --plan --settings=config.settings
.venv/bin/python -B manage.py check --settings=config.settings
```

- `showmigrations`: **21 migraciones aplicadas**, todas con `[X]`, incluida `folios.0001_initial`.
- `migrate --plan`: `No planned migration operations.`
- `check`: `System check identified no issues (0 silenced).`
- `MigrationExecutor`: 21 migraciones coincidentes con los archivos y plan vacío.

La comprobación de modelos/migraciones se hizo antes de aplicar y no detectó diferencias. No hubo cambios de archivos durante la aplicación.

## Inspección de lectura del esquema y las filas

La inspección posterior volvió a confirmar `atencion_ciudadana / atencion_app` y utilizó una transacción con `SET TRANSACTION READ ONLY`. Consultó `pg_attribute`, `pg_class`, `pg_namespace`, `pg_constraint` y `pg_index`, junto con la introspección de Django, para contrastar columnas, tipos, nulabilidad, identidad, claves primarias, referencias, definiciones de CHECK e índices.

**La inspección inicial falló** en la comparación literal de tipos: Django expresaba `varchar(n)` y `format_type` de PostgreSQL devolvía `character varying(n)`. Se normalizaron esos alias equivalentes en la comprobación de lectura. La verificación posterior pasó sin diferencias; no fue un fallo de aplicación de la migración ni requirió cambiar el esquema o archivos.

| Tabla nueva | Columnas | Filas |
| --- | --- | --- |
| `folios_folio` | 10 | **0** |
| `folios_eventofolio` | 8 | **0** |

Las **18 columnas** coincidieron con los modelos: UUID del folio y su referencia en el evento; textos y longitudes correspondientes; fechas con zona horaria; JSONB de datos iniciales; referencias bigint y PK del evento bigint con identidad `BY DEFAULT`. Solo `operador_responsable_id` en Folio y `estado_anterior` en EventoFolio admiten NULL.

Se verificaron **11 restricciones**, todas validadas:

- Dos claves primarias.
- Seis claves foráneas, diferibles e inicialmente diferidas, hacia las tablas y columnas esperadas.
- Tres CHECK: contenido del nombre; En espera y operador vacío; CREACION con anterior NULL y nuevo En espera.

Se verificaron **9 índices**, todos válidos y preparados: dos de PK, seis de FK y el índice único condicional `folios_evento_creacion_unica`, sobre `folio_id` cuando la operación es CREACION.

Los resultados coinciden con la evidencia del registro 007: **2 tablas, 18 columnas, 11 restricciones y 9 índices**. Ambas tablas nuevas quedaron con **cero registros**. Esta inspección no ejecutó pruebas funcionales ni comprobó autorización mediante escrituras en la base normal.

## Estado final y pendientes

`folios.0001_initial` está aplicada y verificada en PostgreSQL local. No se ejecutó la suite de pruebas sobre `atencion_ciudadana`, no se crearon usuarios, folios, eventos o datos de ejemplo, y no se cambiaron permisos ni credenciales. Tampoco se modificaron código, pruebas o migraciones. Al finalizar la aplicación, Git seguía limpio y sincronizado, con HEAD `2d690da`; esa ejecución no hizo commit ni push.

Las **102 pruebas completas anteriores** y las **3 pruebas afectadas posteriores a la corrección del descriptor inverso** siguen documentadas por separado en el registro 007. No se repitieron aquí ni se suman sus conteos. La aplicación del esquema no sustituye esa evidencia.

Esta etapa mantiene el alcance de registro por Recepción, UUID interno, estado En espera, operador vacío y evento CREACION conjunto. Continúan pendientes llamado y reserva, inicio, cierre, notas, traslados, pausas, correcciones, demás acciones, pantallas, formato visible y auditoría global. Retirada de asignaciones y salida de `OPERADOR` permanecen bloqueadas provisionalmente hasta implementar sus comprobaciones definitivas de folios.

Las barreras del ORM conservan sus límites ante SQL directo, deserialización y APIs internas. Las restricciones inspeccionadas no garantizan autorización, coherencia entre filas ni un evento obligatorio para toda escritura; los eventos de creación no constituyen la auditoría global.
