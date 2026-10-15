# 016 — Validación de lecturas de Operador y recuperación DEMO

- Fecha: **14 de octubre de 2026**.
- Diseño: [decisión 011](../decisiones/011-lecturas-autorizadas-de-operador.md) y [acuerdos vigentes](../acuerdos-vigentes.md).
- Punto de partida: `main` sincronizada con `origin/main`, HEAD `cafdbb3ea17da85bf3b08fcdfdad103b92770194`; únicamente los dos archivos nuevos de lectores y pruebas estaban sin seguimiento.
- Configuración exclusiva: **`config.settings_test_migrations`**.
- Identidad real comprobada antes de escribir y al finalizar: **`test_atencion_catalogos_migraciones / atencion_test`**, también como `session_user`; propietario `atencion_test`.
- No se conectó la base normal ni se utilizaron sus credenciales para conexiones o subprocesos PostgreSQL. No se hizo commit ni push.

## Revisión completa

Se revisaron `folios/services_operador.py` y las 31 pruebas de `folios/test_lecturas_operador.py`, contrastándolos con la decisión 011, los acuerdos y los servicios actuales de disponibilidad, llamado, registro y asignaciones.

Los lectores parten de Usuario autenticado y persistido en el alias interno de lectura y filtran actividad y rol OPERADOR con datos de la base. La proyección de datos y la autorización se ejecutan en una sentencia SQL por lector; la fila raíz permite distinguir un resultado vacío autorizado de una denegación. Los flags técnicos no conceden acceso.

La cola utiliza asignaciones activas, sin filtros de actividad de oficina o trámite, orden por llegada original y UUID y lectura de 51 elementos para devolver hasta 50 y detectar continuación. El cursor firmado valida formato, longitud, estructura, fecha con zona y UUID; cada página vuelve a comprobar permisos y asignaciones. No otorga acceso ni determina qué ciudadano se llama.

El folio propio reutiliza el criterio global `_folios_actuales`, independiente de catálogos y asignaciones. La salida se materializa en dataclasses inmutables y tuplas con valores escalares, UUID y fechas con zona. No hay escrituras, reservas o bloqueos de filas. Se conserva `consultar_disponibilidad`, su contrato y permisos, y el comportamiento de llamado; EN_ATENCION sigue sin habilitarse.

**No se identificaron defectos que requirieran correcciones al código o a las 31 pruebas preparadas.** La validación no añadió modelos, migraciones, rutas ni pantallas.

## Aislamiento y respaldo nuevo antes del runner

Se localizaron por su nombre real los registros [013](013-preparacion-llamado-y-reserva.md), [014](014-validacion-llamado-y-reserva-postgresql.md) y [015](015-migracion-llamado-y-reserva-local.md). Se leyó el auxiliar privado conservado en 014 sin ejecutarlo: su modo de ejecución también aplica 0003, por lo que no se utilizó directamente.

Se preparó un auxiliar nuevo con las funciones de conservación revisadas y sin un paso de aplicación de migraciones previo al runner. Antes de cualquier escritura se comprobaron alias único PostgreSQL, NAME y TEST.NAME iguales al nombre aislado, usuario exclusivo, TEST.MIGRATE=True y MIGRATION_MODULES vacío. Se mantuvieron las barreras PostgreSQL existentes de las clases de prueba. La identidad real y el propietario coincidieron con la configuración; había **23 migraciones aplicadas y plan vacío**.

Se comprobó que no había servidores del proyecto activos, que los puertos **8000 y 8001** no aceptaban conexiones IPv4/IPv6 y que había **cero conexiones ajenas** a la base aislada. Estas guardas se repitieron entre fases; no se inició el servidor manual. El primer intento de inspección encontró la prohibición de sockets del aislamiento; se continuó con acceso local autorizado antes de obtener el respaldo o ejecutar pruebas.

Se creó un directorio nuevo, sin sobrescribir respaldos anteriores:

```text
/home/lenin/validacion-lecturas-20261014-nop99z82/
```

Contiene privadamente `validar_lecturas.py`, `test_atencion_catalogos_migraciones.dump`, `manifiesto.json`, `catalogo.toc`, `datos.toc`, `datos.sql`, `recuperacion.sql` y los registros de ejecución. Directorio **0700** y archivos **0600**, fuera del repositorio. No se publicaron filas, credenciales, hashes de cuentas ni contenido del manifiesto. Las contraseñas de prueba de los subprocesos PostgreSQL se pasaron solo en memoria mediante su entorno.

El respaldo completo nuevo, en formato custom, tiene **74 815 bytes**. `pg_dump` utilizó un snapshot exportado desde una transacción **REPEATABLE READ, READ ONLY**, con fechas UTC. `pg_restore --list` y la lectura completa hacia `/dev/null` terminaron con salida 0; también se extrajeron los datos a memoria sin ejecutarlos.

El manifiesto previo registró columnas, conteos y huellas de filas ordenadas de las **18 tablas**, incluidas las migraciones; valores e is_called y definiciones, límites, caché, ciclo, propietario y asociación de las **16 secuencias**; esquema, restricciones e índices y huellas de los archivos de migración. Los COPY y valores de secuencias del respaldo coincidieron con el manifiesto y se repitió la comparación antes de preparar el runner. No se llamó nextval para comprobarlos.

## Recuperación preparada y revisada antes de escribir

Se reutilizó el procedimiento comprobado de 014 sobre el esquema vigente, con extracción selectiva mediante TOC de las **17 tablas de datos**. Se excluyeron `django_migrations` y su secuencia. Se revisaron los 17 bloques COPY y los 15 ALTER SEQUENCE RESTART, y se registró privadamente la huella del archivo de recuperación.

El SQL de recuperación incluye guardas de identidad e historial, zona UTC, constraints diferidas, TRUNCATE explícito **CONTINUE IDENTITY RESTRICT**, COPY con todas las columnas e identificadores actuales, reinicios transaccionales de las 15 secuencias y comprobación inmediata de constraints. No carga esquema del respaldo ni usa CASCADE, setval, restricciones o triggers desactivados, borrado de bases o migraciones simuladas.

El siguiente valor de cada secuencia se calculó desde last_value/is_called e incremento y se comprobó contra límites y máximo identificador recuperable. RESTART conserva la próxima asignación, aunque pueda representar el estado con is_called=False.

El auxiliar organiza las pruebas dentro de un bloque `try/finally`: una vez preparadas las tablas, intenta recuperar DEMO aunque falle el runner o la escritura de sus resultados. Tras comprobar nuevamente respaldo, manifiesto, esquema y ausencia de conexiones ajenas, se vaciaron transaccionalmente solo las 17 tablas de datos para las pruebas, conservando el historial de migraciones.

## Pruebas ejecutadas y resultados reales

```bash
.venv/bin/python -B manage.py test folios.test_lecturas_operador --settings=config.settings_test_migrations --keepdb --parallel 1 --noinput --verbosity 2
.venv/bin/python -B manage.py test usuarios config.tests oficinas tramites folios --settings=config.settings_test_migrations --keepdb --parallel 1 --noinput --verbosity 2
node --check static/js/recepcion.js
node static/js/recepcion.test.cjs
```

| Ejecución | Resultado |
| --- | --- |
| Lecturas de Operador | **31 pruebas satisfactorias**, 3,296 s; salida 0. |
| Regresión completa Django | **273 pruebas satisfactorias**, 43,663 s; salida 0. Incluye las 31 nuevas. |
| JavaScript de Recepción | **4 pruebas satisfactorias**, sin fallos, omisiones o cancelaciones; salida 0. |
| Sintaxis JavaScript | Correcta; salida 0. |

Son **273 casos Django distintos** y 304 ejecuciones contando las dos pasadas; no se suman 31 y 273 como pruebas distintas. No hubo fallos de casos, correcciones ni repeticiones del runner.

La cobertura nueva verificó autorización con instancias obsoletas y combinaciones de flags, varias oficinas y operadores, antigüedad y desempate UUID, páginas de 50 y cursores inválidos, reautorización entre páginas, catálogos desactivados, asignaciones inactivas y reactivadas, folios ajenos y cola vacía autorizada. También comprobó reservas y pausas reales, conservación global del folio propio, proyecciones mínimas de disponibilidad, una consulta por lector, materialización sin consultas posteriores y ausencia de escrituras y bloqueos de reserva. Los estados históricos controlados de los fixtures no habilitan retirada pública de asignaciones o cambio de rol.

La regresión completa incluyó las pruebas existentes de concurrencia y migración. No se añadió una prueba nueva de concurrencia entre conexiones para estos lectores; la instantánea se verifica por su sentencia SQL única y los casos de relectura entre peticiones.

Registros privados:

```text
lecturas-31-9zmtr0xp.log
regresion-completa-zowu04op.log
javascript-sintaxis-x6k9qcth.log
javascript-4-nixritpu.log
```

## Recuperación DEMO comprobada

Terminadas las pruebas se verificó que el esquema coincidía con el manifiesto, con 23 migraciones aplicadas y ninguna pendiente. Se capturó privadamente el historial completo y su secuencia antes de recuperar. `psql -X --set=ON_ERROR_STOP=1 --single-transaction --file=<recuperacion.sql>` ejecutó la recuperación selectiva **una sola vez**, con salida **0**. No se cargó el esquema del respaldo.

La comprobación posterior y una segunda comprobación mediante conexión de solo lectura confirmaron:

- **17 tablas de datos con conteos y huellas idénticos al manifiesto previo**, usando todas sus columnas; cuentas, sesiones, catálogos, relaciones, folios y eventos incluidos.
- **15 secuencias de datos con la próxima asignación original**, misma definición y asociación, sin ejecutar nextval para comprobarlo.
- **Esquema original conservado**, restricciones validadas e índices válidos y preparados; archivos de migración sin cambios.
- **Historial y secuencia de migraciones idénticos a los capturados inmediatamente antes de recuperar**; mismo conjunto de 23 migraciones que al inicio y plan vacío.
- Cuenta RECEPCION activa sin flags técnicos y catálogos DEMO activos y compatibles, sin mostrar datos de cuentas.
- Ausencia de conexiones ajenas y puertos 8000/8001 detenidos. No se reinició DEMO ni se hizo revisión manual de pantallas.

La prueba existente `MigracionLlamadoTests` retrocede a 0002 y reaplica 0003 durante la regresión. Por ello cambió el identificador/fecha de **un registro existente de 0003** y `django_migrations_id_seq` pasó de **25/True a 26/True** durante las pruebas. No es una migración nueva ni un efecto de la recuperación. Esta última preservó exactamente el historial resultante y su secuencia; no restauró encima el historial previo del dump. Las 17 tablas y 15 secuencias de datos se compararon contra el manifiesto original.

Esto acredita la recuperación real de los datos seleccionados sobre el esquema vigente; no constituye una restauración completa del esquema ni una prueba ante cualquier fallo del servidor. El respaldo, manifiesto, SQL, resultados y verificaciones privadas se conservan. **DEMO está recuperado: no volver a ejecutar pruebas sin repetir su preservación.**

## Checks, archivos y pendientes

Después de recuperar se ejecutaron exclusivamente con configuración aislada y conexión de solo lectura:

```bash
PGOPTIONS='-c default_transaction_read_only=on' .venv/bin/python -B manage.py check --settings=config.settings_test_migrations
PGOPTIONS='-c default_transaction_read_only=on' .venv/bin/python -B manage.py makemigrations --check --dry-run --settings=config.settings_test_migrations
git diff --check
```

`check`: **sin incidencias**. Correspondencia modelos/migraciones: **No changes detected**. Sintaxis e importaciones utilizadas de los dos archivos nuevos y formato de los cambios correctos. No se generaron migraciones ni se modificaron modelos. No hubo incidencias de código, pruebas o recuperación ni ajustes del auxiliar posteriores al inicio del runner.

Archivos de esta entrega:

- `folios/services_operador.py` y `folios/test_lecturas_operador.py`, preparados en la etapa anterior y ahora verificados sin correcciones.
- Este registro 016, estado de la decisión 011 y README actualizados.

Quedan fuera de esta entrega pantallas, historial y filtros de Operador, inicio de atención, notas, finalización y correcciones administrativas. Se conservan las decisiones funcionales pendientes de 011 y el formato público del folio. **Sin commit ni push**; los archivos privados permanecen fuera de Git.
