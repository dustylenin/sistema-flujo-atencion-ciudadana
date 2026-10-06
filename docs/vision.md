# Visión del producto

Documento de definición de la versión 1, sujeto a los [acuerdos vigentes](acuerdos-vigentes.md), que prevalecen sobre las propuestas anteriores. Las revisiones corresponden a prototipos visuales: la aplicación todavía no está implementada ni se ha elegido una tecnología de desarrollo.

## Contexto y problema

Una dependencia atiende ciudadanos mediante una red de oficinas. El recorrido comienza en recepción y continúa con un operador de la oficina correspondiente, hasta que se registra el resultado de la atención.

El problema que se busca resolver es mantener una visión consistente de ese recorrido: quién registró al ciudadano, cuándo llegó, qué trámite solicitó, a qué oficina se dirigió, quién lo atendió y qué ocurrió durante la atención. Las notas, las incidencias y los registros de actividad deben conservar su contexto y autoría para reconstruir el recorrido, respetando la edición de la nota mientras la atención está abierta.

No se presupone un sistema previo ni un método actual de trabajo. El proyecto define la solución deseada a partir del flujo proporcionado.

## Objetivo general

Administrar el flujo interno de atención ciudadana y conservar un historial trazable de cada atención, con acceso controlado según el rol y los permisos del usuario.

## Objetivos específicos

- Facilitar el registro en recepción sin exigir correo electrónico ni teléfono.
- Identificar el trámite y la oficina de destino mediante catálogos administrables.
- Permitir a los operadores trabajar en una o varias oficinas según sus autorizaciones.
- Registrar automáticamente los participantes y los tiempos relevantes de la atención.
- Conservar las notas vinculadas con su autor, fecha y oficina, permitiendo su edición mientras la atención está abierta y su consulta tras finalizar.
- Documentar incidencias, motivos de cierre, pausas y traslados sin perder el recorrido previo.
- Preparar la información para un posible análisis futuro de notas e incidencias, sin incorporar IA en la versión 1.

## Usuarios y responsabilidades

| Usuario | Necesidad y responsabilidad |
| --- | --- |
| Administrador | Mantener oficinas y trámites; gestionar cuentas, contraseñas y asignaciones; consultar registros, restaurar estados y reasignar folios abiertos de operadores desactivados. |
| Recepción | Capturar y corregir los datos del ciudadano, elegir oficina y trámite, consultar folios y disponibilidad, trasladar folios En espera y cerrar por ausencia. |
| Operador | Consultar pendientes e historial de sus oficinas asignadas, llamar al siguiente, iniciar la atención, registrar notas, finalizar, denegar y pausar o reanudar. |

El ciudadano es la persona atendida. En esta versión no se contempla un acceso al sistema para ciudadanos.

El inicio de sesión con usuario y contraseña es común a los tres roles. Cada cuenta tiene un único rol. Solo el administrador crea cuentas y establece o cambia contraseñas; no se exige al usuario cambiar una contraseña temporal al iniciar sesión. La navegación posterior y las acciones disponibles dependen del rol y los permisos. Tener acceso a una oficina no concede acceso a todas las demás.

## Alcance de la versión 1

### Registro y seguimiento

Cada registro de atención incluye nombre completo obligatorio, correo y teléfono opcionales. Recepción elige manualmente la oficina y después un trámite de esa oficina. El sistema genera el folio y registra al responsable y la fecha y hora de llegada. Recepción puede corregir los datos del ciudadano, conservando valores anteriores y nuevos, responsable, fecha y oficina.

La atención recorre normalmente En espera → Llamado → En atención → Finalizado. El operador llama al ciudadano con la llegada más antigua y comienza la atención cuando se presenta. Para finalizar, registra una nota con contenido y confirma el cierre. El sistema conserva quién atendió y los tiempos de inicio y fin. No existe la clasificación Concretado / No concretado; lo ocurrido se describe en la nota. El operador decide cuándo continuar, sin llamada automática ni espera fija obligatoria.

Recepción consulta en Status tarjetas por oficina con operador y disponibilidad, ciudadanos en espera, espera más larga y duración de la atención actual, en ese orden. La disponibilidad distingue Libre, Ocupado, En pausa e Inactivo.

### Configuración

Las oficinas y los trámites se administran desde el sistema. Oficina de Registro de Marca y Oficina de Buró de Crédito son ejemplos iniciales, no requisitos de un catálogo fijo. No se definen aquí trámites concretos ni procesos particulares de esas oficinas.

Cada trámite pertenece a una sola oficina y cada oficina puede tener varios trámites. Para el lanzamiento se contempla un operador por oficina; más operadores se conservan como posibilidad de crecimiento. Un operador puede tener varias oficinas asignadas por el administrador y no las selecciona desde su panel. La desactivación de oficinas o trámites impide nuevos registros y conserva el historial; una oficina desactivada permite terminar sus folios pendientes y puede reactivarse. Desactivar una cuenta bloquea el acceso y conserva su historial; puede reactivarse.

### Historial y excepciones

Las notas conservan autor, fecha y oficina. El operador puede editar la nota mientras la atención está abierta; tras finalizar queda disponible para consulta. Historial e incidencias permite consultar atenciones y, en otra pestaña, incidencias y traslados.

Recepción puede trasladar únicamente folios En espera, eligiendo la nueva oficina, un trámite de esa oficina y el motivo. Se conservan el folio, el historial y la llegada original, que determina el lugar en la nueva cola sin interrumpir la atención en curso. El operador no traslada desde Atención actual.

El operador puede denegar antes o después de llamar; Recepción puede cerrar por ausencia sin llamada previa. Ambos cierres requieren motivo y confirmación, dejan el folio Finalizado y conservan el motivo como nota de cierre. El tiempo transcurrido por sí solo no cierra ni deniega un folio.

El operador puede pausar en cualquier momento con motivo y reanudar sin autorización administrativa. El folio conserva su estado y notas. Recepción ve la pausa en Status y el administrador consulta sus datos en Registro de actividad. Los prototipos separan el tiempo desde el inicio de atención y el tiempo de pausa.

El administrador puede restaurar el estado anterior de un folio con motivo, conservando el registro original y la corrección; si vuelve a En espera mantiene la llegada original. También puede reasignar un folio abierto de un operador desactivado a uno activo de la misma oficina, con motivo y conservando estado, notas y autores. Registro de actividad reúne las acciones acordadas y la evidencia de las correcciones.

## Fuera del alcance de la versión 1

- Citas programadas.
- Funciones de inteligencia artificial, incluidos el análisis automático de notas e incidencias y las recomendaciones generadas por modelos.

## Posibles extensiones

- Gestión de citas programadas.
- Análisis de notas e incidencias mediante IA, sujeto a una definición posterior de objetivos, permisos y tratamiento de datos.

Estas extensiones no son requisitos ni compromisos de entrega de la versión 1.

## Criterios de éxito

- Recepción puede registrar una atención con nombre, trámite y oficina, sin correo ni teléfono.
- Los catálogos pueden cambiar desde administración sin modificar el código de aplicación.
- Un operador puede atender folios de sus oficinas asignadas y no puede atender en oficinas sin permiso ni seleccionar oficinas desde su panel.
- El historial permite reconstruir participantes, tiempos, notas, incidencias, transferencias y resultado de la atención.
- El cierre queda registrado como Finalizado y lo ocurrido queda descrito en una nota con contenido, incluido el motivo cuando se deniega o se cierra por ausencia.
