# Sistema de Flujo de Atención Ciudadana

Reglas vigentes tras la revisión de los prototipos. Actualización: 4 de octubre de 2026.

Este documento reúne las decisiones aprobadas para orientar la programación. Las revisiones realizadas corresponden a los prototipos visuales; la aplicación aún no está implementada.

## Roles y acceso

Cada cuenta tiene un único rol: Administrador, Recepción u Operador. El acceso utiliza usuario y contraseña.

| Rol | Pantallas | Funciones acordadas |
| --- | --- | --- |
| Recepción | Nueva atención, Atenciones del día, Detalle de atención, Status | Registrar ciudadanos, corregir sus datos, consultar folios y disponibilidad, trasladar folios en espera y cerrar por ausencia. |
| Operador | Cola de atención y Atención actual | Consultar pendientes e historial, llamar al siguiente, iniciar la atención, registrar notas, finalizar, denegar y pausar o reanudar. |
| Administrador | Resumen, Usuarios, Oficinas, Trámites, Asignaciones, Historial e incidencias, Registro de actividad | Configurar el sistema, gestionar cuentas y contraseñas, asignar oficinas, consultar registros, restaurar estados y reasignar folios de operadores desactivados. |

Solo el administrador crea cuentas y establece o cambia contraseñas desde Usuarios. El personal inicia sesión con la clave asignada. Se descartó el cambio obligatorio de contraseña temporal al iniciar sesión.

## Recepción y registro

- Nombre completo obligatorio; correo y teléfono opcionales.
- Recepción elige manualmente la oficina y después un trámite de esa oficina, según su juicio y responsabilidad.
- Cada trámite pertenece a una sola oficina; una oficina puede tener varios trámites.
- Al registrar se genera el folio, se conserva la fecha y hora de llegada y el estado inicial es En espera.
- La confirmación muestra folio, ciudadano, oficina, trámite, llegada y responsable del registro. Permite consultar el detalle o registrar otra atención.
- Recepción puede corregir nombre, correo y teléfono. Se conservan los valores anteriores y nuevos, responsable, fecha y oficina.

Status muestra información en tarjetas por oficina, con orden fijo: operador y disponibilidad, ciudadanos en espera, espera más larga y duración de la atención actual. Distingue Libre, Ocupado, En pausa e Inactivo.

## Oficinas, trámites y asignaciones

El administrador configura oficinas, trámites, cuentas, roles y asignaciones. Los trámites se gestionan desde Trámites y se vinculan a una única oficina.

Para el lanzamiento se contempla un operador por oficina como organización inicial, no como una prohibición técnica de una segunda asignación. La posibilidad de más operadores por oficina se conserva para el crecimiento del sistema. Un operador puede tener varias oficinas asignadas por el administrador; no selecciona oficinas desde su panel.

El sistema no permitirá eliminar físicamente oficinas ni trámites. Se utilizará la desactivación y se conservarán sus registros y referencias históricas. Desactivar una oficina evita nuevos registros en ella y permite terminar los folios pendientes. Puede reactivarse. Desactivar una cuenta bloquea su acceso y conserva su historial; también puede reactivarse. Un trámite desactivado deja de estar disponible para nuevos registros.

## Recorrido de atención

El recorrido normal es: **En espera → Llamado → En atención → Finalizado**.

1. Recepción registra el folio.
2. El operador llama al ciudadano con la llegada más antigua de la cola correspondiente.
3. Cuando el ciudadano se presenta, el operador pulsa Iniciar atención.
4. El operador registra una nota y confirma la finalización.

No se llama automáticamente al siguiente ciudadano. Tras finalizar, el operador decide cuándo continuar, sin una espera fija obligatoria. El tiempo transcurrido por sí solo no cierra ni deniega un folio.

Cola de atención tiene Pendientes e Historial. El historial permite buscar por folio o nombre y filtrar por fecha o rango, trámite y estado.

## Notas y finalización

- Para finalizar una atención, la nota debe tener contenido. Su redacción y extensión dependen del operador.
- Las notas conservan autor, fecha y oficina.
- El operador puede editar la nota mientras la atención está abierta. Tras finalizar, queda disponible para consulta.
- El estado de cierre es Finalizado. Se descartó la clasificación Concretado / No concretado; lo ocurrido se describe en la nota.

## Denegación y ausencia

El operador puede denegar un folio antes o después de llamar al ciudadano. Recepción también puede cerrar por ausencia. Estas decisiones dependen de la confirmación y responsabilidad del personal; la demora por sí sola no las justifica.

Ambas acciones requieren motivo y confirmación. El folio pasa a Finalizado y el motivo se conserva como nota de cierre, con responsable, fecha, hora y oficina. El cierre por ausencia no exige haber llamado previamente al ciudadano.

## Pausas

La pausa está disponible en todo momento, incluso con un ciudadano Llamado o En atención. Requiere motivo y el operador puede reanudar cuando lo decida, sin autorización administrativa.

El estado del operador pasa a En pausa; el folio conserva su estado y sus notas. Recepción consulta la pausa en Status. El administrador consulta operador, motivo, inicio, fin, duración, oficina y folio asociado en Registro de actividad.

Los prototipos muestran por separado el tiempo desde el inicio de la atención y el tiempo de pausa.

## Traslados

Recepción puede trasladar únicamente folios En espera, seleccionando la nueva oficina, un trámite de esa oficina y el motivo.

Se conserva el folio, su historial y la llegada original. El lugar en la nueva cola se determina por esa llegada, sin interrumpir la atención en curso. El movimiento conserva responsable, fecha y oficinas involucradas. El operador no traslada folios desde Atención actual.

## Correcciones administrativas

El administrador puede restaurar el estado anterior de un folio con motivo obligatorio. El registro original y la corrección se conservan con sus responsables. Si vuelve a En espera, conserva la llegada original para su lugar en la cola.

El administrador también puede reasignar un folio abierto de un operador desactivado a un operador activo de la misma oficina, con motivo obligatorio. Se conserva la oficina, el estado, las notas y sus autores; la reasignación queda en el historial.

## Historial y registro de actividad

Historial e incidencias permite consultar atenciones y, en otra pestaña, incidencias y traslados. El detalle conserva datos del folio, motivo, responsable, fecha y oficinas involucradas.

Registro de actividad permite filtrar por fecha, usuario, oficina y acción. Reúne pausas y reanudaciones, cierres, traslados, reasignaciones, correcciones de datos o estados y cambios en cuentas, oficinas, trámites y asignaciones. Las correcciones conservan evidencia de la acción original.

## Diseño visual aprobado

Estilo moderno, formal e institucional, orientado a un producto para gobierno. Se conserva la estructura de las pantallas.

- Barra lateral en rojo tinto oscuro: `#521F30`.
- Acentos y acciones principales: `#70283E`.
- Fondo claro: `#F5F4F2`; tarjetas blancas y bordes discretos.
- Tipografía legible, esquinas moderadamente redondeadas y estados identificados mediante texto y color.
- Prototipos SVG de escritorio de 1440 × 1024, listos para importar a Figma.

## Propuestas sustituidas

Para la implementación prevalecen las reglas de este documento sobre las propuestas iniciales. Se descartaron la asignación automática de oficina, los trámites compatibles con varias oficinas, la selección de oficina y los traslados desde el panel del operador, la clasificación Concretado / No concretado y el cambio obligatorio de contraseña temporal por el usuario.

`cambiar-contrasena-temporal-tinto-v1.svg` quedó descartado. La ventana vigente para contraseñas es `admin-cambiar-contrasena-tinto-v1.svg`, exclusiva del administrador. Los SVG originales anteriores al rediseño son referencias; no deben reintroducir las propuestas sustituidas.

## Revisión realizada

Se revisaron las pantallas principales y ventanas de las acciones acordadas, así como la coherencia visual del recorrido normal, ausencia, pausa, traslado y permisos previstos por rol. Los datos de los ejemplos son ilustrativos.

La siguiente etapa es planear la programación. La implementación deberá verificar estos permisos y transiciones también en el servidor.
