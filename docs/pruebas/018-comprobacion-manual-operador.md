# 018 — Comprobación manual de pantallas de Operador

- Fecha de registro: **14 de octubre de 2026**.
- Alcance: primera integración de la [decisión 012](../decisiones/012-integracion-pantallas-operador.md), conforme a los [acuerdos vigentes](../acuerdos-vigentes.md).
- Entorno de la comprobación comunicada: **Brave en Linux Mint**, servidor aislado en **`http://127.0.0.1:8001`**, cuenta **`operador_demo`**.
- Versión documentada: `2b18df3b47812a414c86a40419f9be7f40b9eedf` (`feat: integra pantallas y acciones de operador`).

## Fuente y distinción de evidencias

El usuario confirmó los resultados mediante capturas y su reporte. Este registro documenta esa comprobación realizada por el usuario; el asistente no ejecutó la sesión de navegador ni inspeccionó directamente la base durante esta etapa. Las capturas no se incorporan al repositorio ni se reproducen nombres de ciudadanos, contactos, contraseñas o identificadores privados de folios.

La evidencia visual comunicada corresponde a los estados mostrados en pantalla: navegación, cola inicial, folio Llamado y responsable, disponibilidad, cola restante y conservación del folio durante la pausa. Las capturas de estados no acreditan por sí solas la secuencia de acciones, el uso de teclado, la recarga o la desactivación de JavaScript. Esas interacciones se registran como **resultados reportados y confirmados por el usuario**.

## Resultados confirmados

| Comprobación | Resultado y tipo de evidencia |
| --- | --- |
| Acceso y navegación | El usuario entró como `operador_demo`. La evidencia visual comunicada muestra únicamente **Cola de atención** y **Atención actual** como entradas de navegación. |
| Cola inicial | La evidencia visual comunicada muestra **dos pendientes ordenados por llegada**. Este caso no acredita paginación de más de 50 elementos ni un empate de llegada. |
| Llamar siguiente | El usuario reportó el llamado del ciudadano más antiguo. La evidencia visual comunicada muestra su folio en **Llamado**, a cargo de **`operador_demo`**, y disponibilidad **Ocupado**. |
| Cola posterior | La evidencia visual comunicada muestra **un pendiente restante** después del llamado reportado. |
| Pausa | El usuario confirmó el motivo obligatorio y la pausa. La evidencia visual comunicada muestra **En pausa**, conservando el mismo folio, estado **Llamado** y responsable **`operador_demo`**. No se publica el texto del motivo. |
| Reanudación y recarga | El usuario confirmó el retorno a **Ocupado** y la conservación de los datos del mismo folio tras recargar. La persistencia aquí se acredita desde la interfaz y su reporte, sin consulta directa a PostgreSQL. |
| Teclado | El usuario confirmó el funcionamiento del foco de teclado. Esto no constituye una auditoría completa de accesibilidad. |
| Ventana estrecha | El usuario confirmó el funcionamiento con la ventana estrecha de Brave en Linux Mint. No se probó un dispositivo móvil real. |
| JavaScript desactivado | El usuario confirmó **pausa y reanudación**, conservando el mismo folio. El llamado sin JavaScript **no se ejecutó manualmente**. |

## Evidencia automatizada anterior

El [registro 017](017-pantallas-operador-postgresql.md) conserva la ejecución anterior de **308 pruebas Django satisfactorias, incluidas las 35 nuevas de Operador**, y **8 pruebas JavaScript satisfactorias** (4 de Operador y 4 de Recepción). También conserva la incidencia corregida en el fixture de acceso y la recuperación DEMO de aquella validación.

**No se volvieron a ejecutar esas pruebas en esta etapa.** La comprobación manual complementa esa evidencia; sus acciones no se suman al número de pruebas automatizadas. El registro 017 permanece sin modificaciones como evidencia histórica del estado anterior a esta sesión manual.

## Límites y conservación del estado manual

La comprobación confirmada cubre el flujo descrito en Brave sobre Linux Mint. No acredita una auditoría completa de accesibilidad, un dispositivo móvil real, todos los errores y estados posibles, la paginación, concurrencia, doble envío o formularios antiguos mediante una nueva ejecución manual. El llamado sin JavaScript permanece sin comprobación manual. Las garantías automatizadas sobre esos aspectos conservan exclusivamente el alcance documentado en 017.

No se afirma una inspección directa actual de datos, secuencias, eventos, comprobantes o migraciones. El estado **Ocupado** y la conservación del mismo folio tras reanudar son resultados observados por el usuario desde la interfaz; no una certificación nueva del estado interno de PostgreSQL.

Esta etapa modifica únicamente documentación. El asistente no modificó código ni datos, no ejecutó pruebas o migraciones y no restauró respaldos anteriores. La recuperación DEMO de 017 es histórica: no se revierte el llamado, las pausas, las reanudaciones ni la preparación de cuentas del entorno manual con un respaldo previo. Antes de un futuro runner deberá preservarse nuevamente el estado vigente.

La entrega conserva su alcance: sin inicio, notas, finalización, denegación, historial, filtros ni selección manual de oficina o ciudadano para llamar. No se introducen acuerdos funcionales nuevos.
