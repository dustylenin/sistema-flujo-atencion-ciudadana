# 012 — Nueva atención de Recepción en PostgreSQL

- Fecha: 12 de octubre de 2026.
- Alcance aprobado e implementación: [decisión 010](../decisiones/010-nueva-atencion-recepcion.md).
- Punto de partida: `main` limpio en `105755be995012e534b4016c235968e126435fc6`, sincronizado con `origin/main` según Git local.
- Configuración exclusiva: `config.settings_test_migrations`.
- Conexión real comprobada antes del runner y al finalizar: `test_atencion_catalogos_migraciones / atencion_test`.

## Identidad, migraciones y aislamiento

Antes del primer runner se comprobaron `SETTINGS_MODULE`, PostgreSQL, `NAME`, `TEST.NAME` y usuario configurado, seguidos de `SELECT current_database(), current_user`. `MigrationRecorder` contó **22 migraciones aplicadas** y `MigrationExecutor.migration_plan(...)` devolvió un plan vacío. Antes de la regresión completa se repitieron las comprobaciones de configuración, identidad real y ausencia de pendientes. Las pruebas reutilizaron la base mediante `--keepdb`, sin aplicar migraciones pendientes.

La conexión local falló dentro del sandbox; la consulta con acceso autorizado fuera del sandbox confirmó la identidad aislada. No se conectó la base normal ni se leyeron sus cuentas o catálogos. Los fixtures se crearon exclusivamente en pruebas y no quedaron datos permanentes.

La clase nueva hereda `CatalogosPostgreSQLTestCase` y añade la exigencia de `config.settings_test_migrations` y su base exacta. Se conservan las barreras compartidas que verifican identidad real antes de los fixtures. No se debilitaron configuraciones de aislamiento.

## Comandos ejecutados y resultados

```bash
.venv/bin/python -B manage.py test folios.test_recepcion --settings=config.settings_test_migrations --keepdb --parallel 1 --noinput
.venv/bin/python -B manage.py test usuarios config.tests oficinas tramites folios --settings=config.settings_test_migrations --keepdb --parallel 1 --noinput
.venv/bin/python -B manage.py check --settings=config.settings_test_migrations
.venv/bin/python -B manage.py makemigrations --check --dry-run --settings=config.settings_test_migrations
node --check static/js/recepcion.js
node static/js/recepcion.test.cjs
git diff --check
```

| Comprobación | Resultado real |
| --- | --- |
| Primer intento del runner y `check` | Abortaron al importar el formulario: `EmailField` recibió dos argumentos `strip`. No se ejecutaron casos. |
| Ejecución de las pruebas nuevas tras corregir | **25 pruebas satisfactorias**, 2.093 s. |
| Regresión completa después de añadir la prueba de rollback desde la vista | **191 pruebas satisfactorias**, 45.034 s; incluyen las **26 pruebas nuevas**. Los conteos no se suman. |
| `check` final | `System check identified no issues (0 silenced)`. |
| Modelos/migraciones, comprobación y dry-run | `No changes detected`; ningún archivo generado. |
| Sintaxis JavaScript | Correcta, salida 0. |
| Pruebas de JavaScript con DOM y red simulados | **4 satisfactorias**: respuesta atrasada, oficina vaciada, fallos de carga y acción conservada/restauración del botón. |
| Formato | `git diff --check` correcto; archivos nuevos también comprobados sin preparar el índice. |

La corrección del formulario consiste en configurar `strip=False` en la instancia del campo de correo, pues `EmailField.__init__` ya proporciona `strip=True`; se conserva la captura y se vuelve a validar en el servicio. No se cambió `registrar_folio`.

La regresión completa emitió el aviso existente de `asgiref`: `async_to_sync was passed a non-async-marked callable`, desde pruebas anteriores. No produjo fallos.

## Cobertura HTTP y persistencia

Las 26 pruebas verifican formulario, etiquetas y salida; rechazo de anónimos y roles ajenos en todas las rutas; independencia de flags técnicos; cambio de rol y desactivación con sesión existente; filtros de oficinas y trámites; captura incompleta o inválida conservada al cargar; oficina inválida y cambio de oficina; campos obligatorios y opcionales; catálogos inexistentes, incompatibles o desactivados antes de enviar; revalidación de catálogo y rol en el servicio después del formulario; rollback ante fallo del evento desde la vista; registro completo sin ejecutar JavaScript; actor, estado, operador vacío, llegada y evento CREACION; rechazo de sustituciones de campos reservados; confirmación propia, desconocida y posterior a desactivar oficina; GET y carga sin escrituras; dos POST válidos independientes; escape en captura, catálogos y confirmación; CSRF ausente, ajeno y origen externo, tanto para carga como registro; logout; métodos y acciones inválidos; catálogo vacío y respuestas privadas sin caché.

Se usa cliente Django con middleware y sesiones reales sobre PostgreSQL. La prueba CSRF usa `Client(enforce_csrf_checks=True)`. El flujo sin JavaScript comprueba el servidor; no equivale a interacción manual en un navegador con JavaScript deshabilitado. Las pruebas JavaScript simulan DOM y red, sin afirmar una comprobación interactiva de Brave.

## Revisión visual realizada

Se renderizaron las plantillas reales con `RequestFactory`, usuario ilustrativo no persistido y opciones de catálogo en memoria, sin conectar bases; se comprobó `connection.connection is None`. El HTML temporal apuntó a CSS y JavaScript locales. Firefox **146.0.1**, headless con perfiles separados, produjo capturas del formulario de **1440 × 1350** y **390 × 1900**, y de la confirmación de **1440 × 1024**. Se observaron barra tinto, tarjetas, etiquetas, disposición apilada y botones completos sin recortes en esas capturas.

Firefox falló dentro del sandbox; las capturas se obtuvieron con la ejecución autorizada fuera del sandbox. HTML, perfiles y capturas están fuera del repositorio, en `/tmp/revision-recepcion-_h1wxfut/`. Esta revisión no inició sesión, no interactuó con controles ni registró una atención. No acredita funcionamiento de lector de pantalla, foco interactivo ni accesibilidad completa.

## Comprobaciones finales de solo lectura de la etapa automatizada

Se volvió a comprobar identidad real. Las **13 tablas** de aplicación con prefijos `usuarios_`, `oficinas_`, `tramites_`, `folios_`, más `django_session`, tenían **cero registros**; el conteo incluye las relaciones técnicas de Usuario. Los metadatos de Django se conservaron. Seguían **22 migraciones aplicadas y ninguna pendiente**.

Durante esa etapa no se modificaron modelos, migraciones, servicios de negocio, autorización compartida ni barreras de escritura. No se generaron ni aplicaron migraciones, no se crearon cuentas en la base normal y no se hizo commit, push ni preparación del índice. El conteo de cero registros corresponde a ese momento anterior a la preparación manual de datos DEMO.

## Revisión manual realizada por el usuario — 12 de octubre de 2026

El **12 de octubre de 2026**, el usuario revisó Nueva atención en **Linux Mint con Brave**, mediante el servidor **`127.0.0.1:8001`** y la base aislada **`test_atencion_catalogos_migraciones`**. Después de la etapa automatizada se prepararon una cuenta de Recepción y catálogos DEMO para esta revisión; el estado anterior sin fixtures no describe el entorno manual posterior.

| Comprobación | Resultado y evidencia |
| --- | --- |
| Ingreso con rol `RECEPCION` | Apertura de Nueva atención. |
| Selección manual de destino | Selección de oficina DEMO y trámite DEMO perteneciente a esa oficina. |
| Registro con nombre proporcionado y contactos vacíos | Registro satisfactorio con nombre proporcionado y correo y teléfono vacíos. |
| Confirmación | Muestra ciudadano, oficina, trámite, llegada, cuenta registradora y estado En espera. |
| Recarga de confirmación | Conserva la dirección y la llegada, sin solicitar reenvío; confirmado por el usuario. |
| Registrar otra atención | Regreso al formulario. |
| Nombre vacío y correo inválido | Bloqueados por la validación del navegador; comprobados mediante capturas. |
| Navegación con Tab y foco visible | Confirmados por el usuario. |
| Ventana estrecha | Sin cortes; confirmado por el usuario. |

Esta es evidencia manual comunicada por el usuario, distinta de las capturas ilustrativas previas de Firefox y de las **191 pruebas Django y 4 pruebas JavaScript satisfactorias** de la etapa automatizada. No se repitieron esas pruebas para documentar la revisión. Las capturas del bloqueo nativo acreditan la validación del navegador, sin atribuir a ese recorrido una comprobación adicional de rechazos en el servidor.

La recarga se comprobó por el comportamiento observado de la página: **no se consultaron ni verificaron conteos de registros tras recargar**. No se incluyen credenciales, datos personales ni capturas externas. Esta actualización modifica únicamente documentación; no ejecuta pruebas, migraciones ni limpieza de datos.

## Límite aprobado y comprobaciones manuales pendientes

POST satisfactorio redirige a confirmación GET: recargar esa confirmación no registra. Deshabilitar el botón con JavaScript es una ayuda visual. **Dos POST válidos crean dos atenciones independientes**, con un evento CREACION por atención; no hay garantía durable contra reintentos ni deduplicación por datos del ciudadano.

Siguen pendientes el **flujo manual completo con JavaScript deshabilitado**, la alternativa de Cargar trámites ante fallo de carga, la protección frente a respuestas atrasadas en navegador, el lector de pantalla, errores del servidor en el recorrido manual, catálogos incompatibles o desactivados, propiedad de la confirmación con otra cuenta, permisos con otros roles o cambios de cuenta y la salida desde esta pantalla, así como las demás comprobaciones manuales todavía no realizadas. La selección DEMO no acredita por sí sola todos los casos de carga dependiente. La validación administrativa del registro 011 no sustituye estas comprobaciones.

Los datos DEMO se prepararon después de la etapa automatizada exclusivamente para la revisión en la base aislada; no se inspeccionó ni modificó la base normal. Para casos negativos convienen otra cuenta RECEPCION, cuentas de otros roles, otra oficina/trámite y catálogos inactivos. No se exige operador asignado. El formato público de folio y las restantes pantallas y acciones, incluidos llamado y reserva, siguen pendientes conforme a la decisión 010.
