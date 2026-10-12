# 014 — Validación aislada de llamado y reserva y recuperación DEMO

- Fecha: **12 de octubre de 2026**.
- Alcance: servicio, modelos, persistencia privada y migración conforme a la [decisión 008](../decisiones/008-diseno-llamado-y-reserva.md).
- Preparación y procedimiento de conservación: [registro 013](013-preparacion-llamado-y-reserva.md).
- Configuración exclusiva: **`config.settings_test_migrations`**.
- Conexión real antes de escribir y al finalizar: **`test_atencion_catalogos_migraciones / atencion_test`**.
- No se conectó ni migró la base normal; durante la validación no se hizo commit ni push.

## Preparación y respaldo

Se confirmó mediante inspección del puerto y conexiones TCP de IPv4/IPv6 que **8001 estaba detenido**. Se comprobó el alias único PostgreSQL, NAME y TEST.NAME idénticos, usuario exclusivo, TEST.MIGRATE=True y MIGRATION_MODULES vacío. La conexión real confirmó la identidad anterior y READ COMMITTED. Antes de aplicar la migración había **22 migraciones aplicadas y únicamente `folios.0003_llamado_y_reserva` pendiente**; no había otras conexiones a esa base.

Se volvió a leer la migración nueva y su SQL. Sus 18 operaciones no contienen migraciones de datos; el SQL generado fue idéntico al archivo revisado en 013. Se registró privadamente la huella del archivo de migración y se volvió a comprobar al finalizar: **la migración aplicada no se reescribió**.

El respaldo seleccionado corresponde a los datos y secuencias actuales:

```text
/home/lenin/respaldo-llamado-20261012-bynba1if/test_atencion_catalogos_migraciones.dump
```

Conserva **68 506 bytes**, directorio **0700**, archivo **0600** y la huella de archivo registrada en 013. `pg_restore --list` y lectura completa hacia `/dev/null` terminaron correctamente. Se compararon los datos COPY del respaldo con las proyecciones equivalentes de las **17 tablas de datos**, mediante conteos y huellas de filas ordenadas, y los valores de las **16 secuencias**, incluida la de migraciones. El respaldo anterior correspondía; no se detectaron cambios DEMO posteriores que exigieran sustituirlo.

Manifiesto y archivos de recuperación preparados **antes de modificar el esquema o vaciar datos**, fuera del repositorio:

```text
/home/lenin/validacion-llamado-20261012-2n6gwf98/manifiesto.json
/home/lenin/validacion-llamado-20261012-2n6gwf98/datos.toc
/home/lenin/validacion-llamado-20261012-2n6gwf98/datos.sql
/home/lenin/validacion-llamado-20261012-2n6gwf98/recuperacion.sql
/home/lenin/validacion-llamado-20261012-2n6gwf98/0003.sql
```

El directorio tiene permisos **0700** y todos sus archivos y registros **0600**. El manifiesto conserva columnas originales, conteos y huellas privadas por tabla, valores/is_called, incremento, límites, caché, ciclo, propiedad y asociación de las secuencias. No se mostraron credenciales, hashes de cuentas, filas ni contenido sensible de los archivos. Los subprocesos PostgreSQL recibieron la contraseña exclusivamente en su entorno en memoria.

## Migración aplicada y conservación histórica

Se aplicó el único paso pendiente mediante `call_command("migrate", "folios", "0003_llamado_y_reserva", interactive=False)` en la conexión aislada ya verificada. Terminó correctamente. Después se comprobaron:

- **23 migraciones aplicadas y plan vacío**.
- Cuatro columnas nuevas nullable con tipos bigint/UUID previstos; datos iniciales JSONB y pausa resultado ahora nullable.
- Los tres CHECK de coherencia existentes en 0003, todos validados.
- Cuatro FK nuevas diferibles e inicialmente diferidas; ninguna restricción pública sin validar.
- Los seis índices nuevos: nombres, columnas, unicidad, validez y predicados de cola/capacidad. Los nombres y ramas exactos se conservan en 013.
- Unicidades históricas de CREACION y operador/clave conservadas.
- Conteos y huellas de las 17 tablas, proyectando sus columnas originales, idénticos al manifiesto; las cuatro referencias nuevas quedaron NULL y las 15 secuencias de datos no cambiaron por la migración.

Los registros históricos se conservaron antes de preparar las tablas para el runner. EN_ATENCION sigue fuera de los estados admitidos; su literal en el índice global no lo habilita. No se impone unicidad permanente de LLAMADO por folio ni límite de un operador por oficina.

## Ejecuciones y resultados reales

Se vaciaron explícitamente las 17 tablas de datos mediante TRUNCATE CONTINUE IDENTITY RESTRICT, dentro de una transacción, sin afectar `django_migrations` ni su secuencia. La ejecución se organizó con recuperación en un bloque `finally`: un resultado fallido del runner también conduce a recuperar DEMO, sujeto a comprobar primero el esquema final. No se inició el servidor manual durante las operaciones.

```bash
.venv/bin/python -B manage.py test folios.test_llamado folios.test_llamado_concurrencia folios.test_migracion_llamado --settings=config.settings_test_migrations --keepdb --parallel 1 --noinput --verbosity 2
.venv/bin/python -B manage.py test usuarios config.tests oficinas tramites folios --settings=config.settings_test_migrations --keepdb --parallel 1 --noinput --verbosity 2
node --check static/js/recepcion.js
node static/js/recepcion.test.cjs
```

| Ejecución | Resultado |
| --- | --- |
| Llamado, concurrencia y migración | **51 pruebas satisfactorias**, 12,459 s; salida 0. |
| Desglose de las 51 | **30 funcionales, 20 de concurrencia, 1 de migración**. |
| Regresión completa | **242 pruebas satisfactorias**, 56,739 s; salida 0. Incluye las 51 anteriores. |
| JavaScript de Recepción | **4 pruebas satisfactorias**, cero fallos, cancelaciones u omisiones; salida 0. |
| Sintaxis JavaScript | Correcta; salida 0. |

Se ejecutaron **293 casos Django contando ambas pasadas**; son **242 casos distintos de la regresión**, no 293 pruebas distintas. Las 191 pruebas Django y 4 JavaScript de la entrega anterior permanecen como evidencia anterior; los resultados de esta tabla corresponden a ejecuciones nuevas.

La concurrencia comprobó contención real con PIDs distintos y `pg_blocking_pids`, rollback del primer contendiente, selección posterior a las esperas, colas solapadas/disjuntas, claves iguales/distintas y coordinación frente a pausas, reanudación, cambio de rol, desactivación, registro y asignaciones. Las pruebas funcionales ejercieron CHECK/FK/unicidad reales, permisos y flags técnicos, comprobantes incompatibles e históricos, conservación de datos, barreras y rollback. La prueba de migración conservó eventos CREACION y comprobantes de pausa/reanudación al pasar de 0002 a 0003 y recuperó el esquema final.

Registros de los runners conservados en el directorio privado:

```text
llamado-51-t1kkhvx6.log
regresion-completa-pfc34xsk.log
javascript-sintaxis-dvhobgpr.log
javascript-4-kjqwy_um.log
```

## Recuperación DEMO efectivamente realizada

Tras los runners se comprobó el esquema de 0003, 23 migraciones y ninguna pendiente. Se registraron privadamente el historial completo y su secuencia en ese momento. La recuperación selectiva se ejecutó **una vez**, mediante psql con `-X`, `ON_ERROR_STOP=1` y `--single-transaction`; terminó con salida **0**.

El archivo recuperó exclusivamente las 17 tablas de datos: guardas de identidad e historial, constraints diferidas, TRUNCATE explícito CONTINUE IDENTITY RESTRICT, COPY con identificadores y columnas originales, **ALTER SEQUENCE RESTART de las 15 secuencias de datos**, comprobación inmediata de constraints y guardas finales. No cargó esquema del respaldo, `django_migrations` ni su secuencia; no usó CASCADE, desactivación de restricciones, triggers deshabilitados ni `--fake`. El reinicio de secuencias fue transaccional; no se ejecutaron los setval del dump.

Comprobaciones finales, reiteradas mediante conexión de solo lectura:

- **17 tablas con conteos y huellas idénticos al manifiesto**, conservando cuentas, catálogos, relaciones, folios y evidencia histórica; datos originales y llegadas incluidos en las huellas.
- Referencias nuevas de los eventos y comprobantes anteriores NULL. La carga con constraints activas y su comprobación inmediata confirmó la integridad referencial de los datos recuperados.
- **15 secuencias de datos con la próxima asignación original**, misma definición y asociación. RESTART deja is_called=False; no se exige que esa representación sea idéntica a la anterior, sino el siguiente valor. Se comprobó en lectura, sin llamar nextval.
- **Historial de migraciones y su secuencia idénticos a los registrados antes de recuperar**; 23 migraciones, ninguna pendiente, índices válidos y restricciones validadas.
- Presencia de cuenta activa RECEPCION sin is_staff ni is_superuser, y catálogos DEMO activos y compatibles, sin mostrar información de cuentas.
- **8001 sigue detenido**. No se reabrió Brave ni se realizó una nueva revisión manual.

Esto acredita la **recuperación real de los datos seleccionados sobre el esquema nuevo**, no una restauración completa del esquema viejo ni una prueba de recuperación ante cualquier fallo del servidor. El respaldo, manifiesto, SQL y registros privados se conservan.

## Incidencias y checks finales

No falló ningún caso Django ni JavaScript y **no fue necesario corregir código de aplicación o pruebas**. Hubo dos ajustes del auxiliar temporal de conservación, fuera del repositorio:

1. Una comparación inicial de COPY usaba UTC mientras pg_dump utilizaba la zona predeterminada del servidor. Se ajustó la representación de lectura para comparar datos equivalentes. Antes de resolver esa diferencia se creó una copia adicional completa en `/home/lenin/validacion-llamado-20261012-o37qchy8/test_atencion_catalogos_migraciones.dump`, que se conserva; no se utilizó para recuperar. Esa incidencia no aplicó migraciones ni modificó datos.
2. Después de la recuperación ya confirmada, una comparación textual de fechas de migraciones señaló diferencias de zona horaria. Se normalizaron los instantes a UTC y se verificó que filas e identificadores del historial y su secuencia eran iguales. **No se repitió la restauración ni los runners** para resolverlo.

```bash
PGOPTIONS='-c default_transaction_read_only=on' .venv/bin/python -B manage.py check --settings=config.settings_test_migrations
PGOPTIONS='-c default_transaction_read_only=on' .venv/bin/python -B manage.py makemigrations --check --dry-run --settings=config.settings_test_migrations
git diff --check
```

`check`: sin incidencias. Correspondencia modelos/migraciones: **No changes detected**. También se revisó formato de los archivos nuevos. La migración 0003 aplicada conserva su contenido; no se modificaron migraciones anteriores.

## Archivos de la entrega y pendientes

La validación actualiza README, decisión 008 y registro 013, y añade este registro 014. Código y pruebas preparados permanecen sin correcciones adicionales:

- `folios/models.py`, `folios/services_disponibilidad.py`, `folios/services_llamado.py` y `folios/solicitudes.py`.
- `folios/migrations/0003_llamado_y_reserva.py`.
- `folios/tests.py`, `folios/test_disponibilidad.py`, `folios/test_llamado.py`, `folios/test_llamado_concurrencia.py` y `folios/test_migracion_llamado.py`.

La validación terminó sin commit ni push; el cierre y guardado de la entrega se registra debajo. La migración se aplicó **solo en la base aislada**. Lecturas adicionales y pantallas de Operador, inicio de atención, finalización, correcciones administrativas y formato público de folio siguen fuera de alcance. Se conservan los pendientes funcionales de 008. Los datos DEMO están recuperados: **no volver a ejecutar el runner sobre ellos sin repetir la conservación**.

## Cierre de sesión — 12 de octubre de 2026

Se revisaron el diff completo y los archivos nuevos para guardar únicamente código, pruebas, migración y documentación de esta entrega con el mensaje `feat: implementa llamado y reserva con pruebas PostgreSQL`. No se repitieron pruebas, migraciones, recuperación ni limpieza, ni se cambiaron funcionalidades. Los archivos privados permanecen fuera de Git.

El auxiliar `/tmp/validar_llamado_aislado.py` se copió sin ejecutar y sin sobrescribir archivos a **`/home/lenin/validacion-llamado-20261012-2n6gwf98/validar_llamado_aislado.py`**, con permisos **0600** y contenido idéntico. Ese directorio conserva manifiesto, SQL, catálogo de recuperación y registros; los dos respaldos privados indicados arriba también se conservan.

**Punto para retomar:** lecturas autorizadas y pantallas de Operador, todavía pendientes; no se inicia esa etapa en este cierre. Se mantiene el entorno aislado con DEMO recuperado y 0003 verificada, y la base normal sin migrar en esta entrega. Antes de otra ejecución de pruebas debe repetirse la conservación de los datos manuales.
