# 011 — Inicio de sesión y acceso por rol en PostgreSQL

- Fecha: 11 de octubre de 2026.
- Diseño: [decisión 009](../decisiones/009-inicio-de-sesion-y-acceso-por-rol.md).
- Punto de partida: `main` limpio en `aab0205065614513c68908e7dfa1350d6d594b9c`. `HEAD...origin/main` devolvió `0 0` y `git ls-remote --exit-code origin refs/heads/main` confirmó el mismo hash remoto antes de editar.
- Configuración de todas las comprobaciones de Django: `config.settings_test_migrations`.
- Conexión real antes de cualquier escritura de pruebas y al finalizar: `test_atencion_catalogos_migraciones / atencion_test`.

## Alcance comprobado

Login con `LoginView`, `AuthenticationForm` y `ModelBackend`; usuario y contraseña, error genérico, contraseña no repoblada, destinos fijos por rol y `next` ignorado. Rutas privadas protegidas por autenticación, cuenta activa y rol vigente; flags técnicos independientes. Logout exclusivamente POST con CSRF, destinos mínimos y adaptación institucional en HTML/CSS con mejora opcional en JavaScript.

No se cambiaron modelos, servicios existentes ni migraciones. No se generaron ni aplicaron migraciones, no se conectó la base normal y no se crearon cuentas permanentes. Durante la etapa de implementación y comprobaciones no se hizo commit, push ni preparación del índice; su guardado y subida corresponden a una etapa posterior autorizada.

## Identidad y plan antes de ejecutar pruebas

Se usó `manage.py shell --settings=config.settings_test_migrations -c ...` con comprobaciones de `SETTINGS_MODULE`, `NAME`, `TEST.NAME` y usuario configurado, seguidas de `SELECT current_database(), current_user`. La conexión confirmó la identidad exclusiva. `MigrationRecorder` contó **22 migraciones aplicadas** y `MigrationExecutor.migration_plan(...)` devolvió un plan vacío; se exigió ese resultado antes de usar el runner. Así, `--keepdb` reutilizó la base y no hubo migraciones pendientes que aplicar.

La nueva clase de pruebas reutiliza `CatalogosPostgreSQLTestCase`: PostgreSQL obligatorio, nombres exclusivos, usuario de pruebas y verificación por conexión real antes de los fixtures. Añade la exigencia de la configuración y el nombre específicos autorizados para esta entrega. No se debilitaron las barreras compartidas ni las configuraciones de aislamiento.

## Comandos y resultados reales

```bash
.venv/bin/python -B manage.py test usuarios.test_acceso --settings=config.settings_test_migrations --keepdb --parallel 1 --noinput
.venv/bin/python -B manage.py test usuarios config.tests oficinas tramites folios --settings=config.settings_test_migrations --keepdb --parallel 1 --noinput
.venv/bin/python -B manage.py check --settings=config.settings_test_migrations
.venv/bin/python -B manage.py makemigrations --check --dry-run --settings=config.settings_test_migrations
node --check static/js/acceso.js
git diff --check
```

| Comprobación | Resultado |
| --- | --- |
| Primera ejecución de las pruebas nuevas | 25 pruebas en 21.015 s; 1 fallo en la expectativa de la prueba de desactivación. |
| Ejecución final de las pruebas nuevas | **25 pruebas satisfactorias**, 21.320 s. |
| Suite completa posterior | **165 pruebas satisfactorias**, 41.770 s; incluyen las 25 nuevas. No se suman ambos conteos. |
| `check` | Sin incidencias: `System check identified no issues (0 silenced)`. |
| Modelos/migraciones, solo comprobación y dry-run | `No changes detected`; ningún archivo generado. |
| Sintaxis JavaScript | Correcta, salida 0. |
| Formato del diff | Correcto, salida 0. La revisión final también comprobó los archivos nuevos. |

El primer fallo no fue un acceso indebido: todas las rutas rechazaban a la cuenta desactivada. La prueba suponía incorrectamente que `ModelBackend` eliminaba el identificador interno de la sesión al desactivar una cuenta. Se corrigió la prueba para comprobar el bloqueo de las rutas y que el usuario efectivo fuera anónimo; no se cambió el comportamiento estándar de Django. Después pasaron tanto las pruebas nuevas como la suite completa.

La suite completa emitió el aviso existente de `asgiref`: `async_to_sync was passed a non-async-marked callable`, desde pruebas previas de barreras asíncronas. No hubo fallos y esta etapa no cambió esas pruebas ni sus protecciones.

## Cobertura nueva

Las 25 pruebas comprueban el formulario y sus etiquetas, los tres roles y el backend real; redirecciones desde login y raíz; rechazo de `next` interno y externo; GET sin autenticación; errores iguales para cuenta inexistente, clave incorrecta y cuenta desactivada; entrada escapada y contraseña ausente en el HTML; obligatoriedad de campos; bloqueo de anónimos y de roles ajenos; las cuatro combinaciones de flags técnicos para cada rol; desactivación y cambio de rol con una sesión existente; rechazo de un rol inyectado en sesión; renovación de sesión al entrar; CSRF ausente, de otro navegador y origen ajeno; flujo POST completo sin ejecutar JavaScript; rotación de CSRF; métodos prohibidos en logout; rechazo del token anterior al login; destrucción de sesión e ignorar `next` al salir; exposición mínima en destinos; respuestas sin caché; ausencia de rutas de registro, contraseñas y panel técnico.

Son pruebas HTTP con cliente Django, middleware, sesiones y PostgreSQL; las de CSRF usan `Client(enforce_csrf_checks=True)`. El cliente no ejecuta JavaScript: el flujo satisfactorio verifica que el servidor no depende del script. No equivale a un ensayo interactivo del navegador con JavaScript deshabilitado.

## Comprobaciones finales de solo lectura

Una nueva consulta de identidad real confirmó nuevamente la base y el usuario autorizados. Se contaron por SQL todas las tablas de aplicación con prefijos `usuarios_`, `oficinas_`, `tramites_` y `folios_`, incluidas las relaciones técnicas de Usuario, y `django_session`. Las **13 tablas consultadas tenían cero registros**. No quedaron cuentas ficticias, datos de aplicación ni sesiones. Los metadatos de Django se conservan.

`MigrationRecorder` y `MigrationExecutor` volvieron a confirmar **22 migraciones aplicadas y ninguna pendiente**. El contraste de Git confirmó que Usuario, sus managers, oficinas, trámites, Folio, EventoFolio, servicios existentes, configuraciones de aislamiento y migraciones anteriores no tienen modificaciones.

## Revisión visual realmente realizada

Se renderizó el GET de `AccesoView` con `RequestFactory`, usuario anónimo y host `localhost`, sin conectar ninguna base. El HTML temporal apuntó al CSS y JavaScript locales. Con Firefox 146.0.1 en modo headless y perfiles temporales separados se capturaron y observaron imágenes de **1440 × 1024** y **390 × 844**. Se revisaron los dos paneles de escritorio, la disposición apilada móvil, legibilidad, paleta, campos, botón y orientación, sin recortes visibles en esas capturas. La casilla se mostró al cargarse JavaScript.

Las capturas y perfiles quedaron fuera del repositorio, en `/tmp/revision-acceso-w1w0a0e5/`. Esta revisión del HTML renderizado no inició sesión ni probó controles mediante interacción. El código del SVG externo utilizado y el alcance de su aprobación se identifican en la decisión 009.

## Revisión manual realizada por el usuario

El **11 de octubre de 2026**, el usuario realizó una revisión interactiva en **Linux Mint con Brave** y confirmó:

- Mostrar y ocultar contraseña funciona.
- La navegación con Tab y el foco visible funcionan.
- El formulario se adapta al reducir la ventana.
- Las credenciales inválidas muestran un error genérico, conservan el usuario y vacían la contraseña.

Estos resultados son la revisión manual comunicada por el usuario, distinta de las capturas previas de Firefox y de las **165 pruebas automatizadas existentes, que incluyen las 25 nuevas**. No se repitieron pruebas automatizadas para registrar esta revisión ni se modificó su conteo. Esta actualización modifica únicamente documentación; no crea cuentas ni conecta bases.

### Validación manual de acceso administrador — 12 de octubre de 2026

El **12 de octubre de 2026**, el usuario realizó la validación en **Linux Mint con Brave**:

| Comprobación | Resultado y evidencia |
| --- | --- |
| Inicio de sesión válido con una cuenta activa de rol `ADMINISTRADOR` | Llegada a `/administracion/`, confirmada mediante captura. |
| Cerrar sesión | Regresa al inicio de sesión; confirmado por el usuario. |
| Abrir `/administracion/` sin sesión | Exige autenticación; confirmado por el usuario. |
| Volver a iniciar sesión | Permite regresar a Administración; confirmado por el usuario. |

Administración es una **pantalla inicial**, no el panel completo: esta validación no acredita las funciones administrativas previstas. El registro conserva únicamente los resultados y el tipo de evidencia, sin credenciales, hashes de contraseñas, datos de cuentas, archivos `.env` ni exportaciones de la base de datos. No se repitieron pruebas automatizadas ni se cambió su conteo para documentar esta validación.

## Límites y siguientes comprobaciones

Quedan pendientes las pruebas manuales de los roles Recepción y Operador, incluidos el ingreso con una cuenta válida, sus destinos y el cierre de sesión, así como las demás comprobaciones manuales todavía no realizadas. **No se declaran comprobados el lector de pantalla ni el funcionamiento manual sin JavaScript**; ambos siguen pendientes. Durante la etapa de implementación la base normal no se inspeccionó para averiguar cuentas y no se crearon cuentas en ella. La pantalla puede abrirse anónimamente siguiendo el README.

La primera pantalla de recepción y sus acciones siguen pendientes. El llamado y reserva permanecen en diseño; esta entrega no verifica casos reales en Llamado o En atención, notas, cierre ni correcciones administrativas. Se conservan las evidencias anteriores y sus límites.
