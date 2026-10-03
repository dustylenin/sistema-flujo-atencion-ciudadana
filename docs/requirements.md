# Requisitos del sistema

Este documento define los requisitos de la versión 1. Describe el comportamiento esperado sin establecer una tecnología de implementación. Las decisiones pendientes y las posibles extensiones se distinguen de los requisitos confirmados.

## Requisitos funcionales

### Autenticación y permisos

| ID | Requisito |
| --- | --- |
| RF-01 | Ofrecer un único inicio de sesión para administrador, recepcionista y operador de oficina. |
| RF-02 | Redirigir al usuario autenticado al espacio correspondiente a su rol y permisos. |
| RF-03 | Restringir las acciones y el acceso a la información según el rol y los permisos del usuario. |
| RF-04 | Permitir al administrador gestionar usuarios, roles y autorizaciones de oficina. Un operador puede estar autorizado para una o varias oficinas. |

### Catálogos administrables

| ID | Requisito |
| --- | --- |
| RF-05 | Permitir al administrador configurar las oficinas disponibles sin modificar código. |
| RF-06 | Permitir al administrador configurar los trámites disponibles sin modificar código. |
| RF-07 | Usar los catálogos configurados para seleccionar la oficina y el trámite al registrar una atención. |

Oficina de Registro de Marca y Oficina de Buró de Crédito son ejemplos. No se exige un catálogo fijo ni se definen trámites particulares de esas oficinas.

### Registro en recepción

| ID | Requisito |
| --- | --- |
| RF-08 | Permitir al recepcionista registrar el nombre completo del ciudadano como dato obligatorio. Un valor vacío o compuesto únicamente por espacios no es válido. |
| RF-09 | Permitir registrar correo electrónico y número de teléfono como datos opcionales. Su ausencia no impide el registro. |
| RF-10 | Exigir la selección de un trámite y una oficina de los catálogos disponibles. |
| RF-11 | Registrar automáticamente el usuario que realizó el registro y la fecha y hora de llegada, junto con la oficina y el trámite seleccionados. |
| RF-12 | Dejar la atención registrada en espera para la oficina seleccionada. |

### Atención por operadores

| ID | Requisito |
| --- | --- |
| RF-13 | Permitir al operador consultar y atender los registros de las oficinas para las que tiene permiso. Si tiene varias oficinas autorizadas, permitirle identificar en cuál está trabajando. |
| RF-14 | Permitir iniciar una atención en espera y registrar automáticamente al operador y la fecha y hora de inicio. |
| RF-15 | Ofrecer un espacio de texto libre para agregar detalles de la atención mediante notas independientes. |
| RF-16 | Conservar cada nota en el historial con su usuario autor, fecha y hora, vinculada a la atención correspondiente. Agregar una nota no sobrescribe las anteriores. |
| RF-17 | Permitir finalizar la atención y registrar su resultado y la fecha y hora de fin. Distinguir el trámite finalizado del trámite no concretado. |

### Incidencias, transferencias e historial

| ID | Requisito |
| --- | --- |
| RF-18 | Permitir registrar incidencias asociadas a una atención y conservar su descripción, usuario que las registra, fecha y hora. |
| RF-19 | Permitir registrar un resultado no concretado y su explicación, conservando las notas e incidencias previas. |
| RF-20 | Contemplar transferencias excepcionales entre oficinas para usuarios autorizados. Registrar oficina de origen, oficina de destino, motivo, usuario y fecha y hora de la transferencia. Las reglas concretas de autorización y ejecución están pendientes de definición. |
| RF-21 | Conservar el recorrido previo al transferir: oficinas, operadores, tiempos, notas e incidencias. Una transferencia no debe borrar ni sustituir información anterior. |
| RF-22 | Permitir consultar el historial de una atención según los permisos del usuario, con los datos de recepción, la oficina y el trámite, los operadores participantes, los inicios y fines de atención, el resultado, las incidencias, las transferencias y las notas. |

### Datos y estados de referencia

| Información | Captura o registro esperado |
| --- | --- |
| Nombre completo | Capturado en recepción; obligatorio. |
| Correo electrónico y teléfono | Capturados en recepción; opcionales. |
| Trámite y oficina inicial | Seleccionados en recepción desde catálogos; obligatorios. |
| Usuario que registra y llegada | Registrados automáticamente. |
| Operador e inicio de atención | Registrados automáticamente al iniciar la atención. |
| Fin de atención | Registrado automáticamente al finalizarla. |
| Resultado | Seleccionado o registrado al cerrar la atención: trámite finalizado o no concretado. |
| Notas | Texto aportado por el operador; autor, fecha y hora registrados automáticamente por entrada. |
| Incidencias | Descripción aportada por un usuario autorizado; autor, fecha y hora registrados automáticamente. |
| Transferencias | Origen, destino y motivo; usuario, fecha y hora registrados automáticamente. |

Los estados de referencia son **en espera**, **en atención**, **finalizado** y **no concretado**. Los dos últimos representan el cierre y su resultado. Una incidencia es un evento del historial y no implica por sí sola que la atención haya terminado. Una transferencia tampoco equivale a un trámite finalizado; su efecto sobre la espera o la atención en curso debe definirse antes de implementarla.

## Requisitos no funcionales

| ID | Categoría | Requisito |
| --- | --- | --- |
| RNF-01 | Seguridad | Validar autenticación y permisos en cada operación protegida, incluida la autorización de oficina del operador. La restricción no debe depender únicamente de ocultar opciones en la interfaz. |
| RNF-02 | Confidencialidad | Proteger los datos personales, las credenciales, las notas y las incidencias mediante controles de acceso y protección durante su transmisión y almacenamiento. |
| RNF-03 | Integridad del historial | Conservar las notas existentes sin sobrescritura. Las aclaraciones o correcciones se agregan como nuevas entradas. Los cambios en catálogos no deben eliminar ni invalidar el historial registrado. |
| RNF-04 | Trazabilidad temporal | Generar fechas y horas desde una referencia de tiempo consistente y mostrarlas con una zona horaria identificable. La representación debe permitir reconstruir el orden de los eventos. |
| RNF-05 | Consistencia | Evitar que dos operadores inicien simultáneamente la misma atención en espera y mantener coherentes el estado, los tiempos y el resultado. |
| RNF-06 | Usabilidad | Presentar formularios claros, distinguir campos obligatorios y opcionales y comunicar errores de captura de forma comprensible. |
| RNF-07 | Configurabilidad | Mantener oficinas y trámites como datos administrables, sin depender de nombres o listas fijas en el código. |
| RNF-08 | Evolución de la arquitectura | Conservar notas e incidencias como registros identificables, vinculados a la atención, al autor y al momento de creación. Separar conceptualmente estos datos de cualquier mecanismo futuro de análisis para permitir extensiones sin alterar el historial. |

No se establecen todavía cifras de disponibilidad, tiempos de respuesta, volumen de usuarios ni plazos de conservación. Estas metas requieren información operativa y no deben presentarse como compromisos ya acordados.

## Decisiones pendientes antes de implementar

- Qué roles y permisos permiten registrar incidencias y ejecutar transferencias excepcionales.
- En qué estados se permite transferir, cómo se cierra un tramo de atención activo y cómo queda el registro en la oficina de destino.
- Qué criterio se utiliza para seleccionar la siguiente atención en espera; no se presupone prioridad ni orden obligatorio.
- Si los trámites se habilitan para oficinas específicas y, en su caso, cómo se configura esa relación.
- El alcance de consulta del historial para cada rol y los parámetros operativos de rendimiento y conservación de datos.

## Fuera de la versión 1 y posibles extensiones

Las citas programadas y las funciones de IA quedan fuera de la versión 1. Pueden evaluarse posteriormente como posibles extensiones. RNF-08 prepara la estructura de la información para una eventual evolución; no exige implementar análisis, modelos o servicios de IA.
