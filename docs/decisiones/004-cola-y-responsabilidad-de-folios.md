# 004 — Cola conjunta y responsabilidad de folios desde Llamado

Fecha de aprobación: **10 de octubre de 2026**.

Estado: **acuerdos aprobados; implementación pendiente**.

## Autoridad y contexto

Los [acuerdos vigentes](../acuerdos-vigentes.md) son la fuente principal. Esta decisión concreta cómo opera la cola de un operador con varias oficinas y cuándo se asigna la responsabilidad de un folio. Se refleja en [requisitos](../requirements.md), RF-13, RF-14 y RNF-05, y en [flujos de usuario](../user-flow.md), «Consultar, llamar e iniciar una atención».

Las decisiones [002](002-oficinas-tramites-y-asignaciones.md) y [003](003-servicios-de-asignacion-y-actividad.md) conservan el alcance de asignaciones implementado y los bloqueos provisionales. Los modelos de folios, sus servicios y su flujo de atención todavía no están implementados. Esta aprobación no habilita retirada de asignaciones ni salida de `OPERADOR`.

## Cola conjunta aprobada

- Reúne los folios **En espera** de todas las oficinas donde el operador tiene **asignación activa**.
- “Llamar al siguiente” selecciona el folio con la **llegada original más antigua entre esas oficinas**.
- El operador no selecciona una oficina desde su panel.
- Desactivar una oficina no impide atender sus pendientes ni los excluye de esta cola si la asignación sigue activa. Se mantiene el acuerdo existente: la desactivación impide nuevos registros y conserva los pendientes y su historial.

El traslado conserva la llegada original conforme al acuerdo existente; esa llegada sigue determinando la posición del folio en la cola conjunta de los operadores autorizados para su oficina de destino.

## Responsabilidad desde Llamado

- Al llamar, el folio pasa de **En espera** a **Llamado**, queda reservado y se asigna al operador que realizó el llamado.
- Cuando el ciudadano se presenta, ese operador continúa con **Iniciar atención**, pasando el folio de **Llamado** a **En atención**.
- Otro operador no puede llamar ni iniciar el mismo folio por su cuenta.
- Pausar conserva la asignación y el estado del folio, además de sus notas, conforme al acuerdo de pausas existente.
- Se mantiene la reasignación administrativa ya acordada cuando el responsable está desactivado: operador destino activo de la misma oficina, motivo obligatorio y conservación de estado, oficina, notas, autores e historial.

**Asignar la responsabilidad al llamar y registrar el inicio de atención son momentos distintos.** La responsabilidad queda establecida en Llamado; la fecha y hora de inicio corresponden al paso posterior a En atención. La asignación al llamar no debe registrarse como si la atención ya hubiera comenzado.

## Alcance y pendientes

El recorrido normal sigue siendo **En espera → Llamado → En atención → Finalizado**. Se conservan las excepciones y responsabilidades ya acordadas, la llegada original, la ausencia de llamada automática y la continuidad de pendientes en oficinas desactivadas.

Esta decisión no agrega límites de atención simultánea, prioridades, políticas de numeración o reinicios, ni resuelve otras decisiones pendientes. No incorpora nuevas reglas de incidencias, historial, restauración o cierre.

La implementación posterior deberá comprobar autorización, reserva e inicio en el servidor y protegerlos frente a operaciones concurrentes, conservando responsabilidad y trazabilidad. El diseño técnico, los modelos, las migraciones, las pruebas y las pantallas de folios siguen pendientes. Los bloqueos definitivos de retirada y cambio de rol requieren folios reales y su verificación completa.

Esta etapa actualiza únicamente documentación; no modifica código, pruebas, migraciones ni bases y no atribuye las pruebas anteriores de catálogos o asignaciones a estos acuerdos todavía sin implementar.
