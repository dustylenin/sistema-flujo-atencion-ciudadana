# 005 — Registro inicial de folios

Fecha de revisión: **10 de octubre de 2026**.

Estado: **registro inicial implementado y revisado en PostgreSQL de pruebas; migración aplicada y verificada en PostgreSQL local**.

## Autoridad y alcance

Los [acuerdos vigentes](../acuerdos-vigentes.md), apartados «Recepción y registro» y «Oficinas, trámites y asignaciones», son la fuente principal. Los requisitos RF-08 a RF-12 de [requisitos](../requirements.md) describen los datos y el registro inicial. Esta decisión concreta únicamente registro por Recepción, estado **En espera** y evento de creación; no cambia acuerdos funcionales.

Se reutilizan las referencias y conservación de registros de la [decisión 002](002-oficinas-tramites-y-asignaciones.md), y las transacciones, bloqueos y barreras de escritura de la [decisión 003](003-servicios-de-asignacion-y-actividad.md). Conforme a la [decisión 004](004-cola-y-responsabilidad-de-folios.md), registrar no asigna operador: la responsabilidad comienza al llamar, y el inicio de atención es un momento posterior.

Los tipos, nombres de campos y representación interna siguientes son decisiones técnicas implementadas en `folios`. El [registro 007 de pruebas](../pruebas/007-registro-inicial-folios-postgresql.md) documenta la suite completa de **102 pruebas, incluidas 28 de folios, antes de la corrección del descriptor inverso**, y las **3 pruebas afectadas satisfactorias después**. La regresión falló antes de corregir y pasó después; no se repitió la suite completa ni se suman ambos conteos. En pruebas quedaron 21 migraciones aplicadas y sin pendientes, con 2 tablas nuevas, 18 columnas, 11 restricciones y 9 índices, sin datos residuales. Durante esa etapa de pruebas, `folios.0001_initial` todavía estaba pendiente en `atencion_ciudadana`; esa base no se conectó entonces. Las evidencias anteriores se conservan y no se atribuyen por sí solas a los folios.

El **10 de octubre de 2026**, con Git limpio en el commit de código `2d690da` y conexión real `atencion_ciudadana / atencion_app` mediante `config.settings`, se aplicó `folios.0001_initial` tras comprobar 20 migraciones aplicadas y esa única pendiente. El SQL revisado fue coherente. Después quedaron **21 migraciones aplicadas y ninguna pendiente**, con `check` satisfactorio; la comprobación previa de modelos/migraciones no detectó diferencias. La inspección de lectura confirmó 2 tablas nuevas, 18 columnas, 11 restricciones y 9 índices, con cero filas en ambas tablas. La inspección inicial falló por comparar literalmente `varchar` y `character varying`; normalizados esos alias equivalentes, pasó sin diferencias de esquema. No se ejecutaron pruebas en la base normal, no se crearon datos ni se cambiaron permisos. El [registro 008 de aplicación local](../pruebas/008-migracion-folios-local.md) conserva comandos y resultados de esta etapa distinta, sin sustituir la evidencia de pruebas.

## Folio

Modelo implementado en `folios/models.py`:

| Campo | Tipo y obligatoriedad | Valor inicial y procedencia |
| --- | --- | --- |
| `id` | `UUIDField`, clave primaria, `editable=False` | UUID generado en el servidor. Identificador técnico interno. |
| `nombre_completo` | `TextField`, obligatorio, no NULL | Nombre capturado; debe contener algún carácter distinto de espacios. |
| `correo` | `EmailField(max_length=254, blank=True)`, no NULL, valor predeterminado `""` | Correo válido si se proporciona; cadena vacía si se omite. |
| `telefono` | `TextField(blank=True)`, no NULL, valor predeterminado `""` | Valor capturado o cadena vacía, sin imponer un formato no acordado. |
| `oficina` | FK obligatoria a `oficinas.Oficina`, `on_delete=PROTECT` | Oficina seleccionada por Recepción. |
| `tramite` | FK obligatoria a `tramites.Tramite`, `on_delete=PROTECT` | Trámite seleccionado de esa oficina. |
| `registrado_por` | FK obligatoria a `AUTH_USER_MODEL`, `on_delete=PROTECT` | Actor autorizado, releído de la base. |
| `llegada_original` | `DateTimeField`, obligatorio, `editable=False` | Fecha y hora del servidor con zona horaria. |
| `estado` | `CharField(max_length=12)`, obligatorio, valor predeterminado `EN_ESPERA` | `EN_ESPERA`, mostrado como «En espera». |
| `operador_responsable` | FK a `AUTH_USER_MODEL`, `on_delete=PROTECT`, `null=True`, `blank=True`, valor predeterminado `None` | NULL al registrar. |

Las dos relaciones de usuario tienen nombres inversos distintos. No se crea un registro maestro de ciudadano ni se reutilizan sus datos automáticamente. Nombre, correo y teléfono no son únicos: cada registro crea una atención independiente.

Restricciones implementadas:

- Clave primaria UUID, referencias existentes y NOT NULL en los campos obligatorios.
- `CHECK` de nombre con contenido, además de su validación en el servicio.
- `CHECK` que exija conjuntamente `estado='EN_ESPERA'` y `operador_responsable IS NULL`.

**La restricción de estado y operador corresponde exclusivamente a esta entrega.** Se ampliará mediante nuevas migraciones para incorporar el llamado aprobado en la decisión 004, sin reescribir migraciones anteriores. No se incorporan ahora otros estados, fechas de inicio o cierre ni notas.

El UUID no define el formato visible del folio, consecutivos ni reinicios. La coherencia oficina/trámite y las condiciones de actividad se comprueban entre filas en el servicio; no se atribuyen a un `CHECK` ordinario.

## EventoFolio

Modelo implementado en `folios/models.py`, como registro durable de la creación:

| Campo | Tipo y obligatoriedad | Valor en CREACION |
| --- | --- | --- |
| `id` | `BigAutoField`, clave primaria técnica | Generado por la base; no es la numeración visible del folio. |
| `folio` | FK obligatoria a `Folio`, `on_delete=PROTECT`, `related_name='eventos'` | Folio creado. |
| `actor` | FK obligatoria a `AUTH_USER_MODEL`, `on_delete=PROTECT` | La misma cuenta que `registrado_por`. |
| `fecha` | `DateTimeField`, obligatorio, `editable=False` | El mismo instante usado para la llegada original. |
| `operacion` | `CharField(max_length=12)`, obligatorio | `CREACION`, única operación admitida en esta entrega. |
| `estado_anterior` | `CharField(max_length=12, null=True)` | NULL: el folio todavía no existía. |
| `estado_nuevo` | `CharField(max_length=12)`, obligatorio | `EN_ESPERA`. |
| `datos_iniciales` | `JSONField`, obligatorio, no NULL | Copia de nombre, correo, teléfono, IDs de oficina y trámite y llegada original. |

El servidor construye y valida la estructura de `datos_iniciales`; no recibe un JSON arbitrario del cliente. La llegada se representa en formato ISO con zona horaria. Esta copia conserva evidencia inicial para futuras correcciones y traslados, sin implementar esas acciones ahora.

Un `CHECK` exige conjuntamente operación `CREACION`, estado anterior `IS NULL` y estado nuevo `EN_ESPERA`. Operación y estado nuevo son NOT NULL para evitar aceptación accidental de NULL por la lógica de SQL. Una `UniqueConstraint` condicional por folio para `CREACION` impide dos eventos de creación, permitiendo incorporar otros eventos posteriormente.

Los índices necesarios para esta entrega son los de claves primarias y foráneas y el índice de la unicidad condicional. Los índices de selección de cola se justificarán en la entrega del llamado. No se permite editar ni borrar públicamente eventos o folios. **EventoFolio no constituye la auditoría completa del sistema.**

## Servicio registrar_folio

Firma del servicio implementado en `folios/services.py`:

```python
registrar_folio(
    *,
    actor: Usuario,
    nombre_completo: str,
    oficina_id: int,
    tramite_id: int,
    correo: str = "",
    telefono: str = "",
) -> ResultadoRegistroFolio
```

El resultado es inmutable y contiene `folio_id` y `evento_id`, devueltos solo después de guardar ambos. No se realiza deduplicación por datos del ciudadano.

El actor procede del contexto autenticado del servidor y debe ser una cuenta persistida de la misma base. Dentro de la transacción se bloquea y relee su fila: debe existir, tener rol `RECEPCION` y estar activa. No se confía en el rol o actividad de una instancia antigua. `is_staff` e `is_superuser` no conceden autorización funcional.

Se valida nombre con contenido y correo cuando se proporcione; la ausencia de correo o teléfono no impide registrar. Se comprueba bajo bloqueo que oficina y trámite existen, ambos están activos y `tramite.oficina_id == oficina.id`. No se exige una asignación de operador para registrar.

UUID, llegada original, responsable del registro, estado y operador vacío son establecidos por el servidor, sin argumentos públicos que permitan sustituirlos. Se usa un único instante del servidor para llegada y fecha del evento. Una denegación produce `PermissionDenied`; datos inválidos o referencias incompatibles producen `ValidationError`. Ningún rechazo deja registros.

## Transacción y orden de bloqueos

Una sola `transaction.atomic()` y el mismo alias de escritura cubren autorización, validaciones e inserciones. El orden implementado es:

1. Cuenta de Recepción.
2. Oficina.
3. Trámite.
4. Inserción del folio.
5. Inserción del evento.

Los registros existentes se bloquean mediante `select_for_update()` y sus condiciones se comprueban después de adquirir el bloqueo. Este orden mantiene cuentas antes de oficina, como los servicios de asignaciones; el registro inicial no necesita bloquear asignaciones. Las operaciones futuras que involucren más entidades deberán compartir un protocolo completo antes de habilitarse.

Los bloqueos serializan el registro respecto de cambios concurrentes de rol o actividad de la cuenta y de actividad de oficina o trámite. El fallo del evento revierte también el folio; el fallo del folio impide insertar el evento. Una transacción exterior puede revertir ambos. El evento no se difiere a `on_commit` ni a una tarea posterior.

## Barreras de escritura y límites

Los modelos rechazan `save`, `create`, `update`, `get_or_create`, `update_or_create`, `bulk_create`, `bulk_update` y borrado individual o por queryset. Se protegen sus variantes asíncronas, managers por defecto, base e inversos y métodos relacionados como `add`, `set`, `remove` o `clear`. Las consultas usan vías de lectura.

La revisión detectó que Django 5.2.17 reconstruye el manager inverso al seleccionar `relacion(manager="objects")`, perdiendo las prohibiciones personalizadas de operaciones relacionadas. Las escrituras efectivas seguían rechazadas por otras capas, pero algunas llamadas sin filas afectadas se aceptaban. El descriptor corregido conserva las barreras también al seleccionar nuevamente el manager, con regresión de lecturas, selección repetida, `db_manager` y variantes asíncronas.

La persistencia privada es específica para crear el folio y su evento dentro del servicio autorizado. Ambos guardados fuerzan inserción, evitando sobrescribir registros existentes. No hay parámetros públicos de omisión ni contextos generales que permitan escrituras arbitrarias. El registro y los eventos se conservan, sin borrado funcional.

Estas barreras cubren las vías públicas admitidas del ORM. SQL directo, deserializadores y APIs internas pueden eludirlas. Las restricciones de base garantizan referencias, unicidad y estados permitidos, pero no autorización, coherencia entre tablas ni que toda inserción de folio tenga evento. La unicidad garantiza como máximo un evento CREACION; el servicio y su transacción garantizan la pareja de registros al registrar.

## Pruebas y archivos implementados

- Registro válido, opcionales ausentes, nombre vacío o compuesto solo por espacios y correo inválido.
- Autorización con estado actualizado en la base, incluyendo instancias antiguas, cuenta inactiva, rol incorrecto e independencia de `is_staff`/`is_superuser`.
- Oficina o trámite inexistentes, inactivos o incompatibles.
- Estado En espera, operador vacío, valores establecidos por el servidor, copia de datos y correspondencia entre folio y evento.
- Restricciones y referencias protegidas, especialmente combinaciones de NULL y creación duplicada.
- Rollback conjunto ante fallo de inserción del evento y ausencia de evento si falla el folio.
- Rechazo de escritura y borrado por las vías síncronas, asíncronas y relacionadas previstas.
- Concurrencia real frente a cambios de rol o desactivación de cuenta, oficina y trámite: conexiones independientes, sincronización explícita y comprobación de espera mediante `pg_blocking_pids`, siguiendo las pruebas existentes.

La implementación añade `folios/__init__.py`, `apps.py`, `models.py`, `managers.py`, `services.py`, `tests.py`, `migrations/__init__.py` y `migrations/0001_initial.py`, y registra la aplicación en `config/settings.py`. No modifica modelos o servicios existentes ni reescribe migraciones anteriores.

Las pruebas ejecutadas usaron exclusivamente `config.settings_test_migrations`, conservaron las barreras de aislamiento existentes y ampliaron la suite con `folios`. La suite anterior comprobó concurrencia real en ambos órdenes entre registro y desactivación, con conexiones independientes y espera de bloqueo verificada. Después de corregir el descriptor se ejecutaron únicamente las tres pruebas afectadas; no se repitieron la suite completa ni las pruebas de concurrencia. `check`, correspondencia modelos/migraciones y formato fueron satisfactorios. Los comandos y límites están en el registro 007; este documento no supone una ejecución adicional.

## Pendientes

No se identificaron decisiones funcionales pendientes que impidan esta primera entrega. El identificador técnico interno permite posponer el formato visible sin inventarlo.

Quedan pendientes llamado y reserva, inicio, cierre, notas, traslados, pausas, correcciones, demás acciones, pantallas, formato visible y auditoría global. La responsabilidad desde Llamado está aprobada en la decisión 004, pero no se implementa en este alcance. No se agregan prioridades, límites de atención simultánea, numeración ni reinicios.

La existencia de folios solo En espera y sin operador no completa las reglas definitivas de retirada de asignaciones ni salida de `OPERADOR`. Ambos bloqueos provisionales de las decisiones 002 y 003 se mantienen hasta implementar y verificar las comprobaciones completas de folios asignados sin finalizar.
