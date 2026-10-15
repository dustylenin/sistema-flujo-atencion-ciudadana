# Sistema de Flujo de Atención Ciudadana

Reglas vigentes tras la revisión de los prototipos. Actualización: 15 de octubre de 2026.

Este documento reúne las decisiones aprobadas para orientar la programación. Las revisiones visuales corresponden a los prototipos. El registro inicial de folios está implementado conforme a la [decisión 005](decisiones/005-registro-inicial-de-folios.md), y Nueva atención de Recepción con confirmación propia conforme a la [decisión 010](decisiones/010-nueva-atencion-recepcion.md). Su revisión manual sigue pendiente. Los recorridos posteriores y las restantes pantallas siguen pendientes; llamado todavía no está programado. La primera entrega de pausas y disponibilidad está implementada en servicios conforme a la decisión 007, sin incorporar esas acciones en esta pantalla.

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

Status muestra información en tarjetas por oficina, con orden fijo: operador y disponibilidad, ciudadanos en espera, espera más larga y duración de la atención actual. Distingue Libre, Ocupado y En pausa conforme a la decisión 006. La etiqueta Inactivo aparece en los documentos y prototipos anteriores, pero su significado funcional sigue pendiente; no se equipara a la desactivación de la cuenta.

## Oficinas, trámites y asignaciones

El administrador configura oficinas, trámites, cuentas, roles y asignaciones. Los trámites se gestionan desde Trámites y se vinculan a una única oficina.

El nombre de una oficina es único en todo el sistema. El nombre de un trámite es único dentro de su oficina y puede repetirse en otras oficinas. Estas reglas incluyen registros activos y desactivados. Al comparar nombres, no se distinguen mayúsculas y minúsculas ni espacios al principio o al final.

La oficina de un trámite queda fija desde su creación y no puede cambiarse posteriormente. Si el trámite se ofrece en otra oficina, se crea un nuevo registro asociado a ella. El anterior se desactiva cuando deje de ofrecerse en su oficina original, conservando su historial.

Para el lanzamiento se contempla un operador por oficina como organización inicial, no como una prohibición técnica de una segunda asignación. La posibilidad de más operadores por oficina se conserva para el crecimiento del sistema. Un operador puede tener varias oficinas asignadas por el administrador; no selecciona oficinas desde su panel.

El administrador solo puede crear una asignación entre operador y oficina cuando la cuenta tiene rol `OPERADOR`, la cuenta está activa y la oficina está activa.

El administrador retira una oficina a un operador mediante la desactivación de su asignación, sin eliminar el registro. Puede reactivarla utilizando el mismo registro cuando la cuenta tenga rol `OPERADOR` y tanto la cuenta como la oficina estén activas. Las atenciones anteriores conservan su historial.

No se permite desactivar una asignación operador-oficina mientras ese operador tenga folios asignados sin finalizar en esa oficina. Los folios que esperan en la cola de la oficina sin operador asignado no bloquean la desactivación.

El administrador no puede cambiar una cuenta de rol `OPERADOR` a otro rol mientras tenga asignaciones de oficinas activas o folios asignados sin finalizar. Primero deben resolverse los folios conforme a los acuerdos y desactivarse las asignaciones. Se conservan los registros y el historial. Si la cuenta vuelve a tener rol `OPERADOR`, el administrador puede reactivar sus asignaciones bajo las condiciones ya aprobadas.

El sistema no permitirá eliminar físicamente oficinas ni trámites. Se utilizará la desactivación y se conservarán sus registros y referencias históricas. Desactivar una oficina evita nuevos registros en ella y permite terminar los folios pendientes. Puede reactivarse. Desactivar una cuenta bloquea su acceso y conserva su historial; también puede reactivarse.

Un trámite desactivado deja de estar disponible para nuevos registros. El administrador puede reactivarlo, conservando el mismo registro y su historial. Para admitir nuevos registros, tanto el trámite como su oficina deben estar activos.

## Recorrido de atención

El recorrido normal es: **En espera → Llamado → En atención → Finalizado**.

La cola conjunta reúne los folios **En espera** de todas las oficinas donde el operador tiene asignación activa. “Llamar al siguiente” selecciona la **llegada original más antigua entre esas oficinas**, sin que el operador seleccione una oficina desde su panel. Desactivar una oficina no excluye sus folios pendientes de esa cola ni impide atenderlos, mientras el operador conserve la asignación activa; sigue impidiendo nuevos registros conforme al acuerdo existente.

1. Recepción registra el folio.
2. El operador llama al ciudadano con la llegada original más antigua de su cola conjunta. El folio pasa a Llamado y queda reservado y asignado al operador que realizó el llamado.
3. Cuando el ciudadano se presenta, ese operador pulsa Iniciar atención. El folio pasa a En atención y se registra la fecha y hora de inicio.
4. El operador registra una nota y confirma la finalización.

**Asignar responsabilidad al llamar y registrar el inicio de atención son momentos distintos.** Otro operador no puede llamar ni iniciar el mismo folio por su cuenta. Se conserva la reasignación administrativa ya acordada cuando el responsable está desactivado, con motivo e historial. Estos acuerdos se registran en la [decisión 004](decisiones/004-cola-y-responsabilidad-de-folios.md); el registro inicial ya está implementado, pero llamado y flujo posterior siguen pendientes de implementación.

**Autorización de inicio aprobada el 15 de octubre de 2026:** la autorización para iniciar deriva de la responsabilidad vigente sobre el folio actual propio, con cuenta activa y rol funcional `OPERADOR`. No se exige nuevamente una asignación operador-oficina activa. Los flags técnicos `is_staff` e `is_superuser` no sustituyen el rol. Esta regla no modifica la prohibición de retirar asignaciones mientras existan folios asignados sin finalizar ni los requisitos vigentes de asignación para recibir nuevos folios. La desactivación de oficina o trámite no impide iniciar el folio propio pendiente.

El diseño de inicio se documenta en la [decisión 013](decisiones/013-diseno-inicio-de-atencion.md). Su implementación, migración y pruebas siguen pendientes; la consulta del folio propio no ejecuta ni autoriza por sí sola la transición.

No se llama automáticamente al siguiente ciudadano. Tras finalizar, el operador decide cuándo continuar, sin una espera fija obligatoria. El tiempo transcurrido por sí solo no cierra ni deniega un folio.

Cola de atención tiene Pendientes e Historial. El historial permite buscar por folio o nombre y filtrar por fecha o rango, trámite y estado.

## Disponibilidad y folio actual del operador

Acuerdos aprobados el **11 de octubre de 2026**, documentados en la [decisión 006](decisiones/006-disponibilidad-y-folio-actual-del-operador.md):

- Cada operador puede tener como máximo un folio actual en **Llamado** o **En atención**, contando todas sus oficinas. Debe finalizarlo antes de llamar otro; se conservan los cierres por ausencia o denegación y las excepciones administrativas ya aprobadas.
- **Libre**: sin folio actual y sin pausa; puede llamar sujeto a los permisos y asignaciones vigentes.
- **Ocupado**: tiene un folio actual y no está en pausa; no puede llamar otro.
- **En pausa**: no puede llamar, incluso sin folio actual. La pausa conserva el folio, su responsabilidad, estado y notas.
- Al reanudar queda **Libre** si no tiene folio actual, u **Ocupado** si lo tiene.
- La desactivación de la cuenta bloquea el acceso por separado; no equivale a disponibilidad. Una oficina puede seguir teniendo varios operadores.

Siguen pendientes el significado de Inactivo y el tratamiento de restauraciones o reasignaciones administrativas que pudieran producir un segundo folio actual. No se añaden restricciones ni excepciones administrativas para resolverlo; véase la decisión 006. Llamado, disponibilidad y pausa todavía no están programados.

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

La disponibilidad del operador pasa a En pausa y no puede llamar, incluso sin folio actual. Al reanudar queda Libre u Ocupado según tenga un folio actual. El folio conserva su asignación al operador, su estado y sus notas. Recepción consulta la pausa en Status. El administrador consulta operador, motivo, inicio, fin, duración, oficina y folio asociado en Registro de actividad.

**Regla aprobada el 15 de octubre de 2026:** para pasar de Llamado a En atención, el operador debe haber cerrado su pausa. Reanudar no inicia automáticamente la atención. Una solicitud que obtuvo `EN_PAUSA` conserva ese resultado al repetirse con la misma clave; iniciar después requiere una nueva intención explícita.

La implementación, migración y pruebas de inicio siguen pendientes. La [decisión 013](decisiones/013-diseno-inicio-de-atencion.md) cierra su diseño técnico con las reglas aprobadas de pausa y responsabilidad vigente; no acredita su implementación ni validación.

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

La programación de llamado, disponibilidad, pausa y demás acciones posteriores al registro inicial sigue pendiente. La implementación deberá verificar estos permisos y transiciones también en el servidor.
