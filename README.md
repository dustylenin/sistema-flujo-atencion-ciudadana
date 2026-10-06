# Sistema de Flujo de Atención Ciudadana

Proyecto profesional de portafolio para diseñar un sistema interno que permita administrar y dar seguimiento a la atención de ciudadanos en una red de oficinas de una dependencia.

El sistema busca mantener un registro trazable desde la recepción hasta el resultado de la atención, con acceso según el rol y los permisos de cada usuario.

## Estado del proyecto

**Etapa actual: estructura inicial, base del usuario personalizado y conexión local a PostgreSQL verificada.** Este repositorio conserva la visión, los requisitos y los flujos de la versión 1 e incorpora la configuración base de Django y `Usuario(AbstractUser)`. La aplicación funcional todavía no está implementada: no hay oficinas, asignaciones, pantallas ni reglas de atención. La migración inicial `usuarios/migrations/0001_initial.py` está generada y revisada; todavía no se han aplicado migraciones.

Las comprobaciones de Django fueron satisfactorias y `makemigrations --check --dry-run` no detectó cambios de modelos pendientes. Se revisaron el SQL de `sqlmigrate usuarios 0001_initial` y el plan de `migrate --plan`, sin aplicar el SQL ni las operaciones del plan. La persistencia y las restricciones reales en PostgreSQL siguen pendientes de validar después de aplicar las migraciones.

## Tecnologías elegidas

- Interfaz: HTML, CSS y JavaScript con plantillas de Django.
- Servidor: Python con Django **5.2.17 LTS**, con soporte extendido hasta abril de 2028 según la [política oficial](https://www.djangoproject.com/download/).
- Base de datos: PostgreSQL **16.15** funcionando en el entorno local verificado. La recomendación inicial de PostgreSQL **18.6** no describe la instalación actual; ambas ramas figuran en la [política oficial de versiones](https://www.postgresql.org/support/versioning/).
- Python recomendado: **3.14.8**. El entorno virtual local se creó con **3.12.3**, disponible en Linux Mint 22.3. Django 5.2 admite ambas ramas según su [documentación de compatibilidad](https://docs.djangoproject.com/en/5.2/releases/5.2/#python-compatibility). La comprobación local no valida todavía Python 3.14.
- Conexión PostgreSQL: Psycopg **3.3.6**, con paquete binario para desarrollo local; carga de `.env`: python-dotenv **1.2.4**. Las dependencias están fijadas en `requirements.txt`.

## Estructura inicial

```text
config/          Configuración, rutas vacías y entradas ASGI/WSGI
usuarios/        Usuario personalizado, manager y pruebas sin base de datos
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

`AUTH_USER_MODEL` apunta a `usuarios.Usuario`, basado en `AbstractUser`, conforme a la [decisión aprobada de usuarios y asignaciones](docs/decisiones/001-usuarios-y-asignaciones.md). Conserva `username` como identificador de acceso y los campos heredados. Solo se ha implementado la base del usuario; las asignaciones y la autorización funcional siguen pendientes.

El campo `rol` es obligatorio, sin valor predeterminado, y admite `ADMINISTRADOR`, `RECEPCION` u `OPERADOR`. `create_user()` y `create_superuser()` exigen el argumento explícito `rol`; los valores vacíos o inválidos se rechazan antes de guardar. El guardado directo también valida el rol. La restricción del modelo para la base de datos se aplicará cuando se aprueben y ejecuten las migraciones; todavía no existe en PostgreSQL.

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

### Comprobaciones sin base de datos y validaciones pendientes

Con las variables completas, las comprobaciones sin acceso a la base son:

```bash
python -m pip check
python -m compileall -q manage.py config usuarios
python manage.py check
python manage.py test usuarios --verbosity 2
git diff --check
```

`manage.py check` por sí solo no demuestra que exista conexión a PostgreSQL; esa conexión se comprobó separadamente con `SELECT 1`. Las pruebas de usuarios usan `SimpleTestCase`, prohíben consultas a la base e interceptan los guardados válidos: no crean cuentas ni una base de pruebas. La migración inicial ya está generada; todavía no aplicar migraciones con `migrate` ni crear cuentas con `createsuperuser`. El arranque funcional sigue pendiente; no hay rutas de aplicación ni panel administrativo habilitado.

Quedan pendientes de validar en PostgreSQL la persistencia real, la unicidad de `username` y la restricción de roles, una vez que se autoricen y apliquen las migraciones. Las ocho pruebas sin base de datos no comprueban esos comportamientos en el servidor PostgreSQL.

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

## Evolución prevista

Las citas programadas y la inteligencia artificial quedan fuera de la versión 1. La información de notas e incidencias deberá conservar su contexto y trazabilidad para permitir, como posible extensión, su análisis futuro mediante IA. Esta preparación no implica implementar modelos, integraciones ni análisis automáticos en la primera versión.
