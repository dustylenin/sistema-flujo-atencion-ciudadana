# 013 — Preparación de llamado y reserva, sin aplicación de esquema

**Ejecución posterior del 12 de octubre de 2026:** el [registro 014](014-validacion-llamado-y-reserva-postgresql.md) documenta 0003 aplicada solo en la base aislada, 51 pruebas nuevas y regresión de 242 satisfactorias, 4 JavaScript y recuperación DEMO verificada. Este registro conserva la evidencia de preparación/revisión y el procedimiento anteriores a esa ejecución; sus avisos de operaciones todavía no realizadas corresponden a ese momento. Estado actual del entorno aislado: **23 migraciones, ninguna pendiente, DEMO recuperado y 8001 detenido**.

- Fecha: 12 de octubre de 2026.
- Diseño: [decisión 008](../decisiones/008-diseno-llamado-y-reserva.md), conservando acuerdos de las decisiones 004 y 006 e integración de la 007.
- Punto de partida: `main` limpio y sincronizado con `origin/main` según Git local, en `5245a5747a43678397573c6d9e41f53a842779d6`.
- Configuración exclusiva de todas las operaciones Django: `config.settings_test_migrations`.
- Identidad real previa a editar: **`test_atencion_catalogos_migraciones / atencion_test`**, **22 migraciones aplicadas y ninguna pendiente**.

## Conservación y respaldo obtenido

Se comprobaron configuración, PostgreSQL, alias único, `NAME`, `TEST.NAME` y usuario de pruebas antes de abrir la conexión. `SELECT current_database(), current_user` confirmó identidad real. `MigrationRecorder` contó 22 migraciones y `MigrationExecutor` devolvió plan vacío. No se conectó la base normal.

Se creó un directorio nuevo privado fuera del repositorio y un archivo nuevo, sin sobrescribir archivos anteriores. `pg_dump` produjo un respaldo completo en formato custom, con esquema y datos de la base aislada. La contraseña de conexión se transmitió al subproceso exclusivamente en memoria, mediante su entorno; no se escribió en archivos ni se imprimió. No se mostraron cuentas, hashes ni contenido del respaldo.

| Propiedad | Resultado |
| --- | --- |
| Directorio | `/home/lenin/respaldo-llamado-20261012-bynba1if/` |
| Archivo | `test_atencion_catalogos_migraciones.dump` |
| Tamaño | **68 506 bytes**, no vacío. |
| Permisos del directorio / archivo | **0700 / 0600**. |
| Lectura | `pg_restore --list` y generación completa de SQL hacia `/dev/null` terminaron correctamente, sin mostrar su contenido. |
| Restauración real | **No realizada ni comprobada**. |

Los datos DEMO se conservaron. No se restauró, borró o limpió ningún dato. El respaldo no forma parte de los cambios de Git; comprobar su lectura no acredita una restauración ni autoriza ejecutar el runner sobre el entorno manual.

## Código preparado

`folios/services_llamado.py` implementa `llamar_siguiente(*, actor, solicitud_id)` y los cinco resultados del diseño. Relee y bloquea al operador; valida su actividad y rol funcional vigente, independientemente de `is_staff` e `is_superuser`; valida la clave y resuelve un comprobante histórico antes de consultar el estado actual. El rol ADMINISTRADOR no sustituye al OPERADOR para llamar.

Para una intención nueva se evalúan pausa, folio actual global y asignaciones activas. Se bloquean todas las oficinas por PK, luego las asignaciones por PK; se selecciona En espera por `llegada_original, id`, con bloqueo exclusivo de Folio, sin `skip_locked` ni filtros de actividad de oficina/trámite. El servicio revalida la pertenencia a la asignación autorizante. La actualización privada cambia únicamente estado a LLAMADO y operador responsable; llegada y datos iniciales se conservan. Reserva, evento y comprobante se guardan en una transacción, sujetos también al resultado de una transacción exterior.

Los resultados sin transición solo insertan comprobante y devuelven folio/evento NULL. Los reintentos autorizados devuelven identificadores y fecha históricos sin nuevas escrituras. La clave tiene ámbito por operador y es compartida con PAUSAR/REANUDAR; otra operación o argumentos incompatibles se rechazan.

Se extraen exclusivamente clave, búsqueda y comparación de comprobantes en `folios/solicitudes.py`. Pausa/reanudación mantienen resultado y persistencia propios. No cambian `registrar_folio`, barreras del ORM, modelos/servicios de usuarios y asignaciones, ni las rutas o pantallas actuales de Recepción.

## Migración y revisión del SQL

Archivo completo: [folios.0003_llamado_y_reserva](../../folios/migrations/0003_llamado_y_reserva.py). Tiene **18 operaciones**, depende de folios.0002 y conserva dependencias de catálogos/usuario. No contiene RunPython ni instrucciones de alta, actualización o borrado de datos.

El SQL generado contempla:

- Cuatro columnas nullable: responsable y asignación autorizante del evento; folio UUID y evento bigint del comprobante. Cuatro referencias e índices de claves foráneas nuevos.
- `datos_iniciales` y `pausa_resultado` pasan a nullable; los CHECK exigen sus valores en CREACION y pausa/reanudación, respectivamente. La FK de pausa resultado se conserva.
- Sustitución de tres CHECK: Folio exige En espera sin responsable o Llamado con responsable; EventoFolio distingue CREACION y LLAMADO con NULL explícitos y actor igual al responsable; SolicitudOperador distingue PAUSAR, REANUDAR y LLAMAR y sus resultados/referencias.
- Índice parcial de cola `(oficina_id, llegada_original, id)` para En espera y unicidad global del responsable para LLAMADO/EN_ATENCION. El literal EN_ATENCION del índice **no habilita ese estado**: choices y CHECK siguen rechazándolo.
- Los cambios de choices se reflejan en el estado de migraciones; no necesitan SQL propio. Los eventos y comprobantes anteriores cumplen las ramas conservadas y los campos añadidos quedan NULL; su conservación real al migrar todavía debe probarse.

SQL de revisión fuera del repositorio: `/tmp/revision-sql-llamado-ew_bok_a/0003_llamado_y_reserva.sql`. **Generado e inspeccionado; no ejecutado**. El plan mediante `MigrationExecutor` tiene una única operación de aplicación pendiente: `folios.0003_llamado_y_reserva`. El historial de la base conserva **22 migraciones aplicadas**.

La generación de migración, correspondencia y SQL se realizó con `PGOPTIONS='-c default_transaction_read_only=on'`. Para revisar SQL y plan se verificaron nuevamente identidad real y `SHOW default_transaction_read_only = on`. Los conteos agregados de **13 tablas** de aplicación/sesiones, las columnas y las restricciones del esquema fueron iguales antes y después de `sqlmigrate`; no se imprimieron contenidos de tablas. Este contraste acredita ese intervalo de revisión, no una restauración ni una migración aplicada.

## Pruebas escritas, todavía no ejecutadas

| Archivo nuevo | Casos preparados |
| --- | --- |
| `folios/test_llamado.py` | **30**: permisos vigentes, flags, cola múltiple y desactivaciones, desempate, capacidad global, pausas con folio real, comprobantes históricos e incompatibles, restricciones, referencias, barreras e inversas asíncronas, rollback y orden de bloqueos. |
| `folios/test_llamado_concurrencia.py` | **20**: claves iguales/distintas, operadores competidores, colas solapadas/disjuntas, rollback, ambos órdenes frente a pausa/reanudación, desactivación, cambio de rol, registro y servicios de asignación. |
| `folios/test_migracion_llamado.py` | **1**: conservación de folio, evento CREACION, pausa, eventos y comprobantes PAUSAR/REANUDAR mediante aplicación real en una ejecución futura autorizada. Recupera el esquema del runner al terminar. |

**51 casos nuevos definidos por inspección de sintaxis, ninguno ejecutado.** Las clases conservan las barreras existentes de identidad real y configuración exclusiva. Las pruebas de concurrencia preparan conexiones y PIDs distintos, coordinación explícita y comprobación de espera con `pg_blocking_pids`; la cola disjunta debe completar mientras otra oficina mantiene su bloqueo. Los estados históricos inactivos y cambios de rol se preparan como fixtures de pruebas, sin habilitar retirada ni salida funcional de OPERADOR.

En `folios/tests.py` y `folios/test_disponibilidad.py` se adaptan expectativas del CHECK renombrado y de campos ahora nullable pero obligatorios en sus ramas. Las regresiones tampoco se ejecutaron.

## Comprobaciones realizadas en esta etapa

```bash
PGOPTIONS='-c default_transaction_read_only=on' .venv/bin/python -B manage.py makemigrations folios --name llamado_y_reserva --settings=config.settings_test_migrations
.venv/bin/python -B manage.py check --settings=config.settings_test_migrations
PGOPTIONS='-c default_transaction_read_only=on' .venv/bin/python -B manage.py makemigrations --check --dry-run --settings=config.settings_test_migrations
git diff --check
```

Además se obtuvo el SQL mediante `call_command('sqlmigrate', 'folios', '0003_llamado_y_reserva')` en la conexión aislada de solo lectura, se inspeccionó el plan sin ejecutarlo y se validó sintaxis Python. Servicio y módulos de pruebas se importaron sin abrir conexión ni ejecutar casos.

`check` terminó sin incidencias; `makemigrations --check --dry-run` indicó **No changes detected**. Formato del diff y archivos nuevos correcto. **No son pruebas funcionales satisfactorias**. Las 191 pruebas Django y 4 JavaScript anteriores corresponden a Recepción y su etapa previa, sin atribuirse a este código preparado ni presentarse como una nueva ejecución.

## Pendientes y límites

No se ejecutó `migrate`, runner, restauración ni limpieza; no se modificó el esquema ni se conectó la base normal. No se hizo commit, push ni preparación del índice. El código preparado utiliza columnas nuevas: requiere aplicar y verificar folios.0003 en una etapa posterior antes de usar los guardados con esta versión. La revisión DEMO debe conservarse y coordinarse antes de reiniciar sus servicios o ejecutar pruebas.

Quedan pendientes aprobación/revisión de aplicación, comprobación real de esquema y conservación histórica, ejecución de las 51 pruebas nuevas y regresión completa, revisión de concurrencia efectiva y restauración probada del respaldo si se necesita. Disponer del archivo legible no resuelve por sí solo la conservación del entorno manual.

Lecturas adicionales y pantallas de Operador, inicio de atención, finalización, correcciones administrativas y formato público de folio quedan fuera de esta etapa. Se conservan pendientes Inactivo, permisos ampliados, presentación de pausas sin oficina y restauraciones/reasignaciones que pudieran producir un segundo folio actual. Una oficina puede tener varios operadores; no se introduce una restricción de uno activo por oficina.

## Revisión enfocada — 12 de octubre de 2026

Se revisaron el servicio completo, sus primitivas privadas y comprobantes compartidos, modelos, migración 0003 y casos preparados, contrastándolos con la decisión 008 y la integración existente de usuarios, asignaciones, registro y pausas. **No se identificó un defecto concreto que requiriese modificar código, la migración nueva o su SQL**. En esta revisión se amplía únicamente este registro; las migraciones anteriores no cambian y no se añaden reglas funcionales.

| Punto revisado | Evidencia de inspección |
| --- | --- |
| Autorización vigente | `_operador_bloqueado` adquiere Usuario y comprueba actividad y rol con la fila devuelta después de esperar; precede a la búsqueda de comprobantes en LLAMAR, PAUSAR y REANUDAR. ADMINISTRADOR y los flags técnicos no sustituyen OPERADOR. El bloqueo se conserva hasta terminar la transacción. |
| Orden y selección | Usuario → todas las oficinas por PK → asignaciones por PK → Folio. Llamado consulta pausa y capacidad bajo Usuario sin adquirir otros bloqueos antes de las oficinas; pausa/reanudación conservan oficinas → pausas → folio. La selección es una consulta nueva tras adquirir todas las oficinas, ordenada por llegada original y UUID, con `FOR UPDATE OF` Folio y sin `skip_locked`. |
| Cola y capacidad | Asignaciones activas múltiples; sin filtros de actividad de oficina/trámite. El folio actual se consulta globalmente sin ocultarlo por actividad o asignación. |
| Atomicidad | Reserva, evento y comprobante se escriben dentro del mismo `atomic`; reserva actualiza exclusivamente estado y responsable. No se modifica llegada ni datos originales. También quedan sujetos al rollback de la transacción exterior. |
| Idempotencia | Unicidad compartida por operador y clave; se comparan operación, motivo y pausa objetivo. La repetición autorizada devuelve el resultado histórico antes de evaluar disponibilidad o asignaciones, incluidos los cuatro resultados sin llamado. |
| Historia y límites | Los campos nuevos son nullable y las ramas antiguas siguen válidas. Solo se habilita LLAMADO; EN_ATENCION permanece rechazado. No hay unicidad permanente de LLAMADO por folio. |
| Recuperación del esquema en la prueba | `addCleanup(restaurar_esquema)` se registra antes de migrar hacia 0002. `unittest` ejecuta cleanups incluso si falla `setUp` o el caso; Django realiza después su `_post_teardown`. Se vuelve a 0003 antes de la limpieza de datos del caso. Es inspección del código y del ciclo del runner instalado, todavía sin comprobar mediante ejecución. Un fallo de la propia recuperación debe tratarse como error y comprobar el esquema antes de continuar. |

### Restricciones e índices exactos de 0003

Se sustituyen tres CHECK, con estas ramas cerradas:

| Restricción | Combinaciones admitidas |
| --- | --- |
| `folios_folio_estado_responsable` | EN_ESPERA y responsable NULL; o LLAMADO y responsable no NULL. Ningún otro estado. |
| `folios_evento_campos_coherentes`, CREACION | Anterior NULL, nuevo EN_ESPERA, datos iniciales no NULL, responsable y asignación NULL. |
| `folios_evento_campos_coherentes`, LLAMADO | Anterior explícitamente no NULL e igual a EN_ESPERA, nuevo LLAMADO, datos iniciales NULL, responsable y asignación no NULL, actor igual al responsable. |
| `folios_solicitud_campos_coherentes`, PAUSAR | Motivo no NULL y con contenido, objetivo NULL, pausa resultado no NULL; PAUSADA con evento de disponibilidad no NULL o YA_EN_PAUSA con evento NULL. Referencias a folio y evento de folio NULL. |
| `folios_solicitud_campos_coherentes`, REANUDAR | Motivo NULL, objetivo y pausa resultado explícitamente no NULL e iguales; REANUDADA con evento de disponibilidad no NULL o YA_REANUDADA con evento NULL. Referencias a folio y evento de folio NULL. |
| `folios_solicitud_campos_coherentes`, LLAMAR | Motivo, objetivo, pausa resultado y evento de disponibilidad NULL. LLAMADO exige folio y evento de folio no NULL; EN_PAUSA, OCUPADO, SIN_ASIGNACIONES y SIN_PENDIENTES exigen ambos NULL. |

Operación, resultado, actor, estado nuevo y los demás campos obligatorios conservan sus NOT NULL; los CHECK no sustituyen estos requisitos. Las correspondencias entre folio, evento, asignación y cuenta se revalidan en el servicio; los CHECK no realizan comprobaciones entre tablas ni garantizan por sí solos autorización o persistencia conjunta.

Índices añadidos:

- `folios_folio_actual_unico`: UNIQUE por `operador_responsable_id`, parcial para estado IN (LLAMADO, EN_ATENCION), global entre oficinas. Su predicado no habilita EN_ATENCION.
- `folios_cola_en_espera`: por `(oficina_id, llegada_original, id)`, parcial para EN_ESPERA.
- `folios_eventofolio_asignacion_autorizante_id_52fe2c86`: por asignación autorizante.
- `folios_eventofolio_operador_responsable_id_4229e4f4`: por responsable histórico.
- `folios_solicitudoperador_evento_folio_resultado_id_932f94b5`: por evento de folio del comprobante.
- `folios_solicitudoperador_folio_resultado_id_64c2abb6`: por folio del comprobante.

Las cuatro FK nuevas son diferibles, inicialmente diferidas; en el ORM usan PROTECT. Se conserva la FK de pausa resultado, ahora nullable. No se elimina `folios_evento_creacion_unica` (solo CREACION por folio), `folios_solicitud_operador_unica` (operador/clave), ni las restricciones de pausas y eventos de disponibilidad de 0002. No se añade una unicidad de asignación activa por oficina.

### Consultas de lectura realizadas en esta revisión

Se verificó nuevamente la identidad real **`test_atencion_catalogos_migraciones / atencion_test`**, `default_transaction_read_only=on` y aislamiento **READ COMMITTED**. Sobre las expresiones exactas del SQL generado se evaluaron con SELECT y VALUES sintéticos **8 combinaciones de Folio, 864 de EventoFolio y 11 520 de SolicitudOperador**, variando los campos nullable, estados/operaciones/resultados admitidos e inválidos y referencias iguales o distintas. **Ninguna expresión dio NULL ni divergió de las ramas esperadas en esas combinaciones**. Los campos protegidos por NOT NULL se mantuvieron no NULL en este análisis. No se insertaron fixtures ni se ejecutó el runner; esta comprobación de lógica SQL no sustituye rechazos reales de INSERT/UPDATE ni pruebas funcionales o de concurrencia.

También se evaluaron los tres CHECK futuros sobre los registros actuales mediante proyecciones de lectura que añaden NULL para las columnas todavía inexistentes: **cero registros incompatibles**. No se mostraron filas ni datos personales. El esquema actual tiene 18 tablas públicas, 16 secuencias y todas sus FK son diferibles. Conserva **22 migraciones aplicadas** y **solo 0003 pendiente**. No se ejecutó su SQL.

Se volvió a comprobar el respaldo absoluto **`/home/lenin/respaldo-llamado-20261012-bynba1if/test_atencion_catalogos_migraciones.dump`**: 68 506 bytes, directorio 0700, archivo 0600; `pg_restore --list` y lectura completa hacia `/dev/null` correctos. SHA-256 del archivo: `6d13677feaf2c48ab0f8d924b1a28355d8c93f907b303cd4186aee13d9d0f0cb`. Su catálogo contiene 18 entradas TABLE DATA y 16 SEQUENCE SET. **No se restauró: legibilidad e identidad del archivo no demuestran una restauración probada ni que futuros cambios DEMO estén contenidos en él.**

## Procedimiento pendiente para conservar DEMO al ejecutar pruebas

**Procedimiento propuesto, no ejecutado.** Requiere una etapa posterior autorizada para aplicar 0003, vaciar tablas de pruebas y recuperar sus datos. Todas las conexiones serán exclusivamente las de `config.settings_test_migrations`, con barreras de identidad antes de cada operación. El servidor manual debe permanecer detenido durante migración, runner y recuperación; no debe haber otros escritores o conexiones que conserven valores de secuencias en caché.

1. **Fijar el punto de conservación.** Detener el servidor 8001 y verificar configuración e identidad real, historial de 22 migraciones y plan exclusivo de 0003. Comprobar el archivo anterior con tamaño, permisos, SHA-256 y lectura completa por `pg_restore`, sin imprimir su contenido. Si se añadieron o cambiaron datos después del respaldo, crear otro respaldo completo en un directorio nuevo 0700, archivo nuevo 0600; nunca sobrescribir el existente. Con escritores detenidos, registrar en un manifiesto privado los conteos y huellas de las filas de las 17 tablas de datos, además de valores, `is_called`, incremento, límites y asociación de las 15 secuencias de datos. Las huellas y cualquier SQL con datos permanecerán fuera del repositorio y no se mostrarán. El manifiesto debe corresponder al respaldo elegido; no comparar una instantánea reciente con un archivo anterior sin establecer esa correspondencia.
2. **Preparar la recuperación antes de permitir la limpieza.** Usar el catálogo `pg_restore --list` del respaldo elegido. Crear una lista privada que conserve **solo TABLE DATA de public**, excluyendo `django_migrations`; exigir exactamente las 17 tablas enumeradas debajo. Excluir todo SEQUENCE SET del SQL de datos y toda definición de esquema. Leer las 15 entradas de secuencias de datos del respaldo en un archivo privado separado para obtener sus valores; excluir explícitamente `django_migrations_id_seq`. No usar restauración completa, `--clean`, `--create`, `--disable-triggers` ni la sección de esquema. Generar e inspeccionar sin mostrar datos el SQL de recuperación con `pg_restore --data-only --no-owner --no-privileges --use-list=<lista-privada> --file=<datos-privados.sql> <respaldo-absoluto>`. Comprobar las listas de columnas de COPY, ausencia de DDL y de instrucciones sobre el historial. La preparación de este archivo no restaura nada. [Opciones oficiales de pg_restore](https://www.postgresql.org/docs/16/app-pgrestore.html).
3. **Aplicar y verificar 0003 antes del runner.** En la etapa autorizada, aplicar únicamente el plan revisado y comprobar 23 migraciones, ninguna pendiente, cuatro columnas nuevas nullable, tres CHECK, cuatro FK e índices nuevos válidos. Comparar datos originales con el manifiesto: no deben cambiar. Las nuevas referencias de eventos y comprobantes anteriores deben quedar NULL. Conservar el historial completo de migraciones y el estado de su secuencia como referencia del esquema nuevo. La migración de pruebas retrocede temporalmente a 0002 y debe recuperar 0003 mediante su cleanup; eso no recupera datos DEMO.
4. **Ejecutar las pruebas con las tablas de datos vacías.** Solo después de preparar y revisar la recuperación, vaciar explícitamente las 17 tablas de datos en una sola operación aislada, sin tocar `django_migrations` ni su secuencia. Evita colisiones con cuentas DEMO y los conteos de los casos existentes. Ejecutar los casos nuevos y regresión completa con `config.settings_test_migrations` y `--keepdb`; keepdb conserva la base, **no sus filas**. Registrar resultados reales y conservar el respaldo aunque un caso falle. No iniciar el servidor entre estas operaciones.
5. **Comprobar el esquema tras el runner.** Verificar otra vez identidad, 23 migraciones, plan vacío, campos, CHECK, FK e índices finales. Si la prueba de migración no pudo recuperar 0003, detener el proceso y resolver el esquema antes de cargar datos; no falsificar `django_migrations`, usar `--fake` ni recuperar su tabla desde el respaldo. Guardar el historial y la secuencia de migraciones tal como estén una vez verificado el esquema final, para comprobar que la recuperación de datos no los altera.
6. **Recuperar las cuentas y registros sobre el esquema nuevo.** Formar un archivo SQL privado único, sin BEGIN/COMMIT propios: guardas SQL de identidad y esquema; `SET CONSTRAINTS ALL DEFERRED`; `TRUNCATE` explícito de las 17 tablas en una sentencia, **CONTINUE IDENTITY RESTRICT**; los COPY del archivo de datos; reinicio transaccional de las 15 secuencias de datos; `SET CONSTRAINTS ALL IMMEDIATE` y comprobaciones de datos/historial antes de terminar. El vaciado incluye content types y permisos regenerados por las pruebas para evitar colisiones, además de sus relaciones. Mantener todos los identificadores del respaldo conserva las referencias de cuentas, catálogos, folios y auditoría. Los COPY anteriores omiten las cuatro columnas nuevas, que quedan NULL y cumplen las ramas históricas. `TRUNCATE` con todas las tablas relacionadas explícitas evita arrastrar otras tablas con CASCADE y es transaccional. [TRUNCATE](https://www.postgresql.org/docs/16/sql-truncate.html).
7. **Secuencias y ejecución atómica.** Para cada secuencia de datos, calcular el siguiente valor desde el respaldo: `last_value` si `is_called=False`, o `last_value + incremento` si es True. Verificar incremento/límites y que no colisione con los ID recuperados; usar `ALTER SEQUENCE <nombre-validado> RESTART WITH <siguiente>` dentro del mismo archivo. Conserva la próxima asignación, aunque su representación pase a `is_called=False`. No ejecutar los `setval` del dump: sus cambios no se revierten con rollback; RESTART sí es transaccional. No modificar la secuencia de migraciones. Ejecutar el archivo futuro mediante `psql -X --set=ON_ERROR_STOP=1 --single-transaction --file=<recuperacion-privada.sql>`, con base/usuario/host/puerto tomados de la configuración aislada ya verificada. Contraseña solo en el entorno en memoria del subproceso; salida y errores a un registro privado 0600, sin mostrar comandos COPY ni valores. Comprobar código de salida: ante un error, no reabrir el servidor. [ALTER SEQUENCE](https://www.postgresql.org/docs/16/sql-altersequence.html), [psql](https://www.postgresql.org/docs/current/app-psql.html).
8. **Verificación posterior antes de abrir DEMO.** Confirmar identidad real, 23 migraciones y ninguna pendiente; historial y secuencia de migraciones iguales a los registrados antes de recuperar; índices válidos y CHECK/FK validados. Comparar conteos y huellas privadas con el manifiesto, referencias históricas y valores originales, llegada y estado; comprobar el siguiente valor de las secuencias sin llamar `nextval`. Verificar en lectura cuenta RECEPCION activa sin staff/superuser y oficina/trámite DEMO activos y compatibles, sin mostrar información de cuentas. Solo entonces reiniciar 8001 con las cookies diferenciadas y volver a comprobar el acceso manual. Las sesiones recuperadas pueden haber caducado; iniciar sesión de nuevo no exige cambiar cuentas ni contraseñas.

Las **17 tablas de recuperación**, identificadas en los metadatos del respaldo existente, son:

```text
auth_group
auth_group_permissions
auth_permission
django_content_type
django_session
folios_eventodisponibilidad
folios_eventofolio
folios_folio
folios_pausaoperador
folios_solicitudoperador
oficinas_asignacionoperadoroficina
oficinas_eventoasignacion
oficinas_oficina
tramites_tramite
usuarios_usuario
usuarios_usuario_groups
usuarios_usuario_user_permissions
```

La recuperación propuesta mantiene el esquema de 0003 y su historial de migraciones; **no consiste en restaurar el esquema viejo ni en recuperar solo tres filas DEMO**. Conserva también relaciones e historial de registro, asignación y pausa. Preparar el respaldo legible y este procedimiento no equivale a haber probado la restauración. La aplicación de migración, las 51 pruebas nuevas, las regresiones y la recuperación real siguen pendientes; no se hicieron limpieza, restauración, commit ni push durante esta revisión.
