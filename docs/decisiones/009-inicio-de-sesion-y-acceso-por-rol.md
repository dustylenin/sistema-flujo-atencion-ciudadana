# 009 — Inicio de sesión y acceso por rol

- Fecha: 11 de octubre de 2026.
- Estado: implementado y comprobado en PostgreSQL de pruebas; revisión manual parcial realizada por el usuario en Linux Mint con Brave. Ingreso con cuenta válida, destinos por rol y logout manual pendientes.
- Evidencia: [comprobaciones de acceso](../pruebas/011-inicio-de-sesion-y-acceso-postgresql.md).

## Respaldo funcional y alcance

Los [acuerdos vigentes, «Roles y acceso»](../acuerdos-vigentes.md#roles-y-acceso) establecen un único rol por cuenta y acceso con usuario y contraseña. Solo el administrador crea cuentas y establece o cambia contraseñas; se descartó el cambio obligatorio al ingresar. El apartado [«Oficinas, trámites y asignaciones»](../acuerdos-vigentes.md#oficinas-trámites-y-asignaciones) conserva el historial al desactivar una cuenta y bloquea su acceso. Los [requisitos RF-01 a RF-04, «Autenticación y permisos»](../requirements.md#autenticación-y-permisos) y el [flujo, «Acceso común»](../user-flow.md#acceso-común) respaldan autenticación, destino por rol y validación de permisos en el servidor.

Esta entrega implementa exclusivamente inicio de sesión, cierre de sesión y tres destinos mínimos. No incorpora registro público, recuperación ni cambio de contraseña, gestión de cuentas, panel técnico de Django, menús, métricas ni funciones pendientes. No cambia modelos, servicios de negocio, barreras existentes ni migraciones. La pantalla de recepción conectada al registro de folios es el siguiente objetivo; el llamado sigue pendiente conforme a la decisión 008.

Las rutas, el error genérico, ignorar `next`, la mejora opcional mediante JavaScript y el uso de las vistas estándar de Django son decisiones técnicas de esta entrega, solicitadas en la revisión; no amplían los permisos funcionales.

## Autenticación y rutas

Se utiliza `AccesoView`, derivada de `LoginView`, y `FormularioAcceso`, derivado de `AuthenticationForm`. Se conserva `django.contrib.auth.backends.ModelBackend`, backend estándar vigente, sin autenticación alternativa. El formulario mantiene `username`, verificación de contraseña de Django y `PasswordInput` sin `render_value`; nunca devuelve la contraseña en el HTML.

| Ruta | Acceso y resultado |
| --- | --- |
| `/acceso/` | GET muestra el formulario; POST válido autentica y redirige al destino fijo del rol. Una sesión autenticada también redirige a su destino. |
| `/` | Cuenta autenticada y activa de uno de los tres roles: redirección a su destino. Anónimo: `/acceso/`. |
| `/recepcion/` | Solo cuenta activa con rol `RECEPCION`. |
| `/operacion/` | Solo cuenta activa con rol `OPERADOR`. No exige asignaciones para acceder a este destino mínimo ni autoriza atención. |
| `/administracion/` | Solo cuenta activa con rol `ADMINISTRADOR`. No concede gestión funcional todavía. |
| `/salir/` | Exclusivamente POST con CSRF; elimina la sesión y redirige a `/acceso/`. Otros métodos: 405. |

Los destinos muestran únicamente nombre del espacio, identificador de la cuenta conectada y un formulario para cerrar sesión. No consultan ciudadanos, folios, oficinas, pausas ni datos de otras cuentas.

`get_success_url()` fija las redirecciones según el rol; tanto login como logout ignoran `next` de GET y POST, incluso si apunta al mismo sitio. Las rutas privadas redirigen a los anónimos sin conservar `next`; un usuario de otro rol recibe 403. Un rol ajeno a los tres admitidos no obtiene destino ni permisos.

## Autorización y seguridad

`requiere_rol` comprueba autenticación, cuenta activa y rol funcional. No consulta `is_staff`, `is_superuser`, permisos técnicos ni un rol almacenado en la sesión. El middleware y el backend estándar recuperan la cuenta vigente en cada petición: cambiar de rol modifica el acceso con una sesión existente y desactivar la cuenta convierte su autenticación efectiva en anónima. Los identificadores internos pueden permanecer en la sesión desactivada, conforme a Django; no otorgan acceso mientras la cuenta esté desactivada.

La autorización no reemplaza los permisos de servicios ni modifica los bloqueos provisionales para retirar asignaciones o salir del rol OPERADOR. Cada pantalla futura deberá aplicar su autorización y utilizar los servicios correspondientes.

Se mantienen el middleware CSRF y las protecciones heredadas de `LoginView` y `LogoutView`: parámetros sensibles, renovación de sesión al autenticar, rotación de CSRF y respuestas que no deben almacenarse en caché. Ambos formularios usan POST y `{% csrf_token %}`. Usuario inexistente, contraseña incorrecta y cuenta desactivada reciben el mismo mensaje: «No fue posible iniciar sesión. Verifica tu usuario y contraseña». Los campos vacíos conservan sus errores de obligatoriedad. Django escapa la entrada y el identificador mostrado.

## Referencia visual y adaptación

La paleta procede de [«Diseño visual aprobado» de los acuerdos](../acuerdos-vigentes.md#diseño-visual-aprobado): `#521F30`, `#70283E`, fondo `#F5F4F2`, tarjetas blancas y tipografía legible.

Se inspeccionó el código del SVG local `/home/lenin/Descargas/FigmaW/Login_Acceso_al_sistema (2).svg`, de 1440 × 1024, titulado «Inicio de sesión — propuesta visual institucional». Su SHA-256 es `e7ef79984f7cf00a376a8fbb629a00704378eda9faeb9a90153eaabd3e1095bf`. Es la referencia utilizada para adaptar los dos paneles, las iniciales SF, el formulario y la orientación para contactar al administrador. **No se afirma que esa versión concreta esté confirmada como aprobada**; se distingue de la paleta respaldada en los acuerdos. No se copia el archivo externo al repositorio ni se incorporan SVG de otras pantallas.

La interfaz usa plantillas Django y CSS local, sin dependencias visuales externas. En escritorio dispone dos paneles y en pantallas pequeñas apila identidad y formulario. Hay etiquetas visibles asociadas a los campos, contraste con la paleta institucional, controles HTML nativos, foco visible, texto de error y atributos para lectores de pantalla. No se impone un orden de tabulación personalizado.

El formulario y logout funcionan sin JavaScript. El único script habilita la casilla «Mostrar contraseña» y alterna el tipo del campo; la casilla permanece oculta cuando no hay JavaScript. No intercepta el envío ni valida credenciales en el navegador. La autenticación sigue siendo del servidor.

## Archivos y verificación

- `usuarios/acceso.py`, `forms.py`, `views.py` y `urls.py`: autorización, formulario y rutas explícitas; no se incluye el conjunto de rutas de contraseñas de Django.
- `config/urls.py` y `config/settings.py`: rutas y `LOGIN_URL`.
- `templates/base.html`, `templates/usuarios/login.html` y `destino.html`: estructura y formularios.
- `static/css/acceso.css` y `static/js/acceso.js`: adaptación responsiva y mostrar/ocultar contraseña.
- `usuarios/test_acceso.py`: 25 pruebas nuevas con sesiones, autorización y CSRF, exclusivamente en `config.settings_test_migrations` y con las barreras de identidad real existentes.
- README y registro 011: preparación local y resultados de la etapa.

La evidencia diferencia las 25 pruebas nuevas y las 165 de la suite completa, que ya las incluyen, de la revisión de dos capturas de Firefox. Durante la implementación no se verificaron interacciones manuales con teclado, lector de pantalla ni autenticación desde un navegador con una cuenta normal. No se crearon cuentas en la base normal ni se conectó a ella durante esa etapa.

El **11 de octubre de 2026**, el usuario confirmó manualmente en **Linux Mint con Brave** mostrar/ocultar contraseña, navegación con Tab y foco visible, adaptación al reducir la ventana y el error genérico para credenciales inválidas, conservando el usuario y vaciando la contraseña. El [registro 011](../pruebas/011-inicio-de-sesion-y-acceso-postgresql.md#revisión-manual-realizada-por-el-usuario) conserva esta revisión separada de las pruebas automatizadas existentes, que no se repitieron. Siguen pendientes el ingreso con una cuenta válida, los destinos por rol y el logout manual. No se declaran comprobados el lector de pantalla ni el funcionamiento manual sin JavaScript.

## Preparación local pendiente

El README indica cómo servir `/acceso/` en Linux Mint con el entorno y la configuración local existentes. La pantalla puede abrirse sin cuenta; iniciar sesión requiere una cuenta activa con rol y contraseña asignada por el administrador. No se creó ninguna cuenta ni se implementó su administración en esta etapa. No se requiere superusuario técnico para el acceso funcional.
