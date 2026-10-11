# 007 — Registro inicial de folios en PostgreSQL de pruebas

Fecha de registro: **10 de octubre de 2026**.

Estado: **registro inicial implementado y revisado en pruebas; aplicación de `folios.0001_initial` a PostgreSQL local pendiente**.

Este documento conserva las ejecuciones ya realizadas de la [decisión 005](../decisiones/005-registro-inicial-de-folios.md), conforme a los [acuerdos vigentes](../acuerdos-vigentes.md) y la [decisión 004](../decisiones/004-cola-y-responsabilidad-de-folios.md). Su preparación no ejecuta pruebas ni comandos de Django, no conecta bases y no modifica código, pruebas o migraciones. Las evidencias anteriores se conservan intactas.

## Alcance implementado

La aplicación `folios` contiene `Folio`, `EventoFolio` y `registrar_folio`. Recepción registra nombre obligatorio con contenido, correo válido si se proporciona y teléfono opcional sin formato obligatorio inventado. Oficina y trámite deben existir, estar activos y corresponder entre sí.

La cuenta del actor debe proceder del contexto autenticado, estar persistida, activa y tener rol `RECEPCION`. Su estado actual se relee dentro de la transacción después de bloquear su fila. `is_staff` e `is_superuser` no conceden autorización funcional.

El servidor establece UUID técnico interno, llegada original, responsable del registro, estado **En espera** y operador responsable **NULL**. No se define formato visible, consecutivos ni reinicios. El evento **CREACION** guarda el mismo actor y fecha, estado anterior NULL, nuevo `EN_ESPERA` y una copia inicial construida por el servicio: nombre, correo, teléfono, IDs de oficina y trámite y llegada en formato ISO con zona horaria.

Un CHECK exige estado En espera y operador vacío en esta entrega; otro valida contenido del nombre. El CHECK del evento exige CREACION, anterior NULL y nuevo En espera; operación y nuevo estado son NOT NULL. Un índice único condicional impide más de un evento de creación por folio. Las referencias usan `PROTECT`.

Cuenta, oficina y trámite se bloquean en ese orden y sus condiciones se comprueban después de adquirir cada bloqueo. Folio y evento se insertan mediante persistencia privada con `force_insert=True` en la misma transacción y conexión. Un fallo del evento revierte el folio; un fallo del folio no genera evento. La transacción exterior también puede revertir ambos; el evento no se difiere a `on_commit`.

## Entorno y aislamiento

| Comprobación | Resultado |
| --- | --- |
| Configuración | `config.settings_test_migrations` |
| Base real y `TEST.NAME` | `test_atencion_catalogos_migraciones` |
| Usuario real | `atencion_test` |
| Migraciones | `TEST.MIGRATE=True`, `MIGRATION_MODULES={}` |
| Ejecutor | `--keepdb --parallel 1 --noinput` |

La conexión real confirmó `current_database()` y `current_user` antes de aplicar la migración en pruebas y volvió a confirmarse en las inspecciones finales. No se mostraron secretos. Se conservaron las barreras existentes y la lista explícita de los dos nombres autorizados de bases de pruebas; no se aceptó cualquier prefijo `test_`. No se conectaron `atencion_ciudadana` ni la primera base de pruebas, y no se cambiaron privilegios.

## Comandos y resultados

Desde la raíz del repositorio se generó únicamente la migración nueva y se revisaron sus operaciones y SQL antes de aplicarla:

```bash
.venv/bin/python -B manage.py makemigrations folios --settings=config.settings_test_migrations
.venv/bin/python -B manage.py sqlmigrate folios 0001 --settings=config.settings_test_migrations
```

El ejecutor aplicó `folios.0001_initial` correctamente, usando migraciones reales, al ejecutar la suite completa:

```bash
.venv/bin/python -B manage.py test usuarios config.tests oficinas tramites folios --settings=config.settings_test_migrations --keepdb --parallel 1 --noinput --verbosity 2
```

Resultado: **102 pruebas satisfactorias en 8,646 segundos, incluidas 28 de folios**, con `check` sin incidencias. Esta ejecución ocurrió **antes de la corrección posterior del descriptor inverso**. Incluyó validación, autorización actualizada, valores iniciales, restricciones y NULL, unicidad de creación, rollback conjunto, referencias protegidas y barreras públicas del ORM.

Las cinco pruebas de concurrencia de folios usaron conexiones independientes identificadas por `pg_backend_pid()`, sincronización explícita y comprobación de espera mediante `pg_blocking_pids`. Cubrieron cambios de rol y desactivación de cuenta, oficina y trámite mientras el registro esperaba, y el orden contrario para las tres desactivaciones: el registro ya tenía el bloqueo, la desactivación esperó y el folio y evento quedaron guardados correctamente antes del cambio de actividad.

### Revisión y corrección del descriptor inverso

La revisión del código instalado de **Django 5.2.17** detectó que `relacion(manager="objects")` reconstruía el manager inverso y perdía las prohibiciones personalizadas de `add`, `set`, `remove` y `clear`. Algunas operaciones vacías dejaban de rechazarse; las escrituras efectivas seguían protegidas por `save` y los querysets. No se trató de una autorización concedida al actor ni de una escritura de folios sin servicio.

Se añadió una regresión que comprueba lecturas, selección repetida del manager, `db_manager`, operaciones relacionadas vacías con ambos valores de `bulk` y variantes síncronas/asíncronas. Antes de corregir el descriptor se ejecutó:

```bash
.venv/bin/python -B manage.py test folios.tests.RegistroFolioTests.test_seleccion_de_manager_inverso_conserva_lecturas_y_barreras --settings=config.settings_test_migrations --keepdb --parallel 1 --noinput --verbosity 1
```

La regresión **falló**, confirmando la pérdida de las prohibiciones; también hubo errores derivados de una transacción marcada para reversión durante los subcasos. Se corrigió `folios/managers.py` para envolver igualmente el manager seleccionado y conservar las barreras. La regresión aísla cada intento en un bloque `atomic`.

Después de la corrección se ejecutaron únicamente las pruebas afectadas:

```bash
.venv/bin/python -B manage.py test folios.tests.RegistroFolioTests.test_seleccion_de_manager_inverso_conserva_lecturas_y_barreras folios.tests.RegistroFolioTests.test_barreras_de_managers_relacionados folios.tests.RegistroFolioTests.test_barreras_modelos_y_managers_sync_async --settings=config.settings_test_migrations --keepdb --parallel 1 --noinput --verbosity 2
```

Resultado: **3 pruebas satisfactorias en 0,388 segundos**, incluida la regresión, con `check` sin incidencias. **No se repitió la suite completa ni las pruebas de concurrencia después de esta corrección. Las 102 pruebas corresponden a la ejecución anterior; los dos conteos no se suman ni describen una ejecución posterior de la suite completa.**

### Comprobaciones finales

Se ejecutaron durante implementación y revisión:

```bash
.venv/bin/python -B manage.py check --settings=config.settings_test_migrations
.venv/bin/python -B manage.py makemigrations --check --dry-run --settings=config.settings_test_migrations
.venv/bin/python -B manage.py showmigrations --settings=config.settings_test_migrations
.venv/bin/python -B manage.py migrate --plan --settings=config.settings_test_migrations
git diff --check
```

Resultados: `check` sin incidencias; correspondencia modelos/migraciones sin cambios detectados; todas las migraciones aplicadas y plan sin operaciones pendientes. Después de corregir el descriptor se repitieron `check`, la correspondencia modelos/migraciones y la revisión de formato, con resultados satisfactorios. El ajuste no requirió otra migración. Se verificaron también los ocho archivos nuevos con `git diff --no-index --check /dev/null <archivo>`, sin errores de formato.

Al preparar esta entrega se revisó el diff de los doce archivos autorizados y `git diff --cached --check` terminó sin incidencias. En esta etapa de documentación no se repitieron pruebas ni comprobaciones con base de datos.

## Migración, esquema y ausencia de datos residuales

La única migración nueva es `folios.0001_initial`: crea Folio y EventoFolio, añade tres CHECK y la unicidad condicional de CREACION, con sus referencias e índices. No se alteraron migraciones existentes, no se usó `--fake` ni `--fake-initial` y no se desactivaron migraciones.

Quedaron **21 migraciones aplicadas en pruebas**: doce de `auth`, dos de `contenttypes`, una de `sessions`, dos de `usuarios`, dos de `oficinas`, una de `tramites` y una de `folios`. El plan quedó sin pendientes; la lectura posterior a la corrección confirmó nuevamente el total de 21.

La inspección de lectura mediante `information_schema.columns`, `pg_constraint` y `pg_indexes` verificó:

| Elemento | Resultado |
| --- | --- |
| Tablas nuevas | `folios_folio` y `folios_eventofolio` |
| Columnas | 18: diez del folio y ocho del evento |
| Restricciones | 11: dos claves primarias, seis referencias y tres CHECK |
| Índices | 9: dos de PK, seis de FK y uno único condicional por CREACION |

Las pruebas comprobaron rechazos reales de PostgreSQL por estados incoherentes, operador no vacío, valores NULL obligatorios, referencias inválidas y evento de creación duplicado. Un fallo real del INSERT de evento comprobó la reversión del folio ya insertado.

Las inspecciones finales se hicieron en transacciones de lectura y confirmaron **cero filas residuales de aplicación**, tanto al terminar la implementación como después de las pruebas afectadas de revisión:

- `usuarios_usuario`, `oficinas_oficina` y `tramites_tramite`.
- `oficinas_asignacionoperadoroficina` y `oficinas_eventoasignacion`.
- `folios_folio` y `folios_eventofolio`.

**`folios.0001_initial` todavía está pendiente en `atencion_ciudadana`.** La última evidencia de esa base conserva las 20 migraciones de catálogos y asignaciones, documentadas en el [registro 006](006-migraciones-asignaciones-local.md). No se consultó ni modificó esa base durante esta etapa.

## Límites y pendientes

Las barreras cubren escritura y borrado públicos mediante instancias, querysets, managers por defecto, base e inversos, incluidos métodos asíncronos y selección repetida del manager relacionado. No existe una opción pública para omitir validaciones.

SQL directo, deserializadores y APIs internas pueden eludir las barreras. Las restricciones de PostgreSQL no garantizan autorización, coherencia entre filas ni que toda inserción de folio tenga un evento. La unicidad garantiza como máximo un evento CREACION; el servicio autorizado garantiza la persistencia conjunta. La copia inicial se construye en el servicio, sin atribuirle una validación completa de estructura JSON en la base. La compatibilidad del descriptor se revisó con Django 5.2.17 instalado; deberá revisarse al cambiar esa implementación de Django.

La restricción de estado y operador corresponde a esta primera entrega y se ampliará mediante nuevas migraciones para incorporar el llamado aprobado en la decisión 004. Registrar no reserva un operador ni registra un inicio de atención.

Continúan pendientes llamado y reserva, inicio, cierre, notas, traslados, pausas, correcciones, demás acciones, pantallas, formato visible y auditoría global. EventoFolio no es la auditoría completa del sistema. Retirada de asignaciones y salida de `OPERADOR` siguen bloqueadas provisionalmente hasta implementar y verificar sus comprobaciones definitivas de folios asignados sin finalizar. Los acuerdos funcionales y evidencias anteriores se conservan.
