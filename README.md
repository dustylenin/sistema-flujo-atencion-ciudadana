# Sistema de Flujo de Atención Ciudadana

Proyecto profesional de portafolio para diseñar un sistema interno que permita administrar y dar seguimiento a la atención de ciudadanos en una red de oficinas de una dependencia.

El sistema busca mantener un registro trazable desde la recepción hasta el resultado de la atención, con acceso según el rol y los permisos de cada usuario.

## Estado del proyecto

**Etapa actual: lecturas autorizadas de Operador implementadas y verificadas en PostgreSQL aislado; DEMO recuperado.** El [registro 016](docs/pruebas/016-lecturas-operador-postgresql.md) documenta 31 pruebas nuevas y la regresión completa de 273 pruebas Django, incluidas esas 31, además de 4 JavaScript satisfactorias; respaldo nuevo privado, recuperación de 17 tablas y próximas asignaciones de 15 secuencias verificadas. No se conectó la base normal ni se añadieron migraciones, rutas o pantallas.

El [registro 015](docs/pruebas/015-migracion-llamado-y-reserva-local.md) documenta la aplicación anterior y exclusiva de `folios.0003_llamado_y_reserva` en `atencion_ciudadana / atencion_app`: **23 migraciones aplicadas y ninguna pendiente**, respaldo completo privado verificado y conservación de las 17 tablas de datos y 15 secuencias de aplicación, incluida la cuenta administradora y sus credenciales. Solo se añadió el registro de 0003 al historial y avanzó su secuencia. Los checks fueron satisfactorios; no se ejecutaron pruebas ni se crearon datos en la base normal, y no se conectó ni alteró DEMO durante aquella aplicación.

La [decisión 008](docs/decisiones/008-diseno-llamado-y-reserva.md) conserva el diseño revisado. La validación anterior aplicó `folios.0003_llamado_y_reserva` exclusivamente en `test_atencion_catalogos_migraciones / atencion_test`: **23 migraciones y ninguna pendiente**. Pasaron **51 pruebas nuevas y la regresión completa de 242 pruebas, que incluye esas 51**, además de **4 pruebas JavaScript** de Recepción. El [registro 014](docs/pruebas/014-validacion-llamado-y-reserva-postgresql.md) documenta esa aplicación, checks, incidencias del auxiliar temporal y recuperación transaccional de datos/secuencias sobre el esquema nuevo, conservando el historial de migraciones. El [registro 013](docs/pruebas/013-preparacion-llamado-y-reserva.md) mantiene la preparación, revisión y procedimiento anteriores. DEMO vuelve a estar presente y 8001 sigue detenido; no repetir el runner sin conservar nuevamente sus datos. Durante aquella validación aislada no se conectó ni migró la base normal.

La entrega anterior de Recepción quedó implementada, comprobada en pruebas aisladas y revisada manualmente de forma parcial, incluido el registro sin JavaScript. La [decisión 010](docs/decisiones/010-nueva-atencion-recepcion.md) describe Nueva atención, selección manual de oficina/trámite activos, uso exclusivo de `registrar_folio`, confirmación propia y carga sin JavaScript. Su regresión completa pasó con **191 pruebas, incluidas las 26 nuevas de Recepción**, y pasaron **4 pruebas de JavaScript**; esos resultados anteriores no acreditan llamado ni una nueva ejecución. En esa entrega no se cambiaron modelos, servicios ni migraciones. El [registro 012](docs/pruebas/012-nueva-atencion-recepcion-postgresql.md) conserva las evidencias y los pendientes. Recargar la confirmación no registra; **dos POST válidos generan atenciones independientes**, sin deduplicación por datos del ciudadano.

El acceso de la [decisión 009](docs/decisiones/009-inicio-de-sesion-y-acceso-por-rol.md) se conserva. El usuario confirmó el 11 de octubre de 2026 en Linux Mint con Brave contraseña visible/oculta, Tab, foco, adaptación y error genérico; el 12 de octubre validó ingreso de una cuenta activa ADMINISTRADOR, salida, protección sin sesión y reingreso. Administración sigue siendo una pantalla inicial. El [registro 011](docs/pruebas/011-inicio-de-sesion-y-acceso-postgresql.md) conserva esas evidencias, sin extenderlas a Recepción u Operador.

Las lecturas autorizadas de Operador de la [decisión 011](docs/decisiones/011-lecturas-autorizadas-de-operador.md) están implementadas y verificadas: cola conjunta paginada de 50 elementos con cursor firmado, folio actual propio global y reutilización de disponibilidad, sin reservas ni escrituras. La autorización y los datos comparten una instantánea por lector, con resultados inmutables y materializados. El punto para retomar son las pantallas de Operador, todavía pendientes; historial, inicio y finalización quedaron fuera de esta entrega. Servicio, modelos, migración y pruebas de llamado conservan las verificaciones anteriores de los registros 014 y 015. No se habilitan pantallas de llamado ni EN_ATENCION mediante estas lecturas. DEMO está recuperado: no repetir el runner sin conservar nuevamente sus datos.

La primera entrega de pausa, reanudación y disponibilidad está implementada, revisada en PostgreSQL de pruebas y con `folios.0002` aplicada y verificada localmente. Incluye consultas por rol, disponibilidad derivada y persistencia conjunta de pausa, evento y comprobante, con autorización vigente, solicitudes repetidas y barreras del ORM reutilizadas. Con `config.settings_test_migrations`, la conexión real confirmó `test_atencion_catalogos_migraciones` y `atencion_test`. Pasaron **37 pruebas nuevas, incluidas 12 de concurrencia, y la suite completa de 140 pruebas que incluye esas 37**; los conteos no se suman. `check`, correspondencia modelos/migraciones y formato fueron correctos. La inspección verificó 3 tablas nuevas, 22 columnas, 19 restricciones y 15 índices, **22 migraciones aplicadas sin pendientes en pruebas** y cero datos residuales de aplicación. La revisión crítica posterior no encontró defectos, no modificó archivos ni ejecutó nuevas pruebas. El [registro de pausas y disponibilidad](docs/pruebas/009-pausas-disponibilidad-postgresql.md) conserva comandos, correcciones previas, resultados y límites.

La etapa anterior de registro inicial de folios quedó implementada y revisada en PostgreSQL de pruebas, con su migración aplicada y verificada localmente. Recepción registra con UUID interno, estado En espera y operador vacío; folio y evento CREACION se guardan en una misma transacción. En `test_atencion_catalogos_migraciones`, con `config.settings_test_migrations` y `atencion_test`, quedaron entonces **21 migraciones reales aplicadas y sin pendientes**. La suite completa pasó con **102 pruebas, incluidas 28 de folios, antes de la corrección del descriptor inverso**. La regresión confirmó el defecto al seleccionar nuevamente el manager relacionado; después de corregirlo pasaron las **3 pruebas afectadas**, sin repetir la suite completa ni sumar ambos conteos. La inspección verificó 2 tablas nuevas, 18 columnas, 11 restricciones y 9 índices, sin datos residuales de aplicación. El [registro de folios](docs/pruebas/007-registro-inicial-folios-postgresql.md) conserva comandos, resultados y límites.

La etapa anterior de asignaciones implementó `AsignacionOperadorOficina`, `EventoAsignacion` y servicios autorizados por administrador funcional, con eventos durables y transacción conjunta. En pruebas quedaron entonces 20 migraciones reales aplicadas y sin pendientes. Su suite completa pasó con **74 pruebas antes del ajuste final de concurrencia**; después se reforzó la sincronización y pasaron las **3 pruebas afectadas**, sin repetir la suite completa. El [registro de asignaciones](docs/pruebas/005-asignaciones-postgresql.md) conserva ambas verificaciones como evidencia anterior.

Las migraciones de catálogos y asignaciones ya están aplicadas y verificadas en `atencion_ciudadana`, con `config.settings` y `atencion_app`: la evidencia de esa etapa registró **20 migraciones aplicadas y plan sin pendientes**. Las dos migraciones de asignaciones terminaron correctamente; la de Usuario cambia opciones de managers sin cambios físicos de esquema. La inspección de lectura verificó 2 tablas nuevas, 11 columnas, 8 restricciones y 7 índices, con cero filas en asignaciones y eventos y `check` sin incidencias. El [registro de aplicación local de asignaciones](docs/pruebas/006-migraciones-asignaciones-local.md) conserva la ejecución. La etapa posterior aplicó **`folios.0001_initial`** con el código del commit `2d690da`, después de confirmar la conexión real y que era la única pendiente. Quedaron **21 migraciones aplicadas y plan vacío**, con `check` satisfactorio, 2 tablas nuevas, 18 columnas, 11 restricciones y 9 índices; ambas tablas tenían cero filas. La comparación inicial de tipos requirió normalizar los alias equivalentes `varchar` y `character varying`, tras lo cual la inspección pasó sin diferencias. El [registro de aplicación local de folios](docs/pruebas/008-migracion-folios-local.md) conserva la ejecución, sin pruebas sobre esa base, datos de ejemplo ni cambios de permisos. Las demás acciones de folios, pantallas, gestión funcional de cuentas y auditoría global siguen pendientes.

Tras aplicar las migraciones de usuarios, las comprobaciones de Django fueron satisfactorias: `check` no detectó problemas, `showmigrations` mostró todas las migraciones aplicadas, `migrate --plan` no mostró operaciones pendientes y `makemigrations --check --dry-run` no detectó cambios de modelos en esa etapa. Las pruebas puntuales comprobaron la creación y recuperación de usuarios de los tres roles, la unicidad de `username`, las restricciones del rol y la conservación del registro al desactivar una cuenta. Todas las operaciones con usuarios ficticios se revirtieron: quedaron cero usuarios y no se creó ninguna cuenta permanente. Los resultados y el alcance están en el [registro de validación en PostgreSQL](docs/pruebas/001-usuarios-postgresql.md).

La [decisión de servicios de asignación y actividad](docs/decisiones/003-servicios-de-asignacion-y-actividad.md) describe el alcance implementado: creación y reactivación por administrador funcional autenticado y activo, relectura de su estado en la base, resultados explícitos, bloqueos y protecciones del ORM. Retirada y cambio efectivo desde `OPERADOR` están bloqueados provisionalmente hasta verificar sus reglas completas con folios reales. Los eventos cubren únicamente creación y reactivación; no constituyen la auditoría completa del sistema. Las 42 pruebas de la etapa anterior se conservan como evidencia de usuarios, catálogos y configuración de migraciones.

El **11 de octubre de 2026** se aprobaron la disponibilidad y el máximo de un folio actual por operador, contando todas sus oficinas, en la [decisión 006](docs/decisiones/006-disponibilidad-y-folio-actual-del-operador.md). La primera entrega implementa pausa, reanudación y consultas de disponibilidad conforme al [diseño 007](docs/decisiones/007-diseno-pausas-y-disponibilidad.md), conservando Folio, EventoFolio y las evidencias anteriores. La entrega posterior implementó y verificó el servicio de llamado y reserva conforme al registro 014, y su migración está aplicada y verificada en la base normal conforme al registro 015.

El **11 de octubre de 2026** se aplicó `folios.0002` en `atencion_ciudadana`, con `config.settings` y conexión real `atencion_app`, desde Git limpio en `04659c8`. Antes había 21 migraciones aplicadas y esa era la única pendiente; se revisaron el plan y SQL y la aplicación terminó con `OK`. Después quedaron **22 migraciones aplicadas y ninguna pendiente**, con `check` satisfactorio antes y después y sin diferencias de modelos/migraciones. La inspección de solo lectura verificó **3 tablas nuevas, 22 columnas, 19 restricciones y 15 índices**, tipos, nulabilidad y referencias coincidentes, índices válidos, restricciones validadas y cero registros en las tres tablas. El esquema de Folio y EventoFolio permaneció idéntico al capturado antes. No se ejecutaron pruebas en esa base ni se crearon datos de ejemplo. El [registro de aplicación local de pausas y disponibilidad](docs/pruebas/010-migracion-pausas-disponibilidad-local.md) conserva los comandos, resultados y el intento inicial de conexión bloqueado por aislamiento.

La **segunda entrega de llamado y reserva está implementada y verificada en la base aislada, y su migración aplicada y comprobada en la base normal**, conforme a la [decisión 008](docs/decisiones/008-diseno-llamado-y-reserva.md) y los registros 014 y 015. Integra llamado y reserva con pausa y el límite global de un folio actual. Los casos de Ocupado y contexto desde Llamado se verificaron en las pruebas aisladas; esa evidencia no es una ejecución funcional en la base normal. Las lecturas mínimas de Operador están verificadas conforme al registro 016. Pantallas, historial de Operador, inicio, notas, cierre y correcciones administrativas siguen pendientes, al igual que los permisos ampliados, la presentación de pausas sin oficina y el significado de Inactivo. En atención y notas se verificarán cuando se implementen.

## Tecnologías elegidas

- Interfaz: HTML, CSS y JavaScript con plantillas de Django.
- Servidor: Python con Django **5.2.17 LTS**, con soporte extendido hasta abril de 2028 según la [política oficial](https://www.djangoproject.com/download/).
- Base de datos: PostgreSQL **16.15** funcionando en el entorno local verificado. La recomendación inicial de PostgreSQL **18.6** no describe la instalación actual; ambas ramas figuran en la [política oficial de versiones](https://www.postgresql.org/support/versioning/).
- Python recomendado: **3.14.8**. El entorno virtual local se creó con **3.12.3**, disponible en Linux Mint 22.3. Django 5.2 admite ambas ramas según su [documentación de compatibilidad](https://docs.djangoproject.com/en/5.2/releases/5.2/#python-compatibility). La comprobación local no valida todavía Python 3.14.
- Conexión PostgreSQL: Psycopg **3.3.6**, con paquete binario para desarrollo local; carga de `.env`: python-dotenv **1.2.4**. Las dependencias están fijadas en `requirements.txt`.

## Estructura inicial

```text
config/          Configuración, rutas de acceso y entradas ASGI/WSGI
usuarios/        Usuario, acceso, protecciones de rol y pruebas
oficinas/        Catálogo, asignaciones, eventos, servicios y pruebas
tramites/        Catálogo de trámites con oficina fija y pruebas
folios/          Registro inicial, pausas, disponibilidad, llamado/reserva y pruebas
docs/            Documentación del producto conservada
templates/       Acceso, Nueva atención, confirmación y destinos mínimos restantes
static/css/      Estilos institucionales responsivos de acceso y Recepción
static/js/       Mejoras opcionales de acceso y trámites dependientes; pruebas JS
static/img/      Carpeta reservada para imágenes
manage.py        Comandos de Django
requirements.txt Dependencias del entorno
.env.example     Variables de ejemplo sin credenciales reales
.gitignore       Excluye entorno virtual, secretos y archivos generados
```

`AUTH_USER_MODEL` apunta a `usuarios.Usuario`, basado en `AbstractUser`, conforme a la [decisión aprobada de usuarios y asignaciones](docs/decisiones/001-usuarios-y-asignaciones.md). Conserva `username` como identificador de acceso y los campos heredados. La autorización funcional de creación/reactivación de asignaciones está implementada en servicios; el acceso y Nueva atención ya existen. Las restantes pantallas de trabajo y los demás permisos funcionales siguen pendientes.

El campo `rol` es obligatorio, sin valor predeterminado, y admite `ADMINISTRADOR`, `RECEPCION` u `OPERADOR`. `create_user()` y `create_superuser()` exigen el argumento explícito `rol`; los valores vacíos o inválidos se rechazan antes de guardar. El guardado directo también valida el rol. En PostgreSQL ya se comprobaron `UNIQUE (username)`, `NOT NULL` de `rol` y la restricción `usuarios_usuario_rol_valido` para los tres roles, incluidos intentos mediante `update()` que omiten la validación de `save()`.

`rol`, `is_active`, `is_staff` e `is_superuser` son independientes. El manager conserva el comportamiento técnico de Django al crear superusuarios, sin asignarles automáticamente el rol `ADMINISTRADOR`. El acceso implementado comprueba cuenta activa y rol vigente en cada petición; `is_staff` e `is_superuser` no conceden permisos funcionales. No se habilita el panel técnico de Django.

`REQUIRED_FIELDS` conserva los campos de `AbstractUser` y añade `rol`: cuando se autorice usar `createsuperuser`, el modo interactivo solicitará el rol y el modo no interactivo requerirá `--rol` o `DJANGO_SUPERUSER_ROL`. Esto no crea una cuenta ahora ni habilita gestión de contraseñas. La creación de cuentas desde Usuarios y la gestión exclusiva de contraseñas por el administrador siguen pendientes de implementación.

## Revisar Nueva atención en Linux Mint

Para una prueba manual con registro real, preparar mediante una acción autorizada una cuenta activa de rol `RECEPCION` con contraseña utilizable y una oficina activa con un trámite activo asociado, en un entorno aislado. No se necesita operador asignado. Esta entrega no creó datos manuales: los fixtures de pruebas se limpiaron y no se inspeccionó la base normal. La gestión de cuentas y catálogos mediante pantallas todavía no está implementada.

Con la base aislada y su configuración ya preparadas, se puede servir:

```bash
DJANGO_DEBUG=true .venv/bin/python -B manage.py runserver 127.0.0.1:8000 --settings=config.settings_test_migrations
```

Abrir `http://127.0.0.1:8000/acceso/` en Brave; entrar con RECEPCION lleva a `/recepcion/`. Probar carga, validaciones, registro y recarga de confirmación; repetir con JavaScript deshabilitado. Otra cuenta de Recepción no debe abrir esa confirmación. Este comando sirve la configuración aislada, sin ejecutar migraciones; cada registro válido sí escribe en esa base. Evitar ejecutar la suite mientras se realiza la revisión manual, pues limpia los datos de pruebas. Las capturas ilustrativas y comprobaciones automatizadas no sustituyen estos pasos.

## Abrir el inicio de sesión en Linux Mint

Desde la carpeta del proyecto, con el entorno virtual, las variables locales y PostgreSQL ya preparados:

```bash
DJANGO_DEBUG=true .venv/bin/python -B manage.py runserver 127.0.0.1:8000 --settings=config.settings
```

Abrir **http://127.0.0.1:8000/acceso/** en Firefox u otro navegador. La depuración se activa solo para este servidor de desarrollo ligado a la interfaz local, permitiendo servir CSS y JavaScript con `runserver`. Detener con `Ctrl+C`. Este comando está documentado para uso local; no se ejecutó contra la base normal durante la entrega.

La pantalla puede abrirse sin cuenta. Para iniciar sesión se requiere una cuenta activa con usuario, contraseña asignada por el administrador y uno de los tres roles funcionales. La aplicación documentada en el registro 015 confirmó la conservación de una cuenta activa ADMINISTRADOR y de sus credenciales en la base normal, sin crear cuentas ni mostrar secretos. No se necesita un superusuario técnico. La gestión de cuentas y contraseñas mediante pantallas sigue pendiente; cualquier preparación adicional será una acción separada autorizada.

El acceso dirige a `/recepcion/`, `/operacion/` o `/administracion/`. Recepción incluye Nueva atención y su confirmación conforme a la decisión 010 y el registro 012; Operación y Administración conservan destinos iniciales con identidad y cierre de sesión. El formulario funciona sin JavaScript; con él se habilita mostrar/ocultar contraseña. No hay registro público, recuperación ni cambio obligatorio de contraseña; las pantallas de llamado siguen pendientes. La referencia visual y la revisión del acceso se documentan en la decisión 009 y el registro 011.

## Preparación en Linux Mint

Ejecutar desde la raíz del repositorio. Para usar el Python de la distribución:

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
```

Si Python 3.14.8 ya está instalado, crear un entorno virtual nuevo con `python3.14 -m venv .venv` en lugar de `python3 -m venv .venv`, sin reemplazar el Python del sistema. Si ya existe un entorno con otra versión, conservarlo o moverlo antes de crear el nuevo. Usar la última revisión de mantenimiento de la rama elegida al actualizar el entorno.

PostgreSQL es un servicio independiente; instalar Psycopg no instala el servidor. El entorno local ya tiene PostgreSQL 16.15 funcionando. Para preparar otra instalación con la rama 16, usar los paquetes disponibles para la base Ubuntu de Linux Mint (Mint 22.3 usa `noble`, no `zena`). Si hace falta configurar un repositorio, seguir la [guía oficial para Ubuntu](https://www.postgresql.org/download/linux/ubuntu/):

```bash
sudo apt install postgresql-16 postgresql-client-16
psql --version
pg_lsclusters
```

En una instalación nueva, preparar una base vacía y un usuario local con contraseña desde `sudo -u postgres psql`. Omitir este paso si ya existen, como en el entorno verificado:

```sql
CREATE ROLE atencion_app LOGIN;
\password atencion_app
CREATE DATABASE atencion_ciudadana OWNER atencion_app;
\q
```

`\password` solicita la contraseña de forma interactiva, sin incluirla en el comando. Esto prepara la conexión; no crea tablas de Django.

Copiar la configuración de ejemplo únicamente si `.env` no existe, conservando los valores de un archivo local existente:

```bash
cp -n .env.example .env
chmod 600 .env
nano .env
```

Configurar estos valores en `.env`; los marcadores de secretos son ejemplos y deben sustituirse localmente, sin publicarlos:

```dotenv
DJANGO_SECRET_KEY=REEMPLAZAR_CON_CLAVE_ALEATORIA
POSTGRES_DB=atencion_ciudadana
POSTGRES_USER=atencion_app
POSTGRES_PASSWORD='REEMPLAZAR_CON_MI_CONTRASENA'
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
```

Para generar y guardar directamente una clave aleatoria, sin mostrarla y conservando una clave ya configurada, usar el entorno virtual activo:

```bash
python - <<'PY'
from django.core.management.utils import get_random_secret_key
from dotenv import dotenv_values, set_key

key = dotenv_values('.env').get('DJANGO_SECRET_KEY')
if key in (None, '', 'REEMPLAZAR_CON_CLAVE_ALEATORIA'):
    set_key('.env', 'DJANGO_SECRET_KEY', get_random_secret_key())
PY
chmod 600 .env
git check-ignore -v -- .env
```

Mantener secretos únicamente en `.env`, ignorado por Git y con permisos de lectura y escritura exclusivos del propietario. Las variables exportadas en el entorno tienen prioridad sobre ese archivo. `DJANGO_DEBUG` acepta `true` o `false`; el ejemplo activa depuración solo para desarrollo local. `DJANGO_ALLOWED_HOSTS` usa valores separados por comas. La configuración rechaza claves o credenciales obligatorias vacías y utiliza PostgreSQL, sin alternativa automática a SQLite. No intentar conectar mientras haya marcadores de secretos.

### Conexión local verificada

PostgreSQL local **16.15** está funcionando con la base `atencion_ciudadana`, el usuario `atencion_app` y el destino `127.0.0.1:5432`. Desde el entorno virtual y la configuración real de Django, sus comprobaciones finalizaron sin incidencias y `django.db.connection` ejecutó `SELECT 1`, que devolvió **1**. La conexión confirmó la base y el usuario indicados. `.env` sigue ignorado por Git; no se publicaron contraseñas ni la clave de Django.

Para reproducir únicamente la comprobación de conexión, después de completar `.env` y activar el entorno virtual:

```bash
python manage.py check
python manage.py shell -c 'from django.db import connection; cursor = connection.cursor(); cursor.execute("SELECT 1"); print(cursor.fetchone()[0]); cursor.close(); connection.close()'
```

Estas comprobaciones no generan ni aplican migraciones y no verifican la persistencia del modelo ni sus restricciones.

### Comprobaciones sin base de datos

Con las variables completas, las comprobaciones sin acceso a la base son:

```bash
python -m pip check
python -m compileall -q manage.py config usuarios oficinas tramites
python manage.py check
python manage.py test usuarios.tests config.tests oficinas.tests.CatalogosSinBaseTests --verbosity 2
git diff --check
```

`manage.py check` por sí solo no demuestra que exista conexión a PostgreSQL; esa conexión se comprobó separadamente con `SELECT 1`. Las ocho pruebas de usuarios existentes usan `SimpleTestCase`, prohíben consultas a la base e interceptan los guardados válidos: no crean cuentas ni una base de pruebas y no comprueban las restricciones del servidor PostgreSQL.

### Pruebas de oficinas y trámites en PostgreSQL

La etapa anterior terminó con **37 pruebas satisfactorias: 19 con PostgreSQL y 18 sin base de datos**, sin errores ni fallos. Utilizó exclusivamente la base `test_atencion_catalogos_revision`, preparada previamente por el usuario, con `atencion_test` como usuario y propietario en `127.0.0.1:5432`. Se confirmó que ese usuario no tiene `SUPERUSER`, `CREATEDB` ni `CREATEROLE`. No se modificaron `atencion_ciudadana` ni los permisos de `atencion_app`. El [registro de validación de oficinas y trámites](docs/pruebas/002-oficinas-tramites-postgresql.md) conserva los casos y sus límites como evidencia de la etapa con `MIGRATE=False`.

Para preparar otro entorno por primera vez, ejecutar en una terminal administrativa; omitir la creación si ya existen, como en el entorno verificado:

```bash
sudo -u postgres psql -v ON_ERROR_STOP=1 -d postgres
```

Dentro de `psql`:

```sql
CREATE ROLE atencion_test WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
\password atencion_test
CREATE DATABASE test_atencion_catalogos_revision OWNER atencion_test;
\q
```

`\password` solicita la contraseña de forma interactiva. Estos comandos no cambian `atencion_app` ni sus permisos. Si el usuario o la base ya existen, revisar su configuración antes de repetir su creación.

Completar localmente las variables `TEST_POSTGRES_*` de `.env.example` en el `.env` existente, sin sustituir las variables del proyecto: `TEST_POSTGRES_DB=test_atencion_catalogos_revision`, `TEST_POSTGRES_USER=atencion_test`, `TEST_POSTGRES_HOST=127.0.0.1`, `TEST_POSTGRES_PORT=5432` y `TEST_POSTGRES_PASSWORD` con la contraseña introducida. No guardar secretos en Git. La configuración general de Django de `.env` también es necesaria.

Después de esa preparación, desde la raíz del repositorio:

```bash
.venv/bin/python -B manage.py check --settings=config.settings_test
.venv/bin/python -B manage.py test usuarios config.tests oficinas tramites --settings=config.settings_test --keepdb --parallel 1 --noinput --verbosity 2
```

`NAME` y `TEST.NAME` coinciden. La configuración rechaza cualquier otro nombre de base, una coincidencia con la base del proyecto, un usuario distinto de `atencion_test` y una contraseña de pruebas vacía; no tiene alternativa a las credenciales de la aplicación. `--keepdb` reutiliza y conserva la base preparada y `--parallel 1` evita crear bases adicionales. Los datos de esta base son exclusivos de las pruebas y el ejecutor puede limpiarlos. Si no está preparada o faltan permisos, las pruebas deben detenerse; no se concederá `CREATEDB` al usuario.

Las 37 pruebas anteriores usaron `TEST.MIGRATE=False`: Django preparó las tablas desde los modelos en la base de pruebas, por lo que **no verificaron los archivos de migración de oficinas y trámites** ni aplicaron migraciones a la base del proyecto. La configuración de esa suite conserva `MIGRATE=False`.

Posteriormente se generaron `oficinas/migrations/0001_initial.py` y `tramites/migrations/0001_initial.py` con `.venv/bin/python -B manage.py makemigrations oficinas tramites`. Ambas contienen una operación `CreateModel`; la de trámites depende de `oficinas.0001_initial`. Se revisaron campos obligatorios, relación con `PROTECT`, restricciones de contenido y unicidad normalizada incluyendo inactivos. `check`, `makemigrations --check --dry-run` y `git diff --check` fueron satisfactorios; `sqlmigrate` permitió inspeccionar el SQL sin ejecutarlo. No hubo cambios en usuarios ni operaciones previstas sobre tablas existentes. Su aplicación real se verificó en la segunda base exclusiva de pruebas y, después, **ambas migraciones se aplicaron y verificaron en `atencion_ciudadana`**.

La etapa con migraciones reales utilizó `config.settings_test_migrations`: `NAME` y `TEST.NAME` fijos a `test_atencion_catalogos_migraciones`, usuario `atencion_test`, las credenciales locales `TEST_POSTGRES_*`, `TEST.MIGRATE=True` y `MIGRATION_MODULES={}`. No requiere cambiar `TEST_POSTGRES_DB`, que sigue reservado a la configuración anterior. Ambas configuraciones conservan las comprobaciones de aislamiento; el auxiliar solo admite los dos nombres exactos de bases de pruebas, sin aceptar cualquier prefijo `test_`.

Antes de ejecutar se confirmó por conexión real que la nueva base estaba vacía, sin tablas de aplicación ni historial de migraciones, y que su usuario y propietario eran `atencion_test`. El comando ejecutado fue:

```bash
.venv/bin/python -B manage.py test usuarios config.tests oficinas tramites --settings=config.settings_test_migrations --keepdb --parallel 1 --noinput --verbosity 2
```

Terminó con **42 pruebas satisfactorias y 18 migraciones reales aplicadas**, sin `--fake`, `--fake-initial` ni desactivar migraciones. Con la misma configuración, `showmigrations` mostró todas aplicadas y `migrate --plan` no mostró operaciones pendientes. Se verificaron 11 tablas, 29 restricciones y 32 índices, y cero filas residuales en usuarios, oficinas y trámites. No se modificaron la base del proyecto, la primera base de pruebas ni permisos de usuarios. El [registro de migraciones reales](docs/pruebas/003-migraciones-postgresql.md) detalla la ejecución y las comprobaciones finales. La base quedó conservada con `--keepdb`; esta documentación no repite la ejecución.

`Oficina` y `Tramite` tienen identificador, nombre obligatorio de hasta 150 caracteres y estado `activo`; el trámite exige una oficina con relación protectora, sin borrado en cascada. Se verificaron la unicidad global de oficinas y la de trámites por oficina, incluyendo inactivos e ignorando mayúsculas y espacios exteriores, y el rechazo de nombres vacíos o sin contenido. La grafía del nombre almacenado se conserva. Desactivar o reactivar conserva el registro y no cambia automáticamente otros registros; no implementa todavía historial de actividad.

La regresión de oficina fija intercaló, mediante dos conexiones reales, la creación de una PK después de que la comprobación de guardado no encontrara la fila. El guardado normal exigió una inserción y fue rechazado por PK duplicada sin sobrescribir la fila de la otra conexión. También pasaron los casos de `force_insert`, `force_update`, `update_fields`, `oficina_id`, instancias reconstruidas o diferidas y cambios de `activo`, comprobando los datos persistidos. Las comprobaciones de Django incluidas en la ejecución no detectaron problemas.

Los bloqueos de borrado y de cambio de oficina cubren las operaciones públicas admitidas del ORM y sus variantes asíncronas; las operaciones masivas de escritura se restringen y `update()` solo admite un booleano literal para `activo`. SQL directo, APIs internas y deserializadores pueden omitir estas protecciones. No hay disparadores SQL aprobados ni protección frente a esas vías; `activo` tampoco sustituye el historial de actividad pendiente.

### Migraciones y validación en PostgreSQL

Se ejecutó `.venv/bin/python manage.py migrate` sobre la base local `atencion_ciudadana`, inicialmente sin tablas ni migraciones aplicadas. Las 16 migraciones terminaron correctamente: dos de `contenttypes`, doce de `auth`, una de `sessions` y una de `usuarios`. No se usó `--fake` ni se borraron tablas o reinició la base.

Después se ejecutaron con el mismo entorno virtual:

```bash
.venv/bin/python manage.py check
.venv/bin/python manage.py showmigrations
.venv/bin/python manage.py migrate --plan
.venv/bin/python manage.py makemigrations --check --dry-run
```

Todas las comprobaciones fueron satisfactorias, sin migraciones ni cambios de modelos pendientes en esa etapa de usuarios. Se confirmó el modelo activo `usuarios.Usuario` y la existencia de `usuarios_usuario`. Las pruebas de lectura, escritura, contraseñas mediante `check_password`, desactivación y restricciones se realizaron dentro de una transacción revertida, con bloques `atomic` internos para los errores de integridad esperados y captura fuera de esos bloques. No quedó ningún usuario ficticio ni se creó una cuenta permanente.

Fueron pruebas puntuales; en esa validación de usuarios no se añadió una suite automática de integración. La comprobación de `check_password` no valida el inicio de sesión ni la fortaleza de contraseñas. Las etapas posteriores de oficinas y trámites incorporan una suite con PostgreSQL y verifican los archivos de migración mediante su aplicación real en la segunda base de pruebas, descrita arriba. La etapa posterior de asignaciones implementa creación/reactivación y sus eventos. El registro inicial de folios ya está implementado y revisado en pruebas; su migración ya está aplicada localmente. La primera entrega de pausas y disponibilidad también está revisada en pruebas, con `folios.0002` aplicada y verificada localmente, según el [registro 010](docs/pruebas/010-migracion-pausas-disponibilidad-local.md). Siguen pendientes las restantes acciones de folios, la auditoría global, las pantallas de trabajo, los demás permisos funcionales y las protecciones definitivas por folios. El acceso mediante pantallas y los destinos mínimos ya están implementados y comprobados en esta etapa, según el [registro 011](docs/pruebas/011-inicio-de-sesion-y-acceso-postgresql.md); no se habilita el panel técnico de Django. Véase el [registro de casos y resultados de usuarios](docs/pruebas/001-usuarios-postgresql.md).

El **10 de octubre de 2026** se aplicaron los catálogos a la base local mediante `config.settings`, después de confirmar por conexión real `atencion_ciudadana` con `atencion_app`, Git limpio, las 16 migraciones anteriores aplicadas y un plan con exactamente `oficinas.0001_initial` y `tramites.0001_initial`. Las comprobaciones previas de Django pasaron y no se detectaron cambios de modelos. Se ejecutó:

```bash
.venv/bin/python -B manage.py migrate --settings=config.settings --noinput
```

Ambas migraciones terminaron con `OK`. Después, `showmigrations` mostró las **18 migraciones aplicadas**, `migrate --plan` no mostró operaciones pendientes y `check` no detectó incidencias. Una inspección de solo lectura verificó las dos tablas de catálogos, sus columnas, cinco restricciones y cinco índices; ambas tablas tenían cero filas. No se usaron migraciones simuladas, no se ejecutaron pruebas sobre esta base ni se crearon usuarios o datos de ejemplo, y no se cambiaron permisos. El [registro de aplicación local de catálogos](docs/pruebas/004-migraciones-catalogos-local.md) documenta los comandos y resultados. Los registros anteriores se conservan intactos como evidencia de etapas distintas.

## Usuarios

| Rol | Responsabilidad principal |
| --- | --- |
| Administrador | Configurar oficinas y trámites, gestionar cuentas y contraseñas, asignar oficinas y realizar las correcciones administrativas acordadas. |
| Recepción | Registrar y corregir datos del ciudadano, elegir oficina y trámite, consultar disponibilidad, trasladar folios En espera y cerrar por ausencia. |
| Operador | Consultar la cola y el historial, llamar al siguiente ciudadano, iniciar la atención, registrar notas, finalizar, denegar y pausar o reanudar. |

Todos los usuarios acceden mediante el mismo inicio de sesión con usuario y contraseña. Cada cuenta tiene un único rol y el administrador establece o cambia sus contraseñas. Después de autenticarse, el sistema los dirige al espacio correspondiente a su rol y permisos. Un operador puede tener una o varias oficinas asignadas por el administrador; no las selecciona desde su panel. Para el lanzamiento se contempla un operador por oficina como organización inicial; una oficina puede tener varios operadores.

## Alcance de la versión 1

- Registro de nombre completo obligatorio, correo electrónico opcional y teléfono opcional.
- Selección manual en recepción de la oficina y después de un trámite de esa oficina; cada trámite pertenece a una sola oficina.
- Seguimiento del folio mediante En espera → Llamado → En atención → Finalizado.
- Nota de texto libre obligatoria para finalizar, editable mientras la atención está abierta y disponible para consulta tras el cierre, con autor, fecha y oficina.
- Consulta de incidencias y traslados, cierres por denegación o ausencia con motivo y confirmación, y pausas con motivo.
- Traslados por Recepción únicamente de folios En espera, conservando el folio, el historial y la llegada original.
- Trazabilidad automática de usuarios, oficinas, trámites y tiempos de atención.

Las oficinas de **Registro de Marca** y **Buró de Crédito** son ejemplos del contexto inicial. No constituyen un catálogo cerrado ni deben quedar escritas de forma fija en el código.

## Flujo principal

Recepción → registro del ciudadano → selección manual de oficina y trámite → En espera → llamada al ciudadano con la llegada más antigua → Llamado → inicio de atención → En atención → nota con contenido y confirmación → Finalizado.

Las denegaciones, los cierres por ausencia, las pausas y los traslados se documentan como variantes de este flujo. Lo ocurrido se describe en la nota, sin clasificación Concretado / No concretado. Cada operador puede tener como máximo un folio en Llamado o En atención entre todas sus oficinas y debe finalizarlo antes de llamar otro; se conservan los cierres por ausencia o denegación y las excepciones administrativas aprobadas. **Libre**: sin folio actual y sin pausa, puede llamar sujeto a permisos y asignaciones. **Ocupado**: con folio actual y sin pausa, no puede llamar otro. **En pausa**: no puede llamar, incluso sin folio actual; conserva folio, responsabilidad, estado y notas. Al reanudar queda Libre u Ocupado según tenga un folio actual. La desactivación de la cuenta bloquea el acceso por separado y no equivale a disponibilidad.

El operador decide cuándo llamar al siguiente; no hay llamada automática ni cierre por el mero transcurso del tiempo. El significado funcional de Inactivo y el tratamiento de correcciones administrativas que pudieran producir un segundo folio actual siguen pendientes en la decisión 006.

## Documentación

- [Acuerdos vigentes](docs/acuerdos-vigentes.md): fuente principal de las reglas aprobadas; prevalece sobre las propuestas anteriores.
- [Visión del producto](docs/vision.md): problema, objetivos, usuarios y alcance.
- [Requisitos](docs/requirements.md): requisitos funcionales y no funcionales de la versión 1.
- [Flujos de usuario](docs/user-flow.md): recorridos de administrador, recepcionista y operador, incluidas las excepciones.
- [Validación de usuarios en PostgreSQL](docs/pruebas/001-usuarios-postgresql.md): migraciones aplicadas, pruebas puntuales, restricciones y alcance de la comprobación.
- [Diseño de oficinas, trámites y asignaciones](docs/decisiones/002-oficinas-tramites-y-asignaciones.md): estado de catálogos y asignaciones implementados, con protecciones definitivas por folios pendientes.
- [Servicios de asignación y registro de actividad](docs/decisiones/003-servicios-de-asignacion-y-actividad.md): creación/reactivación, autorización, eventos y bloqueos implementados y revisados; alcance y pendientes.
- [Cola conjunta y responsabilidad desde Llamado](docs/decisiones/004-cola-y-responsabilidad-de-folios.md): acuerdos funcionales aprobados; servicio de llamado y lecturas mínimas implementados y verificados, con pantallas y flujo posterior pendientes.
- [Disponibilidad y folio actual del operador](docs/decisiones/006-disponibilidad-y-folio-actual-del-operador.md): acuerdos aprobados el 11 de octubre de 2026 y ambigüedades restantes; pausas, consultas y servicio de llamado/reserva implementados y verificados en pruebas aisladas.
- [Diseño de pausas y disponibilidad](docs/decisiones/007-diseno-pausas-y-disponibilidad.md): primera entrega implementada y revisada en pruebas, con modelos, contratos, permisos, solicitudes repetidas y bloqueos; migración aplicada y verificada localmente.
- [Diseño de llamado y reserva](docs/decisiones/008-diseno-llamado-y-reserva.md): servicio y modelos verificados en la base aislada; migración aplicada y comprobada en la base normal conforme al registro 015. Conserva comprobantes, eventos CREACION, cola combinada, pausa y máximo global; solo LLAMADO devuelve folio y evento.
- [Lecturas autorizadas de Operador](docs/decisiones/011-lecturas-autorizadas-de-operador.md): lectores implementados y verificados. Cola conjunta con cursor de 50 elementos, folio propio global y disponibilidad existente, con autorización vigente y resultados materializados sin escrituras.
- [Validación de lecturas de Operador](docs/pruebas/016-lecturas-operador-postgresql.md): 31 pruebas nuevas incluidas en la regresión de 273, 4 JavaScript y recuperación DEMO verificada desde un respaldo nuevo; sin conexión a la base normal.
- [Validación aislada de llamado y reserva](docs/pruebas/014-validacion-llamado-y-reserva-postgresql.md): 51 pruebas nuevas incluidas en la regresión completa de 242, 4 pruebas JavaScript y recuperación DEMO sobre el esquema nuevo; evidencia anterior que no se repite en la base normal.
- [Aplicación local de llamado y reserva](docs/pruebas/015-migracion-llamado-y-reserva-local.md): respaldo completo privado, 0003 aplicada exclusivamente en la base normal, 23 migraciones sin pendientes y conservación de datos y secuencias; sin runner ni datos de prueba.
- [Inicio de sesión y acceso por rol](docs/decisiones/009-inicio-de-sesion-y-acceso-por-rol.md): implementación, rutas, autorización y referencia SVG; ingreso, protección de sesión y salida comprobados manualmente con ADMINISTRADOR. Las demás revisiones conservan los límites de los registros 011 y 012.
- [Comprobaciones de inicio de sesión y acceso](docs/pruebas/011-inicio-de-sesion-y-acceso-postgresql.md): 25 pruebas nuevas incluidas en la suite de 165; aislamiento, CSRF, sesiones, capturas previas en Firefox y revisión manual del usuario en Linux Mint con Brave.
- [Registro inicial de folios](docs/decisiones/005-registro-inicial-de-folios.md): registro por Recepción, estado En espera y evento de creación implementados y revisados en pruebas; migración aplicada localmente.
- [Registro inicial de folios en PostgreSQL](docs/pruebas/007-registro-inicial-folios-postgresql.md): suite anterior de 102 pruebas, corrección del descriptor inverso y 3 pruebas afectadas posteriores; 21 migraciones en pruebas y límites pendientes.
- [Aplicación local de la migración de folios](docs/pruebas/008-migracion-folios-local.md): 21 migraciones aplicadas, plan vacío, esquema contrastado y dos tablas nuevas sin registros; sin pruebas sobre la base normal.
- [Pausas y disponibilidad en PostgreSQL de pruebas](docs/pruebas/009-pausas-disponibilidad-postgresql.md): 37 pruebas nuevas incluidas en la suite de 140, 12 de concurrencia, 22 migraciones en pruebas, esquema inspeccionado y revisión crítica posterior; conserva el estado histórico previo a la aplicación local.
- [Aplicación local de pausas y disponibilidad](docs/pruebas/010-migracion-pausas-disponibilidad-local.md): `folios.0002` aplicada, 22 migraciones sin pendientes, esquema contrastado y tres tablas nuevas sin registros; sin pruebas sobre la base normal.
- [Validación de oficinas y trámites en PostgreSQL](docs/pruebas/002-oficinas-tramites-postgresql.md): 37 pruebas satisfactorias en esta etapa y límites de las protecciones implementadas.
- [Verificación de migraciones reales en PostgreSQL](docs/pruebas/003-migraciones-postgresql.md): 42 pruebas satisfactorias, 18 migraciones aplicadas y comprobaciones finales en la segunda base exclusiva de pruebas.
- [Asignaciones en PostgreSQL](docs/pruebas/005-asignaciones-postgresql.md): 74 pruebas antes del ajuste final, 3 pruebas de concurrencia posteriores y 20 migraciones en pruebas; evidencia de la etapa anterior a su aplicación local.
- [Aplicación de migraciones de catálogos en PostgreSQL local](docs/pruebas/004-migraciones-catalogos-local.md): oficinas y trámites aplicados en `atencion_ciudadana`, 18 migraciones registradas e inspección de lectura satisfactoria.
- [Aplicación de migraciones de asignaciones en PostgreSQL local](docs/pruebas/006-migraciones-asignaciones-local.md): 20 migraciones aplicadas, plan vacío y esquema nuevo inspeccionado sin datos de ejemplo.

## Evolución prevista

Las citas programadas y la inteligencia artificial quedan fuera de la versión 1. La información de notas e incidencias deberá conservar su contexto y trazabilidad para permitir, como posible extensión, su análisis futuro mediante IA. Esta preparación no implica implementar modelos, integraciones ni análisis automáticos en la primera versión.
