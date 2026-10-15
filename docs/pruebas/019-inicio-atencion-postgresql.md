# 019 — Validación aislada de inicio de atención y recuperación DEMO

- Fecha: **15 de octubre de 2026**.
- Alcance: backend y migración de la [decisión 013](../decisiones/013-diseno-inicio-de-atencion.md), conforme a los [acuerdos vigentes](../acuerdos-vigentes.md).
- Punto de partida: `main` en `d1b55a1d48b7cc84c914c4df227446ed20e21e3f`, con backend, 0004 y pruebas preparados sin commit. Se conservaron los cambios locales.
- Configuración exclusiva: **`config.settings_test_migrations`**; identidad real **`test_atencion_catalogos_migraciones / atencion_test`**.
- **No se conectó ni modificó la base normal. Su migración sigue pendiente.** Sin integración de inicio en la interfaz, reinicio de servidores, commit o push.

## Revisión completa previa

Se revisaron `services_inicio.py`, `models.py`, `solicitudes.py`, 0004, los servicios de llamado/disponibilidad, las 48 pruebas nuevas y las limpiezas de migraciones existentes. El servicio revalida identidad persistida, actividad y rol OPERADOR bajo bloqueo antes de recuperar un comprobante; los flags técnicos no sustituyen el rol. Para una clave nueva exige responsabilidad vigente propia, estado admitido y, al intentar la transición, ausencia de pausa. No consulta ni exige asignación activa.

Se contrastaron los resultados: comprobante histórico antes de evaluar condiciones actuales; YA_EN_ATENCION antes de pausa para una solicitud nueva ya iniciada; EN_PAUSA sobre Llamado conserva ese resultado y requiere otra intención explícita después de reanudar. Claves incompatibles, folios ajenos y solicitudes antiguas no cambian el objetivo ni inician otro folio. Las operaciones anteriores conservan objetivo NULL y sus resultados históricos.

El UPDATE se limita a estado y fecha; llegada original, responsable y datos permanecen. Evento INICIO y comprobante usan el mismo instante y transacción. La auditoría conserva actor, responsable y oficina, con asignación autorizante NULL en INICIO; LLAMADO conserva su referencia original. Bloqueos Usuario → oficina → folio compatibles con llamado, pausa, reanudación y cambios de cuenta; no se saltan filas bloqueadas ni se libera capacidad al iniciar.

Se revisaron las ramas CHECK y sus NULL explícitos, temporalidad, unicidad global, FK protegidas y barreras públicas. La migración añade campos nullable sin reconstrucción histórica; conserva válidos CREACION, LLAMADO y todos los comprobantes anteriores. Las correspondencias entre tablas y la autorización siguen garantizadas por el servicio, no por un CHECK ordinario ni frente a SQL directo.

No se identificó un defecto de lógica que requiriera modificar el servicio, las restricciones o 0004. La única corrección de código posterior al runner fue el auxiliar del fixture de migración descrito abajo. 0004 no se reescribió después de aplicarse.

## Aislamiento, respaldo nuevo y manifiesto

Se verificaron antes de mutar: alias único PostgreSQL, NAME y TEST.NAME iguales a la base aislada, usuario `atencion_test`, TEST.MIGRATE=True y MIGRATION_MODULES vacío. Se revisaron las barreras de `oficinas/testing.py` y `DisponibilidadFixturesMixin`, que comprueban configuración e identidad real de pruebas. La conexión de solo lectura confirmó `current_database`, `current_user`, `session_user` y propietario esperados, **23 migraciones aplicadas y únicamente 0004 pendiente**.

Las comprobaciones reales de sockets/procesos confirmaron **8000 y 8001 detenidos** en IPv4/IPv6; no se detuvo ni reinició ningún servidor. No había conexiones ajenas. Estas guardas se repitieron entre fases y antes de recuperar. El auxiliar utilizó además un bloqueo de archivo para impedir dos validaciones propias simultáneas. Los intentos iniciales de sockets/PostgreSQL quedaron bloqueados por el sandbox; se repitieron con acceso local autorizado, manteniendo el destino aislado.

Directorio nuevo privado, fuera del repositorio:

```text
/home/lenin/validacion-inicio-20261015-s6alsj70/
```

Contiene `validar_inicio.py`, dump custom nuevo, manifiesto, TOC, extracción de datos, recuperación selectiva, SQL revisado, resultados e historiales. Directorio **0700**, archivos **0600**. No se publicaron credenciales, datos personales, hashes de cuentas o manifiesto; las credenciales de pruebas se transmitieron solo en memoria al entorno de subprocesos.

El respaldo nuevo tiene **75 909 bytes**. `pg_dump` utilizó un snapshot exportado desde una transacción REPEATABLE READ, READ ONLY y representación UTC. `pg_restore --list`, lectura completa hacia `/dev/null` y extracción fueron correctos. Columnas, conteos y huellas de todos los COPY coincidieron con las **18 tablas** del manifiesto; valores/is_called coincidieron para las **16 secuencias**, incluida la de migraciones. No se reutilizó ningún respaldo ni manifiesto anterior.

Las lecturas previas usaron columnas de `information_schema` y COPY/SQL compatibles con 0003, sin consultar los modelos nuevos sobre el esquema anterior. El manifiesto conservó cuentas y credenciales, sesiones, catálogos, relaciones, asignaciones, folios, eventos, pausas, comprobantes, esquema, restricciones, índices, archivos de migración y definiciones/asociaciones de secuencias.

Resumen no sensible del DEMO capturado: 3 cuentas, 1 asignación, 2 folios, 3 eventos de folio, 2 pausas, 4 eventos de disponibilidad y 5 comprobantes. Se conserva el folio Llamado de `operador_demo`, el pendiente y la evidencia manual de 018.

## Recuperación revisada antes de escribir

Se adaptó y revisó el procedimiento de [017](017-pantallas-operador-postgresql.md), utilizando exclusivamente el respaldo nuevo. El SQL recupera **17 tablas de datos mediante COPY con sus columnas anteriores** y reinicia **15 secuencias de aplicación**. Excluye `django_migrations`, su secuencia y todo el esquema. Los tres campos nuevos no se cargan desde el dump anterior y quedan NULL.

Incluye guardas de identidad y 24 migraciones con 0004, constraints diferidas, TRUNCATE explícito CONTINUE IDENTITY RESTRICT, reinicios transaccionales mediante ALTER SEQUENCE RESTART y comprobación inmediata de constraints. No usa CASCADE, setval, desactivación de restricciones/triggers, eliminación de bases ni migraciones simuladas. Los siguientes valores se calcularon desde last_value/is_called y se verificaron contra límites y máximos, sin ejecutar nextval.

Se verificaron permisos y huellas del respaldo y SQL antes de cada ciclo. El runner quedó en try/finally con recuperación también ante errores. Antes de cargar se compara el esquema de 0004 y se captura privadamente el historial y secuencia de migraciones resultantes para comprobar que la recuperación no los altera.

Una comprobación adicional inicial del SQL de recuperación rechazó de forma excesiva el nombre `oficina_contexto_id`, que ya existe en PausaOperador antes de 0004. Se corrigió la inspección para comprobar columna y tabla conjuntamente; el SQL de recuperación era correcto y no cambió. Esto ocurrió antes de las mutaciones.

## Aplicación aislada de 0004 y verificación

Se revisó el SQL generado por `sqlmigrate folios 0004` y se confirmó nuevamente que era el único cambio pendiente. Se aplicó:

```bash
.venv/bin/python -B manage.py migrate folios 0004_inicio_de_atencion --settings=config.settings_test_migrations --noinput
```

La aplicación terminó con **salida 0**. Antes del runner se verificaron:

- **24 migraciones y plan vacío**; los registros anteriores se conservaron y se añadió solo 0004.
- Tres columnas nuevas nullable, sin default: timestamp con zona horaria, bigint y UUID según el diseño.
- Dos FK nuevas diferibles/inicialmente diferidas, dos índices nuevos y el CHECK de fecha adicional; las tres restricciones de coherencia ampliadas se validaron.
- Esquema público: **99 → 102 columnas, 71 → 74 restricciones y 69 → 71 índices**. Se conservaron los índices anteriores, incluida la capacidad global y las unicidades de creación y solicitud. Todas las restricciones estaban validadas y los índices válidos/preparados.
- Las 17 tablas de datos coincidieron en sus columnas anteriores, conteos y huellas con el manifiesto; las 15 secuencias de aplicación conservaron exactamente sus valores y definiciones. Los tres campos nuevos quedaron NULL.

El primer auxiliar posterior se detuvo al comparar también `django_migrations` con el manifiesto previo. No fue un fallo de aplicación: el comando había terminado correctamente y esa tabla debía contener una fila adicional. **No se ejecutó el runner hasta corregir y completar la verificación de solo lectura**, separando los datos DEMO del historial y comprobando los registros anteriores más 0004. No se reaplicó la migración para corregir este auxiliar ni se alteró el respaldo.

## Pruebas, fallo y corrección

Los comandos Django se ejecutaron mediante el auxiliar exclusivamente sobre la base aislada, con salida a registros privados. También se ejecutaron las dos suites JavaScript existentes, sin conexión a bases:

```bash
.venv/bin/python -B manage.py test folios.test_inicio folios.test_inicio_concurrencia folios.test_migracion_inicio --settings=config.settings_test_migrations --keepdb --parallel 1 --noinput --verbosity 2
.venv/bin/python -B manage.py test folios.test_migracion_inicio --settings=config.settings_test_migrations --keepdb --parallel 1 --noinput --verbosity 2
.venv/bin/python -B manage.py test usuarios config.tests oficinas tramites folios --settings=config.settings_test_migrations --keepdb --parallel 1 --noinput --verbosity 2
node static/js/operador.test.cjs
node static/js/recepcion.test.cjs
```

| Ejecución | Resultado real |
| --- | --- |
| Primera pasada nueva | **48 casos**, 9,972 s; salida 1. Pasaron 26 funcionales/de restricciones y 20 de concurrencia; dos errores del fixture de migración. |
| Migración corregida | **2 casos satisfactorios**, 1,777 s; salida 0. |
| Regresión completa | **356 pruebas Django satisfactorias**, 61,407 s; salida 0. Incluye las 48 nuevas. |
| JavaScript existente | **4 de Operador y 4 de Recepción satisfactorias**, sin fallos u omisiones. |

Los dos errores fueron `TypeError: ... got multiple values for argument 'nombre'`: `insertar(app, nombre, **datos)` recibía tanto el nombre del modelo como el campo `nombre` de Oficina. Se cambió el argumento del auxiliar a `modelo`. No se cambiaron permisos, lógica de servicio, expectativas de preservación, restricciones ni migración. Se repitieron solo los dos casos fallidos antes de la regresión; los 46 ya satisfactorios no necesitaron una pasada dirigida adicional.

La regresión verificó otra vez los 48 casos nuevos junto con las garantías anteriores. Son **356 casos Django distintos**, no la suma de las pasadas. La concurrencia usa conexiones y PIDs distintos, sincronización explícita y espera real comprobada mediante pg_blocking_pids. Las pruebas de migración verificaron conservación de valores y reintentos anteriores, fallo simulado de DDL y recuperación de las hojas vigentes incluso tras errores; la regresión incluyó también la migración anterior de llamado.

Registros privados principales:

```text
inicio-dirigidas-moi6gwkl.log
inicio-dirigidas-13qkyaxl.log
regresion-completa-3o96j2ji.log
migrate-0004-7a7y3sat.log
sql-0004-19o11hap.log
```

## Recuperación DEMO y comprobación final

Se recuperó DEMO **dos veces**, después de la pasada fallida y al terminar la pasada corregida más la regresión. Ambas recuperaciones terminaron con salida 0 mediante psql `-X`, ON_ERROR_STOP y transacción única. Se cargaron únicamente datos y próximas asignaciones originales, sobre el esquema vigente de 0004.

Las comprobaciones de ambos ciclos y las verificaciones finales independientes de solo lectura confirmaron:

- **17 tablas de datos idénticas al manifiesto**, por columnas anteriores, conteos y huellas; cuentas, credenciales, asignación, folios y toda la evidencia manual conservados.
- **15 secuencias de aplicación con la próxima asignación original**, misma definición, propietario y asociación. RESTART puede dejar is_called=False; se compara el siguiente valor sin consumirlo.
- Nuevos `inicio_atencion`, `oficina_contexto_id` de EventoFolio y `folio_objetivo_id` de SolicitudOperador **NULL en todos los registros DEMO**.
- **Esquema de 0004 conservado, 24 migraciones y plan vacío**, restricciones validadas e índices válidos/preparados; archivos de migración con las huellas anteriores a la aplicación.
- Historial completo y secuencia de migraciones idénticos a los capturados inmediatamente antes de cada recuperación. No se cargó el historial antiguo.
- Un folio **Llamado a cargo de `operador_demo`**, cuenta activa OPERADOR, y **un pendiente sin responsable**. Se conservan las dos pausas y sus cuatro eventos.
- Puertos 8000/8001 detenidos y ausencia de conexiones ajenas. No se abrió una sesión manual ni se inició el folio DEMO.

La secuencia de migraciones partió de **28/True**, pasó a **29/True** con la aplicación inicial de 0004, a **31/True** tras la primera pasada y a **37/True** al concluir las demás pruebas. Las reversiones/reaplicaciones de los casos aislados explican los cambios de identificadores/fechas de 0003/0004. Las recuperaciones conservaron los historiales resultantes y no rebobinaron esa secuencia; los datos y 15 secuencias de aplicación se compararon contra el manifiesto nuevo original.

Esto acredita la recuperación selectiva real sobre 0004, incluso tras errores de pruebas; no una restauración completa del esquema antiguo ni una garantía ante cualquier fallo del servidor. Antes de otro runner debe preservarse nuevamente el estado vigente.

## Checks, archivos y pendientes

Después de recuperar se ejecutaron con configuración aislada y conexión de solo lectura:

```bash
PGOPTIONS='-c default_transaction_read_only=on' .venv/bin/python -B manage.py check --settings=config.settings_test_migrations
PGOPTIONS='-c default_transaction_read_only=on' .venv/bin/python -B manage.py makemigrations --check --dry-run --settings=config.settings_test_migrations
git diff --check
```

`check`: **sin incidencias**. Modelos/migraciones: **No changes detected**. Formato y enlaces locales revisados. No se reescribieron migraciones ni se amplió el alcance.

Esta revisión corrige `folios/test_migracion_inicio.py` y actualiza este registro, README y decisión 013. Los archivos de backend, 0004, pruebas y ajustes de expectativas preparados anteriormente permanecen como cambios locales, ahora con la validación descrita. Respaldo, manifiesto, SQL, auxiliar y registros siguen privados fuera de Git.

**Pendientes:** aplicación y verificación de 0004 en la base normal, nunca conectada durante esta entrega; rutas, formularios, botón Iniciar atención, exposición de su fecha en el lector e integración visual. No se integraron otras acciones ni se reiniciaron servidores. **Sin commit ni push.**
