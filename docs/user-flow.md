# Flujos de usuario

Este documento describe el recorrido de los tres roles en la versión 1. Las oficinas y los trámites se obtienen de catálogos configurables. Las citas programadas y las funciones de IA no participan en estos flujos.

## Acceso común

1. El usuario accede al mismo formulario de inicio de sesión, independientemente de su rol.
2. El sistema autentica al usuario y obtiene su rol y permisos.
3. El sistema lo dirige al espacio de administrador, recepción u operación que corresponda.
4. Cada acción y consulta se valida según sus permisos. El operador solo puede atender en oficinas autorizadas.

Si la autenticación falla, el usuario permanece en el acceso y recibe un mensaje comprensible. Si una acción no está autorizada, el sistema la rechaza.

## Administrador

### Configurar oficinas y trámites

1. Inicia sesión y accede a administración.
2. Consulta y configura el catálogo de oficinas.
3. Consulta y configura el catálogo de trámites.
4. Guarda los cambios para que las opciones disponibles se utilicen en recepción.

Las oficinas de Registro de Marca y Buró de Crédito son ejemplos iniciales. Este flujo no depende de sus nombres ni de procesos específicos. Los cambios de configuración deben conservar la validez del historial de las atenciones existentes.

### Administrar acceso de usuarios

1. Accede a la gestión de usuarios.
2. Configura el rol y los permisos del usuario correspondiente.
3. Para un operador, asigna las oficinas en las que puede trabajar: una o varias.
4. Guarda la configuración, que determina su acceso y las acciones permitidas.

## Recepcionista

### Registrar al ciudadano y dejarlo en espera

1. Inicia sesión y accede al espacio de recepción.
2. Captura el nombre completo del ciudadano.
3. Captura correo electrónico y teléfono cuando se proporcionan; puede dejar ambos vacíos.
4. Selecciona el trámite y la oficina de los catálogos disponibles.
5. Confirma el registro.
6. El sistema valida el nombre, el trámite y la oficina. Si falta un dato obligatorio, solicita corregirlo antes de guardar.
7. El sistema guarda el registro y asocia automáticamente al recepcionista y la fecha y hora de llegada, junto con el trámite y la oficina seleccionados.
8. La atención queda **en espera** para la oficina elegida.

El registro no puede completarse sin nombre, trámite u oficina. Si falta una opción necesaria en los catálogos, su configuración corresponde al administrador; no se reemplaza por un nombre fijo en el código.

## Operador de oficina

### Consultar e iniciar una atención

1. Inicia sesión y accede al espacio de operación.
2. El sistema presenta las oficinas para las que tiene autorización.
3. Si tiene varias oficinas autorizadas, elige en cuál va a trabajar.
4. Consulta los registros en espera de esa oficina y abre la atención correspondiente.
5. Inicia la atención.
6. El sistema verifica que sigue en espera y que el operador tiene permiso para esa oficina.
7. La atención pasa a **en atención** y se registran automáticamente el operador y la fecha y hora de inicio.

Si otro operador ya inició la misma atención, el sistema impide un segundo inicio simultáneo. El criterio para elegir la siguiente atención está pendiente de definición.

### Agregar información durante la atención

1. Consulta los datos y el historial disponibles según sus permisos.
2. Escribe los detalles de la atención en el espacio de texto libre.
3. Guarda la nota.
4. El sistema agrega una entrada al historial con su autor, fecha y hora.
5. Puede agregar nuevas notas mientras atiende. Cada nota conserva su propia autoría y momento de registro.

Las notas anteriores se mantienen. Si necesita aclarar o corregir información, agrega otra entrada en lugar de sobrescribirla.

### Finalizar el trámite

1. Registra la información necesaria para describir la atención realizada.
2. Selecciona el resultado **trámite finalizado** y confirma el cierre.
3. El sistema registra el resultado y la fecha y hora de fin.
4. La atención queda **finalizada**, con sus datos, notas e incidencias conservados en el historial.

## Variantes y excepciones

### Trámite no concretado

1. El operador determina que el trámite no se concretó.
2. Registra una explicación vinculada a la atención.
3. Selecciona el resultado **no concretado** y confirma el cierre.
4. El sistema registra la fecha y hora de fin y conserva el historial completo.

Este resultado es distinto de un trámite finalizado. No se presupone un catálogo de motivos específicos.

### Registrar una incidencia

1. Un usuario con permiso para registrar incidencias identifica una situación durante el recorrido de atención.
2. Registra su descripción y la vincula a la atención.
3. El sistema conserva la incidencia con su autor, fecha y hora.
4. La atención continúa o se cierra según lo que corresponda, dejando su resultado explícito.

Registrar una incidencia no cierra automáticamente la atención. Los roles autorizados y cualquier regla adicional de tratamiento deben definirse antes de implementar este flujo.

### Transferencia excepcional

1. Un usuario autorizado identifica la necesidad de transferir la atención.
2. Selecciona una oficina de destino del catálogo y registra el motivo.
3. El sistema valida la autorización y las reglas de transferencia que se definan.
4. Registra el origen, el destino, el usuario y la fecha y hora de la transferencia.
5. Conserva las oficinas previas, los operadores participantes, sus tiempos, las notas y las incidencias.
6. La atención continúa en la oficina de destino con un operador autorizado para esa oficina.

La transferencia es una excepción y no equivale a finalizar el trámite. Están pendientes los roles que pueden ejecutarla, los estados desde los que se permite, el cierre de un tramo activo y el estado de llegada al destino. Estos puntos deben resolverse antes de implementar la transición.

## Resumen del recorrido y su trazabilidad

| Paso | Estado o evento | Información registrada |
| --- | --- | --- |
| Recepción confirma el registro | En espera | Ciudadano, trámite, oficina, usuario de recepción y llegada. |
| Operador inicia la atención | En atención | Operador y fecha y hora de inicio. |
| Operador agrega una nota | Nueva entrada en el historial | Texto, autor, fecha y hora. |
| Usuario autorizado registra una incidencia | Incidencia asociada | Descripción, autor, fecha y hora. |
| Usuario autorizado transfiere excepcionalmente | Transferencia asociada | Origen, destino, motivo, usuario, fecha y hora; historial previo conservado. |
| Operador cierra la atención | Finalizado o no concretado | Resultado, explicación cuando no se concreta y fecha y hora de fin. |

Las descripciones y notas las aportan los usuarios. El sistema registra automáticamente la autoría y los tiempos asociados, y conserva las relaciones necesarias para reconstruir el recorrido.
