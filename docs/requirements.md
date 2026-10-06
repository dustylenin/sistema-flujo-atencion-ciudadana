# Requisitos del sistema

Este documento define los requisitos de la versión 1 conforme a los [acuerdos vigentes](acuerdos-vigentes.md), que prevalecen sobre las propuestas anteriores. La aplicación todavía no está implementada; las revisiones corresponden a prototipos visuales. No se establece una tecnología de implementación.

## Requisitos funcionales

### Autenticación y permisos

| ID | Requisito |
| --- | --- |
| RF-01 | Ofrecer un único inicio de sesión con usuario y contraseña para Administrador, Recepción y Operador. Cada cuenta tiene un único rol. |
| RF-02 | Redirigir al usuario autenticado al espacio correspondiente a su rol y permisos. |
| RF-03 | Restringir las acciones y el acceso a la información según el rol y los permisos del usuario. |
| RF-04 | Permitir solo al administrador crear cuentas, establecer o cambiar contraseñas, gestionar roles y asignar una o varias oficinas a un operador. El operador no selecciona oficinas desde su panel. No se exige cambio de contraseña temporal al iniciar sesión. Desactivar una cuenta bloquea su acceso y conserva su historial; puede reactivarse. |

### Catálogos administrables

| ID | Requisito |
| --- | --- |
| RF-05 | Permitir al administrador configurar oficinas sin modificar código. Desactivar una oficina impide nuevos registros, permite terminar folios pendientes y conserva el historial. Puede reactivarse. |
| RF-06 | Permitir al administrador configurar trámites desde Trámites sin modificar código. Cada trámite pertenece a una sola oficina; una oficina puede tener varios trámites. Desactivar un trámite impide nuevos registros y conserva su historial. |
| RF-07 | Usar los catálogos configurados para que Recepción elija manualmente la oficina y después un trámite de esa oficina, según su juicio y responsabilidad. |

Oficina de Registro de Marca y Oficina de Buró de Crédito son ejemplos. No se exige un catálogo fijo ni se definen trámites particulares de esas oficinas.

### Registro en recepción

| ID | Requisito |
| --- | --- |
| RF-08 | Permitir al recepcionista registrar el nombre completo del ciudadano como dato obligatorio. Un valor vacío o compuesto únicamente por espacios no es válido. |
| RF-09 | Permitir registrar correo electrónico y número de teléfono como datos opcionales. Su ausencia no impide el registro. |
| RF-10 | Exigir la selección manual de una oficina disponible y después de un trámite de esa oficina. |
| RF-11 | Generar el folio y registrar automáticamente el responsable y la fecha y hora de llegada, junto con la oficina y el trámite. La confirmación muestra folio, ciudadano, oficina, trámite, llegada y responsable; permite consultar el detalle o registrar otra atención. |
| RF-12 | Dejar el folio En espera para la oficina seleccionada. Recepción puede corregir nombre, correo y teléfono, conservando valores anteriores y nuevos, responsable, fecha y oficina. |

### Atención por operadores

| ID | Requisito |
| --- | --- |
| RF-13 | Permitir al operador consultar pendientes e historial de sus oficinas asignadas en Cola de atención. El historial permite buscar por folio o nombre y filtrar por fecha o rango, trámite y estado. |
| RF-14 | Permitir llamar al ciudadano con la llegada más antigua de la cola correspondiente, pasando de En espera a Llamado. Cuando se presenta, el operador pulsa Iniciar atención; pasa a En atención y se registran operador, fecha y hora de inicio. |
| RF-15 | Ofrecer texto libre para la nota de atención. El operador puede editarla mientras la atención está abierta; la redacción y extensión dependen de él. |
| RF-16 | Conservar las notas vinculadas a la atención con autor, fecha y oficina. Tras finalizar quedan disponibles para consulta. |
| RF-17 | Exigir una nota con contenido y confirmación para finalizar; registrar Finalizado y la fecha y hora de fin. Lo ocurrido se describe en la nota, sin clasificación Concretado / No concretado. |

Para el lanzamiento se contempla un operador por oficina; más operadores se conservan como posibilidad de crecimiento. No se llama automáticamente al siguiente ciudadano: el operador decide cuándo continuar, sin espera fija obligatoria. El tiempo transcurrido por sí solo no cierra ni deniega un folio.

### Incidencias, transferencias e historial

| ID | Requisito |
| --- | --- |
| RF-18 | Conservar incidencias asociadas a la atención con descripción, responsable, fecha y hora. Historial e incidencias permite al administrador consultar atenciones y, en otra pestaña, incidencias y traslados, con datos del folio, motivo, responsable, fecha y oficinas involucradas. |
| RF-19 | Permitir al operador denegar antes o después de llamar y a Recepción cerrar por ausencia sin llamada previa. Ambas acciones requieren motivo y confirmación; el folio pasa a Finalizado y el motivo se conserva como nota de cierre con responsable, fecha, hora y oficina. La demora por sí sola no justifica estas decisiones. |
| RF-20 | Permitir a Recepción trasladar únicamente folios En espera, seleccionando nueva oficina, un trámite de esa oficina y motivo. Registrar responsable, fecha y oficinas involucradas. El operador no traslada desde Atención actual. |
| RF-21 | Conservar al trasladar el folio, el historial y la llegada original. Esta llegada determina el lugar en la nueva cola sin interrumpir la atención en curso. |
| RF-22 | Permitir consultar el historial de una atención según los permisos del usuario, con los datos de recepción, la oficina y el trámite, los operadores participantes, los inicios y fines de atención, el resultado, las incidencias, las transferencias y las notas. |

### Pausas, disponibilidad y correcciones aprobadas

- Recepción consulta Status en tarjetas por oficina con orden fijo: operador y disponibilidad, ciudadanos en espera, espera más larga y duración de la atención actual. Distingue Libre, Ocupado, En pausa e Inactivo.
- El operador puede pausar en cualquier momento, incluso con un folio Llamado o En atención, con motivo obligatorio, y reanudar sin autorización administrativa. Su estado pasa a En pausa; el folio conserva estado y notas. Recepción consulta la pausa en Status. El administrador consulta operador, motivo, inicio, fin, duración, oficina y folio asociado en Registro de actividad. Los prototipos separan el tiempo desde el inicio de atención y el tiempo de pausa.
- El administrador puede restaurar el estado anterior con motivo obligatorio, conservando el registro original y la corrección con sus responsables. Si vuelve a En espera conserva la llegada original.
- El administrador puede reasignar un folio abierto de un operador desactivado a uno activo de la misma oficina, con motivo obligatorio. Conserva oficina, estado, notas y autores, y registra la reasignación en el historial.
- Registro de actividad filtra por fecha, usuario, oficina y acción. Reúne pausas y reanudaciones, cierres, traslados, reasignaciones, correcciones de datos o estados y cambios en cuentas, oficinas, trámites y asignaciones. Conserva evidencia de las acciones originales.

### Datos y estados de referencia

| Información | Captura o registro esperado |
| --- | --- |
| Nombre completo | Capturado en recepción; obligatorio. |
| Correo electrónico y teléfono | Capturados en recepción; opcionales. |
| Trámite y oficina inicial | Oficina elegida manualmente y después un trámite de esa oficina; obligatorios. |
| Usuario que registra y llegada | Registrados automáticamente. |
| Operador e inicio de atención | Registrados automáticamente al iniciar la atención. |
| Fin de atención | Registrado automáticamente al finalizarla. |
| Resultado | Estado Finalizado; lo ocurrido se describe en la nota, incluido el motivo de denegación o ausencia. |
| Notas | Texto del operador, editable mientras la atención está abierta y consultable tras finalizar; autor, fecha y oficina. |
| Incidencias | Descripción aportada por un usuario autorizado; autor, fecha y hora registrados automáticamente. |
| Transferencias | Origen, destino y motivo; usuario, fecha y hora registrados automáticamente. |

El recorrido normal es **En espera → Llamado → En atención → Finalizado**. Denegación y ausencia también cierran como Finalizado. Una incidencia no implica por sí sola el cierre. Un traslado mantiene el folio En espera y su llegada original. Una pausa cambia la disponibilidad del operador sin cambiar el estado del folio.

## Requisitos no funcionales

| ID | Categoría | Requisito |
| --- | --- | --- |
| RNF-01 | Seguridad | Validar autenticación, permisos y transiciones también en el servidor, incluida la autorización de oficina del operador. La restricción no debe depender únicamente de ocultar opciones en la interfaz. |
| RNF-02 | Confidencialidad | Proteger los datos personales, las credenciales, las notas y las incidencias mediante controles de acceso y protección durante su transmisión y almacenamiento. |
| RNF-03 | Integridad del historial | Permitir editar la nota mientras la atención está abierta y conservarla para consulta tras finalizar. Las correcciones de datos o estados conservan evidencia de las acciones originales. Los cambios o desactivaciones de catálogos y cuentas no deben eliminar el historial. |
| RNF-04 | Trazabilidad temporal | Generar fechas y horas desde una referencia de tiempo consistente y mostrarlas con una zona horaria identificable. La representación debe permitir reconstruir el orden de los eventos. |
| RNF-05 | Consistencia | Evitar que dos operadores inicien simultáneamente la misma atención y mantener coherentes el estado, los tiempos y el cierre. |
| RNF-06 | Usabilidad | Presentar formularios claros, distinguir campos obligatorios y opcionales y comunicar errores de captura de forma comprensible. |
| RNF-07 | Configurabilidad | Mantener oficinas y trámites como datos administrables, sin depender de nombres o listas fijas en el código. |
| RNF-08 | Evolución de la arquitectura | Conservar notas e incidencias como registros identificables, vinculados a la atención, al autor y al momento de creación. Separar conceptualmente estos datos de cualquier mecanismo futuro de análisis para permitir extensiones sin alterar el historial. |

No se establecen todavía cifras de disponibilidad, tiempos de respuesta, volumen de usuarios ni plazos de conservación. Estas metas requieren información operativa y no deben presentarse como compromisos ya acordados.

## Decisiones pendientes antes de implementar

- El flujo general de captura de incidencias y sus permisos adicionales, que los acuerdos no precisan más allá de la consulta y conservación de registros.
- El alcance de consulta del historial para cada rol y los parámetros operativos de rendimiento y conservación de datos.

La selección manual de oficina, la relación de cada trámite con una sola oficina, el orden de llamada por llegada y las reglas de traslado ya están definidos. El alcance pendiente del historial se limita a lo que no describen las pantallas y funciones acordadas.

## Fuera de la versión 1 y posibles extensiones

Las citas programadas y las funciones de IA quedan fuera de la versión 1. Pueden evaluarse posteriormente como posibles extensiones. RNF-08 prepara la estructura de la información para una eventual evolución; no exige implementar análisis, modelos o servicios de IA.
