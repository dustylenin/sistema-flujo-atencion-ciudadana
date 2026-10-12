# 008 — Diseño de llamado y reserva del siguiente folio

Fecha de revisión: **11 de octubre de 2026**.

Estado actualizado al **12 de octubre de 2026**: **servicio y modelos verificados, migración aplicada exclusivamente en la base aislada y datos DEMO recuperados**. El diseño revisado se conserva como referencia técnica. La [validación 014](../pruebas/014-validacion-llamado-y-reserva-postgresql.md) registra las ejecuciones posteriores a la preparación descrita abajo.

Código contrastado en la revisión del 11 de octubre: **`df626ce`** (`df626ce981be3739aaa7bb90d75280d8c92e09c0`), con `main` limpio y sincronizado con `origin/main`.

## Revisión de compatibilidad — 12 de octubre de 2026

El diseño sigue siendo compatible con el código actual después de implementar el acceso de la [decisión 009](009-inicio-de-sesion-y-acceso-por-rol.md) y Nueva atención de Recepción de la [decisión 010](010-nueva-atencion-recepcion.md). El núcleo de usuarios, asignaciones, folios y pausas conserva la base contrastada en la revisión anterior. **El llamado y la reserva siguen pendientes de implementación**, junto con sus pruebas y migración; esta revisión no modifica el diseño técnico ni replantea acuerdos funcionales cerrados.

El siguiente orden de trabajo será **servicio y modelos con sus pruebas; revisión y verificación de la migración; después lecturas autorizadas y pantallas de Operador**. Sustituye la planificación anterior que priorizaba acceso y la primera pantalla de Recepción.

**Antes de ejecutar pruebas debe resolverse la conservación de los datos DEMO presentes en la base aislada `test_atencion_catalogos_migraciones`**, utilizada para la revisión manual. No se presupone que esté vacía ni se autoriza su limpieza mediante esta nota. No se implementó código, ejecutaron pruebas o migraciones, ni se conectaron o limpiaron bases durante esta revisión documental.

Se mantienen las decisiones todavía pendientes descritas al final del documento y el formato público del folio pendiente conforme a la decisión 005. Se conserva la distinción entre el rol funcional **`ADMINISTRADOR`** y los flags técnicos **`is_staff` e `is_superuser`**: estos no conceden por sí solos autorización funcional ni sustituyen el rol `OPERADOR` requerido para llamar.

## Preparación de código — 12 de octubre de 2026

Después de la revisión de compatibilidad se prepararon `llamar_siguiente`, las ampliaciones de Folio, EventoFolio y SolicitudOperador y la extracción de clave, búsqueda y comparación de comprobantes en `folios/solicitudes.py`. Pausa/reanudación conservan sus contratos y persistencia específica; `registrar_folio`, las barreras públicas, usuarios, asignaciones y Recepción no se modificaron. Se mantiene la selección por llegada original y UUID, los bloqueos ordenados sin `skip_locked`, el máximo global y la confirmación atómica de reserva, evento y solicitud. Solo se añade LLAMADO a los estados admitidos del modelo; EN_ATENCION permanece fuera de los choices y del CHECK.

La migración completa [0003_llamado_y_reserva](../../folios/migrations/0003_llamado_y_reserva.py) está generada, **sin aplicar**. Se prepararon **51 pruebas nuevas**, incluidas 20 de concurrencia y una de conservación histórica mediante migración; **ninguna fue ejecutada**. Se ajustaron las expectativas de restricciones anteriores. El [registro 013](../pruebas/013-preparacion-llamado-y-reserva.md) detalla respaldo, SQL, plan y comprobaciones de solo lectura; no atribuye pruebas previas a esta entrega.

Antes de editar se confirmó la conexión real `test_atencion_catalogos_migraciones / atencion_test`, 22 migraciones aplicadas y ninguna pendiente, y se obtuvo un respaldo completo privado fuera del repositorio. `pg_restore` pudo listar y leer el archivo, **sin probar una restauración**. Después, el plan muestra únicamente folios.0003 pendiente. No se ejecutó `migrate`, runner, restauración ni limpieza, ni se conectó la base normal. La revisión DEMO y la ejecución posterior de pruebas siguen requiriendo coordinación: disponer del respaldo no demuestra su restauración ni autoriza limpiar datos.

El código preparado requiere el esquema de folios.0003 para ejecutar llamado y los guardados que usan los campos nuevos. Todavía no se habilitan rutas o pantallas de Operador, inicio, finalización ni correcciones administrativas. La revisión técnica del SQL no sustituye su aplicación y verificación real posterior.

## Validación aislada — 12 de octubre de 2026

Tras revisar 0003, SQL y plan, se confirmó 8001 detenido, identidad real `test_atencion_catalogos_migraciones / atencion_test`, 22 migraciones y solo 0003 pendiente. Se verificó la correspondencia del respaldo con los datos y secuencias actuales y se preparó un manifiesto privado y recuperación antes de escribir. Se aplicó 0003 en esa base y se comprobaron restricciones, índices y conservación histórica: **23 migraciones y ninguna pendiente**.

Pasaron **51 pruebas nuevas** (30 funcionales, 20 de concurrencia y una de migración), después **242 pruebas de regresión completa que incluyen esas 51**, y **4 pruebas JavaScript** de Recepción. No fueron necesarias correcciones de código o pruebas; la migración aplicada no se reescribió. `check`, correspondencia modelos/migraciones y formato resultaron correctos.

Los datos DEMO se recuperaron transaccionalmente sobre el esquema de 0003, excluyendo tabla y secuencia de migraciones. Se verificaron conteos/huellas de 17 tablas, próxima asignación de 15 secuencias, integridad referencial y conservación del historial de migraciones. El servidor 8001 sigue detenido. El [registro 014](../pruebas/014-validacion-llamado-y-reserva-postgresql.md) conserva comandos, resultados y dos ajustes del auxiliar temporal de comparación de zonas horarias; no se conectó ni migró la base normal ni se hizo commit/push. Las secciones anteriores documentan la preparación previa, cuando migración, runner y recuperación aún no estaban ejecutados.

## Autoridad y alcance

Los [acuerdos vigentes](../acuerdos-vigentes.md), apartados «Recorrido de atención», «Disponibilidad y folio actual del operador» y «Oficinas, trámites y asignaciones», son la fuente principal. Los [requisitos](../requirements.md), RF-13, RF-14 y RNF-05, y el [flujo](../user-flow.md), «Consultar, llamar e iniciar una atención», recogen estas reglas. Las decisiones [004](004-cola-y-responsabilidad-de-folios.md) y [006](006-disponibilidad-y-folio-actual-del-operador.md) establecen la cola conjunta, responsabilidad desde Llamado, pausa y límite global.

La [decisión 005](005-registro-inicial-de-folios.md) documenta el registro inicial existente. La [decisión 007](007-diseno-pausas-y-disponibilidad.md) documenta pausa, reanudación, disponibilidad derivada y comprobantes implementados; su migración está aplicada localmente, conforme al [registro 010](../pruebas/010-migracion-pausas-disponibilidad-local.md). Algunos avisos de los documentos funcionales conservan el estado de implementación anterior; no sustituyen el código ni las evidencias posteriores.

Esta propuesta concreta únicamente la segunda entrega de **llamado y reserva**, integrada con pausa y el máximo global de un folio actual. Su documentación no implementa código, genera o ejecuta migraciones, conecta bases ni ejecuta pruebas. Conserva las evidencias anteriores; ninguna prueba anterior se atribuye a este diseño todavía sin implementar.

## Reglas funcionales aprobadas y decisiones técnicas

Reglas aprobadas que se respetan:

- Cola combinada de folios En espera de todas las oficinas con asignación activa del operador.
- Selección por llegada original más antigua, sin elegir oficina ni folio desde el servicio.
- Pendientes de oficinas y trámites desactivados siguen atendibles; la desactivación impide nuevos registros, no elimina esos pendientes.
- Actor autenticado, cuenta activa y rol funcional OPERADOR vigentes, comprobados separadamente de `is_staff` e `is_superuser`.
- En pausa impide nuevos llamados, incluso sin folio actual.
- Máximo un folio en Llamado o En atención por operador, contando todas sus oficinas.
- En espera → Llamado, con reserva y responsabilidad del operador que llamó; iniciar atención es un momento posterior.
- Pausar conserva responsabilidad, estado y folio; reanudar deriva Libre/Ocupado desde el folio actual.
- Una oficina puede tener varios operadores y un operador varias oficinas. No se introduce el límite de un operador por oficina.

Son **decisiones técnicas propuestas**, no nuevos acuerdos funcionales: nombres y tipos de contratos, comprobantes para resultados sin transición, ampliación de campos y CHECK, índices, bloqueo de todas las oficinas de la cola, desempate por UUID y primitivas de persistencia. Reserva, evento y comprobante conjuntos y reintentos históricos continúan el diseño técnico de la decisión 007.

## Contrato y resultados

```python
llamar_siguiente(
    *,
    actor: Usuario,
    solicitud_id: UUID | str,
) -> ResultadoLlamado
```

No acepta oficina, folio, operador destino, fecha ni estado. El actor procede del contexto autenticado del servidor. La cola se obtiene de sus asignaciones activas.

`ResultadoLlamado` será una dataclass inmutable:

| Campo | Tipo propuesto |
| --- | --- |
| `solicitud_id` | `UUID` |
| `operacion` | `str`, siempre `LLAMAR` |
| `resultado` | Enumeración de resultados |
| `folio_id` | **`UUID \| None`** |
| `evento_id` | **`int \| None`** |
| `confirmada_en` | `datetime` con zona horaria |
| `repetida` | `bool` |

**`folio_id` y `evento_id` son opcionales: solo `LLAMADO` devuelve ambos.** Todos los demás resultados devuelven ambos NULL; no devuelven el folio que ya tenga el operador como si fuera una reserva nueva.

Para una clave nueva, se propone este orden de evaluación:

| Resultado | Condición | Escrituras |
| --- | --- | --- |
| `EN_PAUSA` | Existe una pausa abierta, con o sin folio actual. | Solo comprobante. |
| `OCUPADO` | Sin pausa, pero con folio actual global. | Solo comprobante. |
| `SIN_ASIGNACIONES` | Libre, sin asignaciones activas. | Solo comprobante. |
| `SIN_PENDIENTES` | Libre, con asignaciones activas, sin folios En espera en su cola. | Solo comprobante. |
| `LLAMADO` | Se selecciona y reserva el siguiente folio. | Actualización de Folio, evento y comprobante. |

Los resultados sin llamado no generan eventos funcionales ni almacenan disponibilidad. Confirmarlos mediante comprobante es una propuesta técnica: repetir una petición inicialmente bloqueada no debe ejecutar otro llamado después de reanudar, obtener una asignación o recibir nuevos registros. Esa intención nueva requiere otra clave. El resultado describe la petición histórica, no la disponibilidad actual.

La autorización se comprueba siempre, incluso al repetir: actor autenticado, persistido en el mismo alias de escritura, cuenta activa y rol OPERADOR releído bajo bloqueo. Los flags técnicos no sustituyen la autorización. Un actor inválido produce `PermissionDenied`; una clave UUID inválida o incompatible produce `ValidationError`. Estos errores no dejan comprobante. Un fallo de persistencia revierte la operación.

## Integración con SolicitudOperador

Se conserva la tabla y su unicidad **`(operador, solicitud_id)`**, compartida entre PAUSAR, REANUDAR y LLAMAR. No se añade un registro paralelo de solicitudes.

| Cambio propuesto | Definición |
| --- | --- |
| `operacion` | Añadir `LLAMAR`; `max_length=8` sigue siendo suficiente. |
| `resultado` | Añadir los cinco resultados de llamado; caben en `max_length=16`. |
| `pausa_resultado` | Pasar a `null=True, blank=True`, conservando FK `PROTECT`. |
| `folio_resultado` | Nueva `FoliosForeignKey` a Folio, referencia UUID, nullable, `PROTECT`. |
| `evento_folio_resultado` | Nueva `FoliosForeignKey` a EventoFolio, referencia bigint, nullable, `PROTECT`. |

Se mantienen `evento_resultado` como referencia a **EventoDisponibilidad**, los argumentos de pausa/reanudación y `confirmada_en`. No se cambia el significado de esos campos para almacenar un evento de otra clase. Las relaciones nuevas tendrán nombres inversos distintos y las barreras existentes.

El CHECK ampliado admitirá solo estas ramas:

| Operación | Coherencia exigida |
| --- | --- |
| `PAUSAR` | Motivo no NULL y con contenido; objetivo NULL; pausa resultado **no NULL**; resultados actuales; evento de disponibilidad no NULL para PAUSADA y NULL para YA_EN_PAUSA; ambos campos nuevos NULL. |
| `REANUDAR` | Motivo NULL; objetivo y pausa resultado **no NULL**, e iguales; resultados actuales; evento de disponibilidad no NULL para REANUDADA y NULL para YA_REANUDADA; ambos campos nuevos NULL. |
| `LLAMAR` | Motivo, objetivo, pausa resultado y evento de disponibilidad NULL. Para LLAMADO, folio y evento de folio no NULL; para los otros cuatro resultados, ambos NULL. |

Después de hacer nullable `pausa_resultado`, su presencia en las ramas de pausa se exigirá explícitamente. No se confiará en una comparación con NULL que permita aceptar el CHECK por un resultado SQL desconocido.

Los comprobantes anteriores conservan todos sus valores, referencias y resultados. Los campos nuevos quedan NULL y sus combinaciones continúan siendo válidas. No se persisten comprobantes intermedios ni JSON arbitrario; cada inserción contiene el resultado definitivo y queda inmutable.

### Solicitudes repetidas e incompatibles

1. Autorizar y bloquear Usuario.
2. Validar la clave y los argumentos correspondientes.
3. Buscar el comprobante por operador y clave.
4. Comparar operación y argumentos.
5. Si coinciden, devolver el resultado original con `repetida=True`, **antes de consultar pausa, folio actual o asignaciones**.
6. Si difieren, rechazar sin transición ni escrituras.
7. Si no existe, evaluar el estado presente.

LLAMAR no tiene argumentos funcionales adicionales. Reutilizar una clave de PAUSAR o REANUDAR es incompatible. El mismo UUID utilizado por otro operador pertenece a un ámbito distinto. Se conserva la comparación exacta del motivo validado y de la pausa objetivo en las operaciones existentes.

Actualmente `_repetida` en `services_disponibilidad.py` devuelve `ResultadoOperacionPausa`. Se propone extraer solamente búsqueda y comparación común a `folios/solicitudes.py`. Cada servicio mantiene su constructor de resultado y su inserción privada específica; no se añade un guardado genérico.

Un comprobante LLAMADO seguirá devolviendo los identificadores y fecha originales cuando el operador esté ocupado o haya pausado, sin otra reserva ni otro evento. Se obtiene la disponibilidad presente mediante `consultar_disponibilidad`; el comprobante no afirma que siga siendo el estado actual. Los reintentos no omiten la autorización vigente.

## Folio y máximo global

Folio añadirá exclusivamente `LLAMADO` a sus estados admitidos. Se sustituirá el CHECK inicial por:

```text
(estado = EN_ESPERA AND operador_responsable IS NULL)
OR
(estado = LLAMADO AND operador_responsable IS NOT NULL)
```

La reserva establece conjuntamente `estado=LLAMADO` y `operador_responsable=actor`. No necesita otra tabla ni un indicador de reserva. Se conservan UUID, nombre, correo, teléfono, oficina, trámite, llegada original y responsable del registro. No se añade fecha de inicio de atención.

La protección global propuesta en PostgreSQL es una unicidad condicional; este SQL expresa el diseño, **no una migración generada o ejecutada**:

```sql
CREATE UNIQUE INDEX folios_folio_actual_unico
ON folios_folio (operador_responsable_id)
WHERE estado IN ('LLAMADO', 'EN_ATENCION');
```

Cuenta todas las oficinas del operador, sin condiciones de actividad de oficina, asignación o cuenta. El CHECK exige responsable para LLAMADO. La comprobación previa del servicio utiliza el folio actual global, como `services_disponibilidad.py`, sin ocultarlo por oficina o asignación inactiva.

Incluir el literal EN_ATENCION en el índice **no habilita ese estado**: los choices y el CHECK lo seguirán rechazando en esta entrega. Cuando se implemente inicio, se ampliará el CHECK para exigir responsable también en En atención; el índice ya cubrirá ambos estados.

## EventoFolio y evidencia del llamado

| Cambio propuesto | Definición |
| --- | --- |
| `operacion` | Añadir `LLAMADO`; conservar `CREACION` y `max_length=12`. |
| `datos_iniciales` | Nullable; obligatorio para CREACION y NULL para LLAMADO. |
| `operador_responsable` | Nueva FK nullable a Usuario, `PROTECT`; responsable histórico al llamar. |
| `asignacion_autorizante` | Nueva FK nullable a AsignacionOperadorOficina, `PROTECT`. |

Las nuevas referencias utilizarán `FoliosForeignKey`, nombres inversos distintos y las protecciones actuales. Fecha, actor y transición permanecen en los campos existentes.

El CHECK tendrá dos ramas:

- **CREACION:** anterior NULL, nuevo EN_ESPERA, `datos_iniciales` no NULL y nuevas referencias NULL.
- **LLAMADO:** anterior explícitamente no NULL e igual a EN_ESPERA, nuevo LLAMADO, `datos_iniciales` NULL y ambas referencias no NULL; además, `actor_id = operador_responsable_id`.

Los eventos CREACION anteriores y sus JSON se conservan sin cambios. Permanece su unicidad condicional. No se propone unicidad permanente de LLAMADO por folio, porque podría interferir con una futura restauración y otro llamado legítimo. En esta entrega, bloqueo y transición desde En espera impiden duplicar el llamado.

El evento conserva actor, fecha del servidor, transición, responsable y asignación activa que autorizó la operación. Para LLAMADO se utilizará un mismo instante del servidor en la fecha del evento y `confirmada_en` del comprobante. Bajo bloqueo, el servicio comprobará:

```text
asignación.operador_id = actor.id = responsable.id
asignación.oficina_id = folio.oficina_id
asignación.activo = True
```

La oficina histórica se obtiene de esa asignación: sus referencias no cambian por los servicios actuales, que permiten creación y reactivación. Su actividad futura no invalida la evidencia. La correspondencia entre evento, folio y asignación se garantiza en el servicio, no mediante CHECK entre tablas.

## Transacción, bloqueos y selección

Una única `transaction.atomic()` y el alias de escritura de Folio cubrirán autorización, selección, reserva, evento y comprobante. No se utilizará la consulta pública de disponibilidad como autorización: puede elegir un alias de lectura y no sustituye las comprobaciones dentro de la reserva.

El orden compatible con registro, asignaciones y la decisión 007 será:

```text
Usuario → oficinas por PK → asignaciones por PK
→ pausas si requieren bloqueo → folio → escrituras
```

Procedimiento para una solicitud nueva:

1. Bloquear y releer Usuario; comprobar cuenta activa y rol funcional OPERADOR.
2. Validar la clave y resolver primero un comprobante repetido o incompatible.
3. Consultar pausa abierta y folio actual global. Usuario impide cambios concurrentes mediante pausa, reanudación y llamado; los resultados EN_PAUSA u OCUPADO confirman solo comprobante.
4. Si puede continuar, leer sus asignaciones activas. Usuario mantiene estable el conjunto frente a creación/reactivación; retirada continúa bloqueada.
5. Bloquear **todas las oficinas del conjunto**, una a una por PK ascendente, sin exigir actividad.
6. Bloquear y revalidar las asignaciones activas por PK. No adquirir cuentas después de oficinas.
7. Seleccionar Folio En espera de esas oficinas, ordenado por **`llegada_original, id`**, con `select_for_update(of=("self",))`.
8. Revalidar estado, responsable vacío y pertenencia a una asignación autorizante bloqueada.
9. Reservar el folio, insertar evento e insertar comprobante definitivo. Si no hay asignaciones o pendientes, insertar únicamente el comprobante correspondiente.

No se filtra `Oficina.activo` ni `Tramite.activo`. El llamado no necesita bloquear Trámite, pues su actividad no condiciona la atención del pendiente. No se adquieren bloqueos de filas relacionadas accidentalmente mediante joins.

### Concurrencia, rollback y desempate

Bloquear todas las oficinas es la propuesta técnica para conservar la selección por llegada. Dos operadores con colas solapadas esperan en una oficina compartida y seleccionan después de adquirir el conjunto completo. Colas disjuntas pueden continuar en paralelo. El coste es reducir la concurrencia en las oficinas compartidas; no se promete un rendimiento todavía sin medir.

La selección se hace en una consulta nueva después de las esperas, bajo READ COMMITTED, utilizado por la configuración actual:

- Si el primer operador confirma, el segundo no encuentra su folio En espera y selecciona el siguiente.
- Si el primero revierte, el segundo encuentra y selecciona el folio más antiguo liberado.
- Si Recepción registra primero y mantiene bloqueada la oficina, el llamado espera y después incluye el registro confirmado.
- Si el llamado bloquea primero, el registro espera y pertenece a una selección posterior.

No se utiliza `skip_locked`, porque podría saltar un pendiente más antiguo cuya reserva termine revertida. El desempate por UUID es **técnico y determinista**; no constituye numeración, prioridad funcional ni afirmación sobre cuál se registró primero cuando las llegadas son iguales.

Usuario coordina también las operaciones del mismo operador:

- Misma clave: una operación y un resultado repetido.
- Claves distintas: un llamado; la segunda encuentra OCUPADO.
- Pausa antes del llamado: EN_PAUSA.
- Llamado antes de pausa: se conserva el folio real LLAMADO como contexto de la pausa.
- Reanudación antes de un llamado nuevo: puede continuar si no tiene folio actual.
- Una petición confirmada como EN_PAUSA conserva ese resultado histórico al repetirse después de reanudar.

Un fallo en reserva, evento o comprobante revierte el conjunto, también ante rollback exterior. No se difieren eventos a `on_commit` ni a tareas. `confirmada_en` conserva su significado: la confirmación definitiva ocurre al confirmar la transacción exterior. Un error de integridad no se convierte en éxito ni deja un comprobante parcial.

## Persistencia específica y barreras del ORM

Primitivas privadas propuestas:

- `_reservar_folio`: recibe folio bloqueado y operador validado; actualiza exclusivamente `estado` y `operador_responsable`, con actualización forzada y `update_fields` cerrado.
- `_crear_evento_llamado`: construye e inserta exclusivamente la evidencia de LLAMADO.
- `_confirmar_solicitud_llamado`: inserta exclusivamente un comprobante LLAMAR definitivo y las referencias correspondientes al resultado.

No reciben diccionarios arbitrarios de campos ni permiten cambiar llegada, datos originales, eventos existentes o comprobantes. Las inserciones fuerzan INSERT. La persistencia de pausa/reanudación mantiene sus operaciones específicas.

Se reutilizan `folios/managers.py`, el modelo base y `FoliosForeignKey`. Continúan rechazados escritura pública, borrado, métodos masivos, variantes asíncronas, managers por defecto/base/inversos y `add`, `set`, `remove`, `clear`, incluida la selección repetida del manager relacionado.

SQL directo, deserializadores y APIs internas conservan los límites documentados: las restricciones no garantizan por sí solas autorización, inmutabilidad ni existencia conjunta de evento y comprobante. No se añaden disparadores ni una auditoría global completa.

Las proyecciones por rol de disponibilidad permanecen iguales: Recepción recibe identidad y disponibilidad; el operador recibe su referencia mínima de folio actual y pausa. El comprobante de llamado responde únicamente al propio operador autorizado. No se amplían permisos de consulta.

## Migración y archivos previstos

Se prevé una nueva **`folios.0003`**, dependiente de `folios.0002`, para campos y choices, sustitución de CHECK de Folio, EventoFolio y SolicitudOperador, unicidad global, referencias protegidas y un índice parcial de cola por `(oficina_id, llegada_original, id)` para EN_ESPERA. El SQL se revisará antes de aplicarlo en pruebas.

No se reescriben migraciones anteriores ni datos históricos. Los registros existentes cumplen las ramas de CREACION y pausa/reanudación; las columnas nuevas quedan NULL.

| Archivo previsto | Alcance |
| --- | --- |
| `folios/models.py` | Estados, campos, restricciones e índice. |
| `folios/services_llamado.py` | Contrato, resultados, selección, bloqueos y persistencia específica. |
| `folios/solicitudes.py` | Búsqueda y comparación común de comprobantes. |
| `folios/services_disponibilidad.py` | Integrar la búsqueda conservando contratos y escrituras actuales. |
| `folios/migrations/0003_…py` | Migración nueva, todavía no generada. |
| `folios/test_llamado.py` | Funcionalidad, restricciones y rollback. |
| `folios/test_llamado_concurrencia.py` | Concurrencia real. |
| `folios/tests.py` | Ajustar expectativas del CHECK anterior y conservar cobertura de registro y CREACION. |
| `folios/test_disponibilidad.py` y `folios/test_disponibilidad_concurrencia.py` | Regresiones de comprobantes y casos reales desde LLAMADO. |

`folios/services.py` conserva el comportamiento de registro. No se prevén cambios funcionales en usuarios u oficinas, ni en las barreras existentes salvo que una regresión demuestre un defecto.

## Pruebas necesarias, todavía pendientes

La validación futura utilizará exclusivamente `config.settings_test_migrations`, con conexión real **`test_atencion_catalogos_migraciones / atencion_test`** verificada antes de escribir y las barreras de aislamiento existentes. No se ejecutarán pruebas sobre la base normal.

Cobertura necesaria:

- Cola combinada; pendientes fuera de asignaciones excluidos; oficinas y trámites desactivados incluidos; llegadas iguales y desempate.
- Autorización vigente, instancias antiguas, UUID inválido e independencia de flags técnicos.
- Llamado real mediante el servicio, reserva y evidencia correctas, disponibilidad real OCUPADO y máximo global entre oficinas.
- Pausa real desde LLAMADO, contexto de folio/oficina e historial; conservación íntegra del folio; reanudación que deriva OCUPADO.
- Consulta global que conserva el folio con oficina desactivada. El caso de asignación inactiva utilizará un estado histórico controlado en pruebas, sin habilitar retirada pública.
- Reintentos después de pausa, reanudación, registro o cambios de asignaciones; resultados sin transición repetidos; incompatibilidad entre LLAMAR, PAUSAR y REANUDAR.
- Conservación de comprobantes anteriores, eventos CREACION y datos iniciales al migrar.
- Rechazos reales de PostgreSQL por CHECK, NULL, unicidad global y referencias inválidas; PROTECT y barreras públicas completas, incluidas variantes asíncronas y selección repetida del manager inverso.
- Fallo de cada escritura y rollback exterior, conservando En espera y sin eventos o comprobantes parciales.
- Operadores distintos compitiendo por uno o varios folios, colas solapadas/disjuntas, confirmación y rollback del primero.
- Mismo operador con claves iguales/distintas y ambos órdenes frente a pausa, reanudación, desactivación de cuenta, registro y creación/reactivación de asignaciones; conservación de los bloqueos provisionales.

La concurrencia usará `TransactionTestCase`, conexiones y PIDs distintos, sincronización explícita y espera real comprobada mediante `pg_blocking_pids`; el tiempo de espera por sí solo no será evidencia. Se verificará el orden de adquisición de varias oficinas.

Después se ejecutarán pruebas nuevas, regresiones afectadas y suite completa, porque se amplían modelos y comprobantes compartidos. También check, correspondencia modelos/migraciones, formato e inspección del esquema. **Nada de ello se ejecutó en esta revisión documental.**

## Pendientes y siguiente orden de trabajo

No se identifica una duda funcional que bloquee llamado y reserva con este alcance. Los contratos, comprobantes sin transición y serialización por oficinas se registran como diseño técnico revisado, sin presentarlos como nuevos acuerdos funcionales.

Permanecen pendientes permisos ampliados, presentación de pausas sin oficina y correcciones administrativas que pudieran generar un segundo folio actual. No se define Inactivo ni se resuelven esas correcciones. Retirada de asignaciones y salida de OPERADOR conservan sus bloqueos provisionales.

En atención y notas conservan su verificación pendiente. Inicio, cierre, pantallas y correcciones administrativas quedan fuera de esta entrega. El llamado permitirá reservar y pausar el folio, pero no completar su atención ni liberar al operador mediante un cierre funcional.

El orden vigente es el registrado en la revisión de compatibilidad del **12 de octubre de 2026**: **servicio y modelos con pruebas; revisión y verificación de migración; después lecturas autorizadas y pantallas de Operador**. Servicio, modelos, pruebas y migración ya están verificados en la base aislada conforme al registro 014, con datos DEMO recuperados sobre el esquema nuevo. El cierre guarda esta entrega sin iniciar otra etapa; las lecturas adicionales y pantallas de Operador son el punto pendiente para retomar. Antes de otra ejecución del runner debe repetirse la conservación: DEMO vuelve a estar presente. La recuperación selectiva realizada no acredita una restauración completa del esquema antiguo.
