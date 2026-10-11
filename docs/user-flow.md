# Flujos de usuario

Este documento describe los recorridos previstos de la versión 1 conforme a los [acuerdos vigentes](acuerdos-vigentes.md), que prevalecen sobre las propuestas anteriores. El registro inicial de folios está implementado conforme a la [decisión 005](decisiones/005-registro-inicial-de-folios.md). Los recorridos posteriores y las pantallas siguen pendientes; llamado, disponibilidad y pausa todavía no están programados. Las oficinas y los trámites son configurables. Las citas programadas y la IA quedan fuera de estos flujos.

## Acceso común

1. El usuario accede al mismo formulario de inicio de sesión con usuario y contraseña.
2. El sistema autentica al usuario y obtiene su único rol (Administrador, Recepción u Operador) y sus permisos.
3. El sistema lo dirige al espacio de administrador, recepción u operación que corresponda.
4. Cada acción y consulta se valida según sus permisos; la implementación deberá verificar permisos y transiciones también en el servidor. El operador solo puede atender en oficinas asignadas.

Si la autenticación falla, el usuario permanece en el acceso y recibe un mensaje comprensible. Si una acción no está autorizada, el sistema la rechaza.

El personal usa la clave asignada por el administrador. No se exige cambiar una contraseña temporal al iniciar sesión. Una cuenta desactivada no puede acceder. Este bloqueo es independiente de la disponibilidad del operador.

## Administrador

### Configurar oficinas y trámites

1. Inicia sesión y accede a administración.
2. Consulta y configura el catálogo de oficinas.
3. Desde Trámites configura cada trámite y lo vincula a una sola oficina; una oficina puede tener varios trámites.
4. Guarda los cambios para que las opciones disponibles se utilicen en recepción.

Las oficinas de Registro de Marca y Buró de Crédito son ejemplos iniciales. Este flujo no depende de sus nombres ni de procesos específicos. Los cambios de configuración deben conservar la validez del historial de las atenciones existentes.

Desactivar una oficina impide nuevos registros, permite terminar sus folios pendientes y conserva el historial; puede reactivarse. Un trámite desactivado deja de estar disponible para nuevos registros y conserva el historial.

### Administrar acceso de usuarios

1. Accede a la gestión de usuarios.
2. Crea o gestiona una cuenta con un único rol y establece o cambia su contraseña desde Usuarios; solo el administrador realiza estas acciones.
3. Para un operador, asigna las oficinas en las que puede trabajar: una o varias.
4. Guarda la configuración, que determina su acceso y las acciones permitidas.

Para el lanzamiento se contempla un operador por oficina como organización inicial; una oficina puede tener varios operadores. El operador no selecciona oficinas desde su panel. Desactivar una cuenta bloquea su acceso y conserva su historial; puede reactivarse.

### Consultar y corregir registros

1. En Historial e incidencias consulta atenciones y, en otra pestaña, incidencias y traslados; el detalle conserva datos del folio, motivo, responsable, fecha y oficinas involucradas.
2. En Registro de actividad filtra por fecha, usuario, oficina y acción. Consulta pausas y reanudaciones, cierres, traslados, reasignaciones, correcciones de datos o estados y cambios en cuentas, oficinas, trámites y asignaciones.
3. Si restaura el estado anterior de un folio, registra un motivo obligatorio. Se conservan el registro original y la corrección con sus responsables. Si vuelve a En espera, mantiene la llegada original para su posición en la cola.
4. Si reasigna un folio abierto de un operador desactivado, elige uno activo de la misma oficina y registra un motivo obligatorio. Se conservan oficina, estado, notas y autores, y la reasignación queda en el historial.

## Recepción

### Registrar al ciudadano y dejarlo en espera

1. Inicia sesión y accede al espacio de recepción.
2. Captura el nombre completo del ciudadano.
3. Captura correo electrónico y teléfono cuando se proporcionan; puede dejar ambos vacíos.
4. Elige manualmente la oficina según su juicio y responsabilidad, y después un trámite de esa oficina.
5. Confirma el registro.
6. El sistema valida el nombre, el trámite y la oficina. Si falta un dato obligatorio, solicita corregirlo antes de guardar.
7. El sistema genera el folio y asocia automáticamente al responsable y la fecha y hora de llegada, junto con el trámite y la oficina seleccionados.
8. La atención queda **En espera**. La confirmación muestra folio, ciudadano, oficina, trámite, llegada y responsable; permite consultar el detalle o registrar otra atención.

El registro no puede completarse sin nombre, trámite u oficina. Si falta una opción necesaria en los catálogos, su configuración corresponde al administrador; no se reemplaza por un nombre fijo en el código.

### Consultar, corregir datos y revisar disponibilidad

1. Consulta folios en Atenciones del día y Detalle de atención.
2. Puede corregir nombre, correo y teléfono. Se conservan valores anteriores y nuevos, responsable, fecha y oficina.
3. En Status consulta tarjetas por oficina con orden fijo: operador y disponibilidad, ciudadanos en espera, espera más larga y duración de la atención actual. Distingue Libre, Ocupado y En pausa conforme a la decisión 006. La etiqueta Inactivo aparece en los documentos y prototipos anteriores, pero su significado funcional sigue pendiente; no se equipara a la desactivación de la cuenta.

## Operador de oficina

### Consultar, llamar e iniciar una atención

1. Inicia sesión y accede al espacio de operación.
2. Consulta Pendientes en la cola conjunta: reúne los folios En espera de todas las oficinas donde tiene asignación activa. No selecciona oficinas desde su panel.
3. Si está Libre (sin pausa ni folio actual en Llamado o En atención en ninguna de sus oficinas), puede pulsar Llamar al siguiente, sujeto a sus permisos y asignaciones vigentes. El sistema selecciona la llegada original más antigua entre esas oficinas. El folio pasa de **En espera** a **Llamado** y queda reservado y asignado al operador que realizó el llamado.
4. Cuando el ciudadano se presenta, ese operador pulsa Iniciar atención.
5. El sistema verifica el estado Llamado, la responsabilidad asignada y el permiso del operador para la oficina del folio.
6. El folio pasa a **En atención** y se registran automáticamente la fecha y hora de inicio; su responsable ya quedó asignado al llamar.

Cada operador puede tener como máximo un folio actual en Llamado o En atención, contando todas sus oficinas. Mientras lo tenga y no esté en pausa, queda Ocupado y debe finalizarlo antes de llamar otro. En pausa tampoco puede llamar, incluso sin folio actual. Se conservan los cierres por ausencia o denegación y las excepciones administrativas aprobadas.

**La asignación de responsabilidad y el inicio de atención son momentos distintos.** Otro operador no puede llamar ni iniciar el mismo folio por su cuenta; se impiden llamadas duplicadas y un segundo inicio simultáneo. Se mantiene la reasignación administrativa ya acordada si el responsable está desactivado, con motivo e historial.

Desactivar una oficina no excluye sus pendientes de la cola conjunta ni impide atenderlos cuando el operador conserva la asignación activa; sigue impidiendo nuevos registros. No se llama automáticamente al siguiente: tras finalizar, el operador decide cuándo continuar sin una espera fija obligatoria. El tiempo transcurrido por sí solo no cierra ni deniega un folio.

La [decisión 004](decisiones/004-cola-y-responsabilidad-de-folios.md) registra estos acuerdos aprobados; la [decisión 006](decisiones/006-disponibilidad-y-folio-actual-del-operador.md) registra disponibilidad y el máximo de un folio actual, aprobados el 11 de octubre de 2026. El registro inicial ya está implementado; llamado, disponibilidad y pausa todavía no están programados.

### Agregar información durante la atención

1. Consulta los datos y el historial disponibles según sus permisos.
2. Escribe los detalles de la atención en el espacio de texto libre.
3. Guarda la nota.
4. El sistema conserva la nota con autor, fecha y oficina.
5. Puede editar la nota mientras la atención está abierta. La redacción y extensión dependen del operador.

Tras finalizar, la nota queda disponible para consulta.

### Finalizar el trámite

1. Registra una nota con contenido para describir lo ocurrido.
2. Confirma la finalización.
3. El sistema registra **Finalizado** y la fecha y hora de fin, conservando datos, notas e incidencias en el historial.

No se selecciona Concretado / No concretado; lo ocurrido se describe en la nota. Tras cerrar el folio actual, el operador queda Libre si no está en pausa; si está en pausa, sigue sin poder llamar.

### Consultar el historial

1. Abre Historial en Cola de atención.
2. Busca por folio o nombre y filtra por fecha o rango, trámite y estado.
3. Consulta los registros según sus permisos.

## Variantes y excepciones

### Denegación y cierre por ausencia

1. El operador decide denegar antes o después de llamar, o Recepción decide cerrar por ausencia sin exigir llamada previa.
2. El responsable registra un motivo y confirma el cierre bajo su responsabilidad.
3. El folio pasa a **Finalizado** y el motivo se conserva como nota de cierre con responsable, fecha, hora y oficina.

La demora por sí sola no justifica estas decisiones.

### Consultar incidencias

1. El administrador consulta incidencias y traslados en la pestaña correspondiente de Historial e incidencias.
2. Consulta el detalle con datos del folio, motivo, responsable, fecha y oficinas involucradas. Se conservan la descripción, la autoría y los tiempos asociados a la incidencia.

Una incidencia no implica por sí sola el cierre. Los acuerdos no precisan un flujo general de captura ni permisos adicionales para esa captura; no se atribuye aquí esa acción a un rol.

### Traslado por Recepción

1. Recepción identifica un folio **En espera** que necesita trasladar.
2. Selecciona nueva oficina, un trámite de esa oficina y el motivo.
3. El sistema valida el permiso de Recepción y el estado En espera.
4. Registra responsable, fecha y oficinas involucradas.
5. Conserva folio, historial y llegada original; el folio sigue En espera en la nueva cola, ordenado por esa llegada, sin interrumpir la atención en curso.

El operador no traslada folios desde Atención actual. El traslado no finaliza la atención.

### Pausar y reanudar

1. El operador solicita una pausa en cualquier momento, incluso con un folio Llamado o En atención, y registra el motivo.
2. Su disponibilidad pasa a **En pausa** y no puede llamar, incluso sin folio actual; el folio conserva su responsabilidad, estado y notas.
3. Reanuda cuando lo decide, sin autorización administrativa. Queda **Libre** si no tiene folio actual, u **Ocupado** si tiene uno en Llamado o En atención.

Recepción consulta la pausa en Status. El administrador consulta operador, motivo, inicio, fin, duración, oficina y folio asociado en Registro de actividad. Los prototipos muestran separados el tiempo desde el inicio de atención y el tiempo de pausa.

## Ambigüedades pendientes

El significado funcional de Inactivo y el tratamiento de restauraciones o reasignaciones administrativas que pudieran producir un segundo folio actual siguen pendientes en la decisión 006. Este flujo no los resuelve ni cambia las excepciones administrativas aprobadas.

## Resumen del recorrido y su trazabilidad

| Paso | Estado o evento | Información registrada |
| --- | --- | --- |
| Recepción confirma el registro | En espera | Ciudadano, trámite, oficina, usuario de recepción y llegada. |
| Operador llama al siguiente | Llamado | Llegada original más antigua de la cola conjunta; folio reservado y asignado al operador que llamó. |
| Operador responsable inicia la atención | En atención | Fecha y hora de inicio, distintas del momento de asignación al llamar. |
| Operador escribe o edita la nota | Nota de atención abierta | Texto, autor, fecha y oficina. |
| Administrador consulta una incidencia | Incidencia asociada | Descripción, responsable, fecha y oficinas involucradas. |
| Recepción traslada | En espera en la nueva oficina | Nueva oficina y trámite, motivo, responsable y fecha; folio, historial y llegada original conservados. |
| Operador finaliza o deniega; Recepción cierra por ausencia | Finalizado | Nota de cierre, motivo cuando corresponde, responsable y tiempos. |
| Operador pausa o reanuda | Disponibilidad; asignación y estado del folio sin cambio | Motivo, inicio, fin, duración, oficina y folio asociado. |
| Recepción corrige datos | Corrección registrada | Valores anteriores y nuevos, responsable, fecha y oficina. |
| Administrador restaura o reasigna | Corrección administrativa | Motivo, responsables y evidencia original; llegada o estado conservados según la acción. |

Las descripciones y notas las aportan los usuarios. El sistema registra automáticamente la autoría y los tiempos asociados, y conserva las relaciones necesarias para reconstruir el recorrido.
