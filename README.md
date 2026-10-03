# Sistema de Flujo de Atención Ciudadana

Proyecto profesional de portafolio para diseñar un sistema interno que permita administrar y dar seguimiento a la atención de ciudadanos en una red de oficinas de una dependencia.

El sistema busca mantener un registro trazable desde la recepción hasta el resultado de la atención, con acceso según el rol y los permisos de cada usuario.

## Estado del proyecto

**Etapa actual: definición y documentación.** Este repositorio documenta la visión, los requisitos y los flujos de la versión 1. La aplicación todavía no está implementada y no se ha definido una tecnología de desarrollo.

## Usuarios

| Rol | Responsabilidad principal |
| --- | --- |
| Administrador | Configurar oficinas y trámites, y administrar los roles y permisos de los usuarios. |
| Recepcionista | Registrar al ciudadano, seleccionar el trámite y la oficina, y incorporarlo a la espera de atención. |
| Operador de oficina | Atender registros de las oficinas autorizadas, agregar notas y registrar el resultado de la atención. |

Todos los usuarios acceden mediante el mismo inicio de sesión. Después de autenticarse, el sistema los dirige al espacio correspondiente a su rol y permisos. Un operador puede tener autorización para una o varias oficinas.

## Alcance de la versión 1

- Registro de nombre completo obligatorio, correo electrónico opcional y teléfono opcional.
- Selección de oficinas y trámites configurables desde administración.
- Seguimiento de la espera, el inicio de atención y su finalización.
- Notas de texto libre conservadas como historial, con autor, fecha y hora.
- Registro de incidencias, trámites no concretados y transferencias excepcionales.
- Trazabilidad automática de usuarios, oficinas, trámites y tiempos de atención.

Las oficinas de **Registro de Marca** y **Buró de Crédito** son ejemplos del contexto inicial. No constituyen un catálogo cerrado ni deben quedar escritas de forma fija en el código.

## Flujo principal

Recepción → registro del ciudadano → selección de trámite y oficina → espera → inicio de atención por un operador autorizado → registro de información → trámite finalizado.

Las incidencias, los resultados no concretados y las transferencias excepcionales se documentan como variantes de este flujo.

## Documentación

- [Visión del producto](docs/vision.md): problema, objetivos, usuarios y alcance.
- [Requisitos](docs/requirements.md): requisitos funcionales y no funcionales de la versión 1.
- [Flujos de usuario](docs/user-flow.md): recorridos de administrador, recepcionista y operador, incluidas las excepciones.

## Evolución prevista

Las citas programadas y la inteligencia artificial quedan fuera de la versión 1. La información de notas e incidencias deberá conservar su contexto y trazabilidad para permitir, como posible extensión, su análisis futuro mediante IA. Esta preparación no implica implementar modelos, integraciones ni análisis automáticos en la primera versión.
