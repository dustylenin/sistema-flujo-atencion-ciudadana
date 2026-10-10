# Sistema de Flujo de Atención Ciudadana

Proyecto profesional de portafolio para diseñar un sistema interno que permita administrar y dar seguimiento a la atención de ciudadanos en una red de oficinas de una dependencia.

El sistema busca mantener un registro trazable desde la recepción hasta el resultado de la atención, con acceso según el rol y los permisos de cada usuario.

## Estado del proyecto

**Etapa actual: creación y reactivación de asignaciones implementadas y revisadas en pruebas, con sus migraciones aplicadas y verificadas en PostgreSQL local.** Se incorporaron `AsignacionOperadorOficina`, `EventoAsignacion` y servicios autorizados por administrador funcional, con eventos durables y transacción conjunta. En `test_atencion_catalogos_migraciones`, con `config.settings_test_migrations` y `atencion_test`, quedaron 20 migraciones reales aplicadas y sin operaciones pendientes. La suite completa pasó con **74 pruebas antes del ajuste final de concurrencia**; después se reforzó la sincronización y pasaron las **3 pruebas afectadas**, sin repetir la suite completa. El [registro de asignaciones](docs/pruebas/005-asignaciones-postgresql.md) distingue ambas verificaciones.

Las migraciones de catálogos y asignaciones ya están aplicadas y verificadas en `atencion_ciudadana`, con `config.settings` y `atencion_app`: **20 migraciones aplicadas y plan sin pendientes**. Las dos migraciones de asignaciones terminaron correctamente; la de Usuario cambia opciones de managers sin cambios físicos de esquema. La inspección de lectura verificó 2 tablas nuevas, 11 columnas, 8 restricciones y 7 índices, con cero filas en asignaciones y eventos y `check` sin incidencias. El [registro de aplicación local de asignaciones](docs/pruebas/006-migraciones-asignaciones-local.md) conserva la ejecución. Folios, pantallas, gestión funcional de cuentas y auditoría global siguen pendientes.

Tras aplicar las migraciones de usuarios, las comprobaciones de Django fueron satisfactorias: `check` no detectó problemas, `showmigrations` mostró todas las migraciones aplicadas, `migrate --plan` no mostró operaciones pendientes y `makemigrations --check --dry-run` no detectó cambios de modelos en esa etapa. Las pruebas puntuales comprobaron la creación y recuperación de usuarios de los tres roles, la unicidad de `username`, las restricciones del rol y la conservación del registro al desactivar una cuenta. Todas las operaciones con usuarios ficticios se revirtieron: quedaron cero usuarios y no se creó ninguna cuenta permanente. Los resultados y el alcance están en el [registro de validación en PostgreSQL](docs/pruebas/001-usuarios-postgresql.md).

La [decisión de servicios de asignación y actividad](docs/decisiones/003-servicios-de-asignacion-y-actividad.md) describe el alcance implementado: creación y reactivación por administrador funcional autenticado y activo, relectura de su estado en la base, resultados explícitos, bloqueos y protecciones del ORM. Retirada y cambio efectivo desde `OPERADOR` están bloqueados provisionalmente hasta verificar sus reglas completas con folios reales. Los eventos cubren únicamente creación y reactivación; no constituyen la auditoría completa del sistema. Las 42 pruebas de la etapa anterior se conservan como evidencia de usuarios, catálogos y configuración de migraciones.

## Tecnologías elegidas

- Interfaz: HTML, CSS y JavaScript con plantillas de Django.
- Servidor: Python con Django **5.2.17 LTS**, con soporte extendido hasta abril de 2028 según la [política oficial](https://www.djangoproject.com/download/).
- Base de datos: PostgreSQL **16.15** funcionando en el entorno local verificado. La recomendación inicial de PostgreSQL **18.6** no describe la instalación actual; ambas ramas figuran en la [política oficial de versiones](https://www.postgresql.org/support/versioning/).
- Python recomendado: **3.14.8**. El entorno virtual local se creó con **3.12.3**, disponible en Linux Mint 22.3. Django 5.2 admite ambas ramas según su [documentación de compatibilidad](https://docs.djangoproject.com/en/5.2/releases/5.2/#python-compatibility). La comprobación local no valida todavía Python 3.14.
- Conexión PostgreSQL: Psycopg **3.3.6**, con paquete binario para desarrollo local; carga de `.env`: python-dotenv **1.2.4**. Las dependencias están fijadas en `requirements.txt`.

## Estructura inicial

```text
config/          Configuración, rutas vacías y entradas ASGI/WSGI
usuarios/        Usuario personalizado, protecciones de rol y pruebas
oficinas/        Catálogo, asignaciones, eventos, servicios y pruebas
tramites/        Catálogo de trámites con oficina fija y pruebas
docs/            Documentación del producto conservada
templates/       Carpeta reservada para plantillas; sin pantallas
static/css/      Carpeta reservada para estilos
static/js/       Carpeta reservada para JavaScript
static/img/      Carpeta reservada para imágenes
manage.py        Comandos de Django
requirements.txt Dependencias del entorno
.env.example     Variables de ejemplo sin credenciales reales
.gitignore       Excluye entorno virtual, secretos y archivos generados
```

`AUTH_USER_MODEL` apunta a `usuarios.Usuario`, basado en `AbstractUser`, conforme a la [decisión aprobada de usuarios y asignaciones](docs/decisiones/001-usuarios-y-asignaciones.md). Conserva `username` como identificador de acceso y los campos heredados. La autorización funcional de creación/reactivación de asignaciones está implementada en servicios; las pantallas y los demás permisos funcionales siguen pendientes.

El campo `rol` es obligatorio, sin valor predeterminado, y admite `ADMINISTRADOR`, `RECEPCION` u `OPERADOR`. `create_user()` y `create_superuser()` exigen el argumento explícito `rol`; los valores vacíos o inválidos se rechazan antes de guardar. El guardado directo también valida el rol. En PostgreSQL ya se comprobaron `UNIQUE (username)`, `NOT NULL` de `rol` y la restricción `usuarios_usuario_rol_valido` para los tres roles, incluidos intentos mediante `update()` que omiten la validación de `save()`.

`rol`, `is_active`, `is_staff` e `is_superuser` son independientes. El manager conserva el comportamiento técnico de Django al crear superusuarios, sin asignarles automáticamente el rol `ADMINISTRADOR`. Esos indicadores no implementan los permisos de las pantallas propias.

`REQUIRED_FIELDS` conserva los campos de `AbstractUser` y añade `rol`: cuando se autorice usar `createsuperuser`, el modo interactivo solicitará el rol y el modo no interactivo requerirá `--rol` o `DJANGO_SUPERUSER_ROL`. Esto no crea una cuenta ahora ni habilita gestión de contraseñas o pantallas. La creación de cuentas desde Usuarios y la gestión exclusiva de contraseñas por el administrador siguen pendientes de implementación.

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

Fueron pruebas puntuales; en esa validación de usuarios no se añadió una suite automática de integración. La comprobación de `check_password` no valida el inicio de sesión ni la fortaleza de contraseñas. Las etapas posteriores de oficinas y trámites incorporan una suite con PostgreSQL y verifican los archivos de migración mediante su aplicación real en la segunda base de pruebas, descrita arriba. La etapa posterior de asignaciones implementa creación/reactivación y sus eventos. Siguen pendientes los folios, la auditoría global, el acceso mediante pantallas, los demás permisos funcionales y las protecciones definitivas por folios. El arranque funcional sigue pendiente; no hay rutas de aplicación ni panel administrativo habilitado. Véase el [registro de casos y resultados de usuarios](docs/pruebas/001-usuarios-postgresql.md).

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

Todos los usuarios acceden mediante el mismo inicio de sesión con usuario y contraseña. Cada cuenta tiene un único rol y el administrador establece o cambia sus contraseñas. Después de autenticarse, el sistema los dirige al espacio correspondiente a su rol y permisos. Un operador puede tener una o varias oficinas asignadas por el administrador; no las selecciona desde su panel. Para el lanzamiento se contempla un operador por oficina, con posibilidad de crecimiento posterior.

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

Las denegaciones, los cierres por ausencia, las pausas y los traslados se documentan como variantes de este flujo. Lo ocurrido se describe en la nota, sin clasificación Concretado / No concretado. El operador decide cuándo llamar al siguiente; no hay llamada automática ni cierre por el mero transcurso del tiempo.

## Documentación

- [Acuerdos vigentes](docs/acuerdos-vigentes.md): fuente principal de las reglas aprobadas; prevalece sobre las propuestas anteriores.
- [Visión del producto](docs/vision.md): problema, objetivos, usuarios y alcance.
- [Requisitos](docs/requirements.md): requisitos funcionales y no funcionales de la versión 1.
- [Flujos de usuario](docs/user-flow.md): recorridos de administrador, recepcionista y operador, incluidas las excepciones.
- [Validación de usuarios en PostgreSQL](docs/pruebas/001-usuarios-postgresql.md): migraciones aplicadas, pruebas puntuales, restricciones y alcance de la comprobación.
- [Diseño de oficinas, trámites y asignaciones](docs/decisiones/002-oficinas-tramites-y-asignaciones.md): estado de catálogos y asignaciones implementados, con protecciones definitivas por folios pendientes.
- [Servicios de asignación y registro de actividad](docs/decisiones/003-servicios-de-asignacion-y-actividad.md): creación/reactivación, autorización, eventos y bloqueos implementados y revisados; alcance y pendientes.
- [Validación de oficinas y trámites en PostgreSQL](docs/pruebas/002-oficinas-tramites-postgresql.md): 37 pruebas satisfactorias en esta etapa y límites de las protecciones implementadas.
- [Verificación de migraciones reales en PostgreSQL](docs/pruebas/003-migraciones-postgresql.md): 42 pruebas satisfactorias, 18 migraciones aplicadas y comprobaciones finales en la segunda base exclusiva de pruebas.
- [Asignaciones en PostgreSQL](docs/pruebas/005-asignaciones-postgresql.md): 74 pruebas antes del ajuste final, 3 pruebas de concurrencia posteriores y 20 migraciones en pruebas; evidencia de la etapa anterior a su aplicación local.
- [Aplicación de migraciones de catálogos en PostgreSQL local](docs/pruebas/004-migraciones-catalogos-local.md): oficinas y trámites aplicados en `atencion_ciudadana`, 18 migraciones registradas e inspección de lectura satisfactoria.
- [Aplicación de migraciones de asignaciones en PostgreSQL local](docs/pruebas/006-migraciones-asignaciones-local.md): 20 migraciones aplicadas, plan vacío y esquema nuevo inspeccionado sin datos de ejemplo.

## Evolución prevista

Las citas programadas y la inteligencia artificial quedan fuera de la versión 1. La información de notas e incidencias deberá conservar su contexto y trazabilidad para permitir, como posible extensión, su análisis futuro mediante IA. Esta preparación no implica implementar modelos, integraciones ni análisis automáticos en la primera versión.
