# Sistema de Flujo de Atención Ciudadana

Proyecto profesional de portafolio para diseñar un sistema interno que permita administrar y dar seguimiento a la atención de ciudadanos en una red de oficinas de una dependencia.

El sistema busca mantener un registro trazable desde la recepción hasta el resultado de la atención, con acceso según el rol y los permisos de cada usuario.

## Estado del proyecto

**Etapa actual: definición y documentación.** Este repositorio documenta la visión, los requisitos y los flujos de la versión 1. La aplicación todavía no está implementada y no se ha definido una tecnología de desarrollo.

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
