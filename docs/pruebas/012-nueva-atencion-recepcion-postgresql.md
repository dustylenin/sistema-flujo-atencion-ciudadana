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

## Comprobaciones finales de solo lectura

Se volvió a comprobar identidad real. Las **13 tablas** de aplicación con prefijos `usuarios_`, `oficinas_`, `tramites_`, `folios_`, más `django_session`, tenían **cero registros**; el conteo incluye las relaciones técnicas de Usuario. Los metadatos de Django se conservaron. Seguían **22 migraciones aplicadas y ninguna pendiente**.

No se modificaron modelos, migraciones, servicios de negocio, autorización compartida ni barreras de escritura. No se generaron ni aplicaron migraciones, no se crearon cuentas en la base normal y no se hizo commit, push ni preparación del índice.

## Límite aprobado y revisión manual pendiente

POST satisfactorio redirige a confirmación GET: recargar esa confirmación no registra. Deshabilitar el botón con JavaScript es una ayuda visual. **Dos POST válidos crean dos atenciones independientes**, con un evento CREACION por atención; no hay garantía durable contra reintentos ni deduplicación por datos del ciudadano.

Pendientes manuales en Linux Mint con Brave: ingreso con RECEPCION, carga dependiente y alternativa ante fallo, flujo completo con JavaScript deshabilitado, teclado y foco, lector de pantalla, adaptación en ventana real, errores, registro y recarga de confirmación, propiedad de la confirmación y salida. La validación administrativa del registro 011 no acredita esta pantalla.

Para revisar con registro real se requiere un entorno aislado autorizado, una cuenta activa RECEPCION con contraseña utilizable y al menos una oficina activa con un trámite activo asociado. Para casos negativos convienen otra cuenta RECEPCION, cuentas de otros roles, otra oficina/trámite y catálogos inactivos. No se exige operador asignado. No se prepararon esos datos manuales ni se inspeccionó su existencia en la base normal; la base de pruebas quedó sin fixtures. El formato público de folio y las restantes pantallas y acciones siguen pendientes conforme a la decisión 010.
