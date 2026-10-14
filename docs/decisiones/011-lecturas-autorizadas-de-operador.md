# 011 — Lecturas autorizadas de Operador

Fecha de aprobación: **14 de octubre de 2026**.

Estado: **diseño aprobado; implementación y pruebas pendientes**.

## Autoridad y alcance

El usuario aprobó la propuesta de consultas de lectura para las primeras pantallas de Operador. Esta decisión registra ese diseño conforme a los [acuerdos vigentes](../acuerdos-vigentes.md) y las decisiones [004](004-cola-y-responsabilidad-de-folios.md), [006](006-disponibilidad-y-folio-actual-del-operador.md), [007](007-diseno-pausas-y-disponibilidad.md) y [008](008-diseno-llamado-y-reserva.md).

El servicio de llamado y reserva y la consulta de disponibilidad ya existen. Las validaciones anteriores no acreditan estos nuevos lectores: su implementación y sus pruebas siguen pendientes. Algunos documentos conservan avisos de etapas previas; esta decisión no reescribe esas evidencias.

Esta etapa modifica únicamente documentación. No implementa código ni pantallas, ejecuta pruebas, migraciones u operaciones sobre bases de datos. Los datos DEMO se conservan.

## Pendientes de la cola conjunta

Contrato aprobado para implementar posteriormente:

```python
consultar_pendientes_operador(*, actor, cursor=None)
```

- Reúne exclusivamente folios **En espera** de todas las oficinas con asignación activa al operador, de cualquier fecha.
- Ordena por **`llegada_original, id`** ascendentes, igual que `llamar_siguiente`. El UUID es el desempate técnico determinista existente; no constituye prioridad funcional ni numeración pública.
- No exige oficina ni trámite activos. Los catálogos desactivados no ocultan pendientes existentes mientras se conserve la asignación activa.
- Una asignación inactiva excluye sus pendientes de la cola del operador.
- Estar ocupado o en pausa no impide consultar pendientes; conserva las restricciones existentes para llamar.
- No admite selección o filtro manual de oficina, ciudadano, estado o fecha, ni operador destino.

Cada elemento devuelve `folio_id` técnico UUID, `nombre_completo`, `estado`, `llegada_original`, identificador y nombre de oficina y de trámite. Los nombres corresponden al catálogo leído, sin presentarlos como una reconstrucción histórica. Esta proyección inicial no incorpora contactos, notas ni historial.

### Paginación técnica

Se aprueban páginas de **50 elementos**, con `cursor_siguiente` opcional. Se lee un elemento adicional para detectar continuación, sin contar toda la cola. El cursor continúa después del par `(llegada_original, id)` del último elemento devuelto; sus tipos y formato se validan. Un cursor inválido produce `ValidationError`.

La paginación limita memoria y tamaño de respuesta; no limita el número de pendientes atendibles ni introduce prioridades. Cada página vuelve a comprobar autorización y asignaciones activas. El cursor no concede acceso ni permite escoger el folio del llamado.

Las páginas no congelan la cola entre peticiones. Registros, reservas o cambios de asignación confirmados pueden cambiar los resultados; se debe poder refrescar desde el principio. Los futuros traslados conservan la llegada original conforme a los acuerdos, sin implementar esa operación en esta entrega.

## Folio actual propio

Contrato aprobado para implementar posteriormente:

```python
consultar_folio_actual_operador(*, actor)
```

Devuelve `None` o una proyección con los mismos campos básicos de pendientes y `operador_responsable_id`. Busca globalmente por responsable igual al actor y estado en **LLAMADO o EN_ATENCION**, contando todas sus oficinas.

La responsabilidad y la reserva comienzan desde LLAMADO. La consulta no depende de actividad de oficinas o trámites ni de asignaciones actuales; los cambios posteriores de catálogo o asignación no ocultan el folio propio. Una pausa también conserva su visibilidad.

No recibe identificador de folio ni operador destino y no permite consultar el folio actual de otra persona. El máximo global existente protege la unicidad. Incluir EN_ATENCION en el criterio conserva el significado acordado: no habilita ese estado, todavía excluido por los choices y el CHECK actuales, ni agrega fechas de inicio, cierre o notas.

## Autorización y consistencia de lectura

Ambos lectores requieren un actor autenticado, persistido en el alias utilizado, con **cuenta activa y rol funcional OPERADOR releídos de la base**. No se confía en valores de una instancia antigua ni en permisos de la pantalla. Administrador y Recepción no reciben acceso sustitutivo; **`is_staff` e `is_superuser` no sustituyen el rol funcional**.

La denegación produce `PermissionDenied`, incluso si no hay resultados. Debe distinguirse una lectura vacía autorizada de un actor sin autorización.

Cada lector obtiene autorización y datos en **una misma sentencia SQL y una misma instantánea**, partiendo de la fila del actor y utilizando subconsultas para conservar esa distinción cuando la cola esté vacía. En pendientes, la comprobación de asignaciones pertenece a esa instantánea. Se utiliza un único alias de lectura resuelto internamente, sin aceptar un alias del solicitante y sin `select_for_update`.

Los resultados se materializan dentro del servicio como **dataclasses inmutables y tuplas**. No se devuelven modelos, querysets, generadores o relaciones diferidas que puedan ejecutarse después de la autorización o leer otra instantánea.

Consultas sucesivas y páginas distintas pueden observar cambios confirmados; no se promete una instantánea conjunta entre lectores. La lectura no reserva el primer pendiente ni garantiza el resultado del próximo llamado. `llamar_siguiente` conserva su selección y revalidación transaccionales, sin recibir oficina ni ciudadano elegido desde el listado.

## Integración con disponibilidad

Se reutiliza **`consultar_disponibilidad(actor=actor, operador_id=actor.pk)`**, conservando su contrato: identidad, disponibilidad, `pausa_abierta_id` y referencia mínima del folio propio. El nuevo detalle reutiliza el criterio global de `_folios_actuales`.

No se amplían las proyecciones de Recepción ni los permisos del administrador. Libre sigue sujeto a autorización, asignaciones y pendientes. Ocupado y En pausa conservan su significado vigente; no se añade disponibilidad almacenada.

**Estas lecturas no reservan folios, modifican pausas ni escriben eventos o comprobantes.** Los resultados históricos de solicitudes de llamado o pausa no sustituyen la consulta presente de disponibilidad.

## Archivos previstos y pruebas pendientes

| Archivo previsto | Alcance futuro |
| --- | --- |
| `folios/services_operador.py` | Contratos, lectores, autorización, materialización y cursor. |
| `folios/test_lecturas_operador.py` | Acceso, campos, orden, paginación, consistencia y ausencia de escrituras. |
| `folios/test_disponibilidad.py` y `folios/test_llamado.py` | Regresión de contratos e integración con reservas y pausas reales. |

No se requieren cambios de modelos, migraciones, rutas o plantillas para esta entrega de lectores.

Pruebas relevantes, **todavía no implementadas ni ejecutadas para estos lectores**:

- Actores no autenticados, no persistidos o de otro alias; cuenta inactiva y rol incorrecto releídos, incluso con instancias obsoletas y todas las combinaciones de flags técnicos.
- Cola de varias oficinas, exclusión de asignaciones inactivas y oficinas ajenas, pendientes antiguos, llegada original y desempate UUID; catálogos desactivados incluidos.
- Páginas de 50, continuación sin duplicados con datos estables, cursor inválido y revalidación de permisos y asignaciones entre páginas.
- Folio actual propio reservado mediante llamado real, exclusión de folios ajenos, resultado vacío y conservación ante pausa o cambios posteriores de catálogo o asignación. Los estados históricos controlados no habilitan retirada pública de asignaciones.
- Disponibilidad Libre, Ocupado y En pausa y conservación de las proyecciones actuales por rol. EN_ATENCION mantiene su verificación pendiente hasta implementar inicio.
- Autorización y datos en una sola sentencia por lector, incluida la lectura vacía; resultados inmutables y materializados sin consultas posteriores al consumirlos.
- Únicamente sentencias SELECT, sin bloqueos de reserva y sin cambios en folios, pausas, eventos o comprobantes.

Una ejecución futura requerirá conservar nuevamente DEMO conforme al [registro 014](../pruebas/014-validacion-llamado-y-reserva-postgresql.md). Esta aprobación documental no autoriza limpiar sus datos ni ejecuta el runner.

## Exclusiones y decisiones realmente pendientes

Pendientes representa la cola operativa actual. **Historial**, búsquedas por folio o nombre y filtros por fecha, trámite o estado quedan fuera de esta entrega. También quedan fuera pantallas, inicio de atención, notas, finalización, cierres y correcciones administrativas.

No queda una decisión funcional que bloquee estos lectores mínimos. Permanecen pendientes el formato público del folio, permisos ampliados de consulta, presentación de pausas sin oficina, significado de Inactivo y tratamiento de restauraciones o reasignaciones administrativas que pudieran producir un segundo folio actual. No se añaden permisos, rechazos, liberaciones ni excepciones para resolverlos.
