# 006 — Disponibilidad y folio actual del operador

Fecha de aprobación: **11 de octubre de 2026**.

Estado: **acuerdos funcionales aprobados; llamado, disponibilidad y pausa pendientes de programación**.

## Autoridad y contexto

Los [acuerdos vigentes](../acuerdos-vigentes.md) son la fuente principal. Esta decisión complementa la [decisión 004](004-cola-y-responsabilidad-de-folios.md), que dejó pendiente el límite simultáneo al aprobar la cola conjunta y la responsabilidad desde Llamado el 10 de octubre de 2026. Ese límite queda resuelto aquí, sin alterar el contexto histórico ni las evidencias anteriores.

El [registro inicial de folios](005-registro-inicial-de-folios.md) ya está implementado: registra En espera y sin operador responsable. Esa implementación y sus pruebas no verifican estos acuerdos. Las asignaciones siguen admitiendo varias oficinas por operador y varios operadores por oficina, conforme a las decisiones [002](002-oficinas-tramites-y-asignaciones.md) y [003](003-servicios-de-asignacion-y-actividad.md).

## Folio actual y límite aprobado

Un folio actual es el folio bajo responsabilidad del operador en **Llamado** o **En atención**. Cada operador puede tener **como máximo uno**, contando todas sus oficinas, no uno por oficina.

Debe finalizar el actual antes de llamar otro. Se conservan los cierres por ausencia o denegación, con motivo y confirmación, y las excepciones administrativas ya aprobadas. No se llama automáticamente al siguiente y el tiempo transcurrido por sí solo no cierra ni deniega el folio.

Una oficina puede seguir teniendo varios operadores: el límite de un folio actual corresponde a cada operador y no limita las asignaciones de una oficina.

## Disponibilidad aprobada

| Disponibilidad | Condición | Puede llamar otro folio |
| --- | --- | --- |
| Libre | Sin folio actual y sin pausa. | Sí, sujeto a los permisos y asignaciones vigentes. |
| Ocupado | Tiene un folio en Llamado o En atención y no está en pausa. | No; debe finalizar el actual. |
| En pausa | Tiene una pausa, con o sin folio actual. | No, incluso sin folio actual. |

Cuando un operador con folio actual pausa, su disponibilidad es En pausa y conserva el folio. La pausa no libera su responsabilidad ni modifica el estado o las notas. Requiere motivo y puede reanudarse sin autorización administrativa, conforme al acuerdo vigente.

Al reanudar, queda **Libre** si no tiene folio actual, u **Ocupado** si lo tiene. Cerrar el folio actual no habilita otro llamado mientras continúe en pausa.

La **desactivación de la cuenta** bloquea el acceso por separado y conserva el historial; no equivale a disponibilidad. Estar Libre no sustituye la autorización de acceso ni los permisos y asignaciones de la operación.

## Excepciones conservadas y ambigüedades restantes

Se conserva la restauración administrativa del estado anterior con motivo, registro original y corrección; si vuelve a En espera, mantiene la llegada original. También se conserva la reasignación de un folio abierto de un operador desactivado a uno activo de la misma oficina, con motivo y conservación de oficina, estado, notas, autores e historial.

Los acuerdos no precisan cómo proceder si una restauración o reasignación administrativa pudiera producir un segundo folio actual para un operador. No se define aquí un rechazo, una selección de destino, una liberación automática ni una excepción nueva al máximo aprobado. Esa interacción requiere aclaración funcional antes de implementar los casos afectados.

La etiqueta **Inactivo** aparece en la documentación y los prototipos anteriores, pero los acuerdos de esta fecha no precisan su significado como disponibilidad. Queda pendiente aclararlo; no se inventa una cuarta definición ni se equipara con cuenta desactivada, ausencia de sesión o falta de asignaciones.

## Alcance documental e implementación pendiente

Estos acuerdos se reflejan en [requisitos](../requirements.md), RF-14, RNF-05 y el apartado de pausas y disponibilidad; en [flujos de usuario](../user-flow.md), llamado, cierre, pausa y reanudación; y en el [README](../../README.md).

**Llamado, disponibilidad y pausa todavía no están programados.** La implementación posterior deberá verificar el máximo por operador entre todas sus oficinas y las condiciones de llamado también en el servidor, incluyendo operaciones concurrentes. Esta decisión no prescribe modelos, campos, servicios, mecanismos de bloqueo ni migraciones.

Esta etapa es únicamente documental. No cambia código, pruebas, migraciones ni bases, no ejecuta pruebas de aplicación y no atribuye resultados anteriores a estas reglas pendientes de implementación. Los bloqueos provisionales de retirada de asignaciones y salida de OPERADOR siguen vigentes hasta verificar sus reglas definitivas.
