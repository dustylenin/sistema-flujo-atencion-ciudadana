# 007 — Diseño de pausas, reanudación y disponibilidad

Fecha: **11 de octubre de 2026**.

Estado: **primera entrega implementada y revisada en PostgreSQL de pruebas; aplicación local de `folios.0002` pendiente**.

El diseño revisado se conserva como referencia de los contratos y propuestas técnicas. La [evidencia de implementación y pruebas](../pruebas/009-pausas-disponibilidad-postgresql.md) registra la validación posterior del 11 de octubre de 2026 y sus límites, sin atribuirle las evidencias de etapas anteriores.

## Autoridad y alcance

Los [acuerdos vigentes](../acuerdos-vigentes.md) son la fuente principal. La [decisión 006](006-disponibilidad-y-folio-actual-del-operador.md) define disponibilidad y el máximo de un folio actual por operador entre todas sus oficinas. Este documento concreta el diseño técnico revisado de la primera entrega: persistencia de pausa, reanudación y consulta de disponibilidad. Distingue reglas expresas de propuestas técnicas y permisos pendientes; no agrega acuerdos funcionales.

Se conservan los servicios y bloqueos de la [decisión 003](003-servicios-de-asignacion-y-actividad.md), la responsabilidad desde Llamado de la [decisión 004](004-cola-y-responsabilidad-de-folios.md) y el registro inicial implementado de la [decisión 005](005-registro-inicial-de-folios.md).

**Esta primera entrega no cambia Folio ni EventoFolio**, sus restricciones, estados o eventos CREACION. No implementa llamado, inicio de atención, notas, cierre, correcciones administrativas ni pantallas. La revisión documental inicial no implementó código ni ejecutó pruebas; la implementación y validación posteriores se registran ahora por separado. Las evidencias anteriores de usuarios, asignaciones y registro inicial no verifican este diseño.

## Respaldo funcional y consultas por rol

| Tema | Respaldo expreso: archivo y apartado |
| --- | --- |
| Motivo obligatorio | [docs/acuerdos-vigentes.md, «Pausas»](../acuerdos-vigentes.md#pausas) dice «Requiere motivo». [docs/requirements.md, «Pausas, disponibilidad y correcciones aprobadas»](../requirements.md#pausas-disponibilidad-y-correcciones-aprobadas) dice expresamente «motivo obligatorio». [docs/user-flow.md, «Pausar y reanudar»](../user-flow.md#pausar-y-reanudar) indica que el operador registra el motivo. |
| Recepción | [Acuerdos, «Recepción y registro»](../acuerdos-vigentes.md#recepción-y-registro) y [requisitos, «Pausas, disponibilidad y correcciones aprobadas»](../requirements.md#pausas-disponibilidad-y-correcciones-aprobadas) definen Status por oficina con operador, disponibilidad, ciudadanos en espera, espera más larga y duración de atención actual. [Flujo, «Consultar, corregir datos y revisar disponibilidad»](../user-flow.md#consultar-corregir-datos-y-revisar-disponibilidad) reproduce esa consulta. [Acuerdos, «Pausas»](../acuerdos-vigentes.md#pausas) y [flujo, «Pausar y reanudar»](../user-flow.md#pausar-y-reanudar) establecen que Recepción consulta la pausa en Status. |
| Administrador | [Acuerdos, «Pausas»](../acuerdos-vigentes.md#pausas), [requisitos, «Pausas, disponibilidad y correcciones aprobadas»](../requirements.md#pausas-disponibilidad-y-correcciones-aprobadas) y [flujo, «Pausar y reanudar»](../user-flow.md#pausar-y-reanudar) enumeran operador, motivo, inicio, fin, duración, oficina y folio asociado en Registro de actividad. [Flujo, «Consultar y corregir registros»](../user-flow.md#consultar-y-corregir-registros) incluye consulta de pausas y reanudaciones. |
| Reanudación y conservación del folio | [Acuerdos, «Disponibilidad y folio actual del operador»](../acuerdos-vigentes.md#disponibilidad-y-folio-actual-del-operador) y «Pausas», requisitos y flujo establecen reanudación sin autorización administrativa, Libre/Ocupado según el folio actual y conservación de responsabilidad, estado y notas al pausar. |

No hay respaldo expreso para que Recepción consulte motivo, historial detallado o tiempos individuales de las pausas. Tampoco se establece expresamente el uso de Status por el administrador. Esos permisos ampliados quedan pendientes, sin incorporarlos como aprobados.

La exposición mínima propuesta para Recepción entrega información operativa; **no es una prohibición funcional definitiva** de consultar otros datos. La consulta propia del operador se propone como soporte de pausa y reanudación, sin añadir un historial personal completo. La consulta administrativa detallada se limita a los campos y registros expresamente aprobados.

## Modelos y referencias

Los tres modelos propuestos se ubican en `folios`. Todas sus claves foráneas utilizan `PROTECT`, hacia `settings.AUTH_USER_MODEL`, Folio, Oficina o los modelos nuevos según corresponda. Tendrán nombres inversos distintos, también cuando varias referencias apunten al mismo modelo. Se conservarán las barreras de escritura pública y de relaciones inversas existentes.

### PausaOperador

| Campo | Tipo propuesto | NULL y procedencia |
| --- | --- | --- |
| `id` | `BigAutoField`, PK | No; identificador técnico generado por la base. |
| `operador` | FK a Usuario | No; actor autorizado, releído de la base. |
| `motivo` | `TextField` | No; texto validado con contenido. |
| `inicio` | `DateTimeField`, `editable=False` | No; fecha del servidor con zona horaria. |
| `fin` | `DateTimeField`, `null=True`, `blank=True`, `editable=False` | Sí; NULL mientras esté abierta, fecha del servidor al reanudar. |
| `folio_contexto` | FK a Folio, `null=True`, `blank=True` | Sí; folio actual al iniciar la pausa, como referencia histórica. |
| `oficina_contexto` | FK a Oficina, `null=True`, `blank=True` | Sí; oficina de ese folio, conservada como contexto histórico. |

Restricciones propuestas:

- Unicidad condicional de `operador` cuando `fin IS NULL`: como máximo una pausa abierta por operador, también en PostgreSQL.
- CHECK de motivo con algún carácter distinto de espacios, además de validación del servicio.
- CHECK `fin IS NULL OR fin >= inicio`.
- CHECK que exija conjuntamente folio y oficina NULL, o conjuntamente ambos no NULL.

Operador, motivo, inicio y contexto quedan inmutables por las vías admitidas. El servicio solo permite pasar `fin` de NULL a una fecha; no reabre una pausa ni modifica un fin anterior.

Sin folio actual, ambos contextos son NULL; no se elige arbitrariamente una oficina asignada. Con folio actual, se conserva su oficina aunque esté desactivada. El servicio comprueba la correspondencia entre folio y oficina: un CHECK ordinario no verifica esa relación entre tablas.

El contexto es evidencia histórica, no una segunda fuente del folio actual. Representar la ausencia de contexto con NULL es una propuesta técnica; los acuerdos no exigen elegir una oficina al pausar sin folio. La presentación de ese caso sigue pendiente.

### EventoDisponibilidad

| Campo | Tipo propuesto | NULL y procedencia |
| --- | --- | --- |
| `id` | `BigAutoField`, PK | No; generado por la base. |
| `pausa` | FK a PausaOperador | No; pausa de la transición. |
| `actor` | FK a Usuario | No; actor autorizado. |
| `fecha` | `DateTimeField`, `editable=False` | No; fecha del servidor con zona horaria. |
| `operacion` | `CharField(max_length=11)` | No; `PAUSA` o `REANUDACION`. |

CHECK de operaciones admitidas y unicidad por `(pausa, operacion)`. Todos los campos quedan inmutables. El operador se obtiene de la pausa; no se duplica en el evento.

El servicio exige que actor y operador sean la misma cuenta. La fecha de PAUSA coincide con `inicio`; la de REANUDACION coincide con `fin`. Estas correspondencias entre registros se garantizan mediante el servicio y su transacción, no mediante un CHECK entre tablas. Los resultados sin transición no generan eventos funcionales.

### SolicitudOperador

| Campo | Tipo propuesto | NULL y procedencia |
| --- | --- | --- |
| `id` | `BigAutoField`, PK | No; generado por la base. |
| `operador` | FK a Usuario | No; actor autorizado. |
| `solicitud_id` | `UUIDField` | No; clave proporcionada por el cliente para identificar la petición. |
| `operacion` | `CharField(max_length=8)` | No; `PAUSAR` o `REANUDAR`. |
| `motivo_solicitado` | `TextField`, `null=True`, `blank=True` | Sí; argumento validado de PAUSAR, NULL en REANUDAR. |
| `pausa_objetivo` | FK a PausaOperador, `null=True`, `blank=True` | Sí; pausa concreta de REANUDAR, NULL en PAUSAR. |
| `resultado` | `CharField(max_length=16)` | No; resultado definitivo construido por el servidor. |
| `pausa_resultado` | FK a PausaOperador | No; pausa a la que corresponde el resultado. |
| `evento_resultado` | FK a EventoDisponibilidad, `null=True`, `blank=True` | Sí; evento de un cambio efectivo, NULL si no hubo transición. |
| `confirmada_en` | `DateTimeField`, `editable=False` | No; fecha del servidor con zona horaria. |

Unicidad por `(operador, solicitud_id)`. El comprobante es inmutable y se inserta directamente con el resultado definitivo; no se persisten estados intermedios. No recibe JSON arbitrario ni almacena disponibilidad.

El CHECK de operación, argumentos y resultado admite solo estas combinaciones:

| Operación | Argumentos | Resultados | Evento |
| --- | --- | --- | --- |
| `PAUSAR` | Motivo no NULL y con contenido; pausa objetivo NULL. | `PAUSADA`, `YA_EN_PAUSA`. | No NULL para `PAUSADA`; NULL para `YA_EN_PAUSA`. |
| `REANUDAR` | Motivo NULL; pausa objetivo no NULL e igual a pausa resultado. | `REANUDADA`, `YA_REANUDADA`. | No NULL para `REANUDADA`; NULL para `YA_REANUDADA`. |

Se utilizarán comprobaciones explícitas de NULL para no admitir combinaciones incoherentes por resultados SQL desconocidos. El servicio verifica que las pausas pertenecen al operador y que el evento corresponde a la pausa y operación; esas condiciones entre tablas no se atribuyen al CHECK.

No se impone como condición histórica que una cuenta siga activa o conserve el rol OPERADOR. La autorización se comprueba al ejecutar cada servicio, sin invalidar registros anteriores.

## Disponibilidad derivada y consulta global del folio

No se añaden a Usuario campos `disponibilidad`, `ocupado`, `en_pausa` ni `folio_actual_id`. Tampoco se almacena duración de pausa: se calcula desde inicio y fin, o desde inicio hasta el instante de consulta si sigue abierta.

El folio actual se consulta globalmente por `operador_responsable` y estado en `LLAMADO` o `EN_ATENCION`. **No se filtra por oficina activa ni asignación activa**: su desactivación no debe ocultar un folio bajo responsabilidad del operador. La existencia de pausa abierta se determina por `fin IS NULL`.

| Fuentes actuales | Disponibilidad calculada |
| --- | --- |
| Existe pausa abierta, con o sin folio actual. | En pausa. |
| Sin pausa abierta y con folio actual. | Ocupado. |
| Sin pausa abierta ni folio actual. | Libre. |

Cuenta activa y rol funcional se comprueban por separado; una cuenta desactivada no produce una cuarta disponibilidad. La lectura obtiene pausa y folio desde una misma instantánea SQL, sin escribir ni generar eventos.

Actualmente Folio solo admite En espera y responsable vacío. La consulta prevista de los estados futuros no los habilita ni modifica sus restricciones. Los casos reales de Ocupado y contexto desde Llamado se verificarán al integrar la segunda entrega; En atención y notas se verificarán cuando se implementen.

## Contratos, permisos y exposición

Firmas propuestas:

```python
consultar_disponibilidad(*, actor, operador_id) -> ResultadoDisponibilidad

pausar_operador(*, actor, motivo, solicitud_id) -> ResultadoOperacionPausa

reanudar_operador(*, actor, pausa_id, solicitud_id) -> ResultadoOperacionPausa
```

`actor` procede del contexto autenticado. Las consultas verifican autenticación, cuenta activa y rol autorizado con datos actuales. Las mutaciones exigen un Usuario persistido de la misma base de escritura, releído bajo bloqueo, con `is_active=True` y rol funcional `OPERADOR`. `is_staff` e `is_superuser` no sustituyen esas comprobaciones. El operador de las mutaciones siempre es el actor: no se acepta un operador destino ni autorización administrativa sustitutiva.

| Servicio y rol | Permiso y datos expuestos |
| --- | --- |
| `consultar_disponibilidad`, Operador | Solo sobre sí mismo: identidad, disponibilidad, `pausa_abierta_id` y referencia mínima del folio actual (identificador, estado y oficina), sin datos personales ni notas. Es el soporte técnico propuesto de pausa y reanudación. |
| `consultar_disponibilidad`, Recepción | Identidad del operador y disponibilidad; En pausa informa la existencia de pausa. No expone motivo, identificador interno de pausa, folio actual ni historial detallado. Es exposición mínima propuesta, no una prohibición funcional definitiva. |
| `pausar_operador` y `reanudar_operador` | Solo el propio operador autenticado, activo y con rol funcional OPERADOR; no requieren autorización administrativa adicional. Devuelven el comprobante de la operación propia. |
| Consulta administrativa de pausas | Un lector adicional propuesto, `consultar_pausas(*, actor, operador_id, ...)`, exclusivo del administrador funcional autenticado y activo. Devuelve operador, motivo, inicio, fin, duración calculada, contexto de oficina/folio y eventos. Los filtros siguen Registro de actividad: fecha, usuario, oficina y acción. No concede por sí mismo acceso del administrador a Status. |

El lector administrativo puede conservar y consultar pausas históricas de cuentas desactivadas; es la cuenta del actor la que debe estar activa. Las métricas restantes de Status, las pantallas y un historial propio completo del operador quedan fuera de esta entrega.

`ResultadoOperacionPausa` devuelve `solicitud_id`, `operacion`, `resultado`, `pausa_id`, `evento_id` o NULL, `confirmada_en` y `repetida`. No incluye disponibilidad almacenada ni presenta el resultado histórico como estado actual. Las consultas no crean comprobantes.

## Pausar y reanudar una pausa concreta

| Situación | Resultado y efectos |
| --- | --- |
| Pausar sin pausa abierta. | `PAUSADA`: crea pausa, evento PAUSA y comprobante. |
| Pausar con pausa abierta. | `YA_EN_PAUSA`: devuelve la pausa existente y crea solo comprobante para una clave nueva; no cambia motivo, inicio ni contexto, ni genera evento. |
| Reanudar una pausa propia abierta. | `REANUDADA`: establece fin y crea evento REANUDACION y comprobante. |
| Reanudar una pausa propia cerrada. | `YA_REANUDADA`: crea solo comprobante para una clave nueva; no cambia el fin ni genera evento. |

El motivo sigue siendo obligatorio para una nueva petición de pausa aunque encuentre una ya abierta. Un motivo diferente no edita la pausa anterior; el argumento queda en el comprobante sin sustituir el motivo de PausaOperador.

Reanudar recibe la pausa concreta mediante `pausa_id`. Una petición retrasada sobre una pausa cerrada no termina otra pausa posterior. Tras una reanudación efectiva, la consulta actual deriva Libre/Ocupado desde el folio; si se consulta después de una nueva pausa, devuelve En pausa.

Pausa inexistente produce `ValidationError`; pausa ajena produce `PermissionDenied`. Actor no autenticado, desactivado o sin rol OPERADOR produce `PermissionDenied`. Motivo inválido, UUID inválido o argumentos incompatibles producen `ValidationError`. No hay registros parciales ante estos errores.

Pausar y reanudar **no actualizan Folio ni EventoFolio**. Conservan responsabilidad, estado y, cuando estén implementadas, notas. No exigen tener una asignación activa para pausar o reanudar; tampoco seleccionan una oficina desde el panel del operador.

## Solicitudes repetidas y resultado histórico

El cliente conserva la misma clave al reintentar una petición y utiliza otra para una intención nueva. La clave identifica la solicitud, sin conceder permisos.

Después de autorizar y bloquear al operador, validar los argumentos y consultar el comprobante:

- Misma clave y mismos argumentos: devuelve el comprobante original con `repetida=True`, sin nuevas escrituras ni eventos.
- Misma clave con otra operación, motivo o pausa objetivo: `ValidationError`.
- Clave nueva: evalúa el estado presente y guarda el resultado normal correspondiente.

El motivo validado se conserva y compara exactamente; no se normaliza silenciosamente. También se confirman `YA_EN_PAUSA` y `YA_REANUDADA`, sin evento funcional, para que un reintento posterior no ejecute una acción distinta. Los errores de autorización, validación o transacción no dejan comprobante.

Repetir un resultado `PAUSADA` puede devolverlo cuando la pausa ya esté cerrada: significa que esa solicitud creó esa pausa. La disponibilidad actual se obtiene con su consulta. Tampoco se vuelve a ejecutar una reanudación confirmada aunque exista otra pausa abierta.

## Transacción conjunta y orden de bloqueos

Cada mutación utiliza una sola `transaction.atomic()` y el mismo alias de escritura para autorización, cambio de pausa, evento y comprobante definitivo. Un fallo en cualquiera revierte el conjunto; una transacción exterior también puede revertirlo. `confirmada_en` es la fecha registrada en el comprobante, no una prueba de que una transacción exterior ya haya confirmado. La confirmación definitiva ocurre al hacer commit de esa transacción. No se difieren eventos a `on_commit` ni a tareas posteriores.

El orden relativo compatible con los servicios existentes es:

```text
Cuentas por PK → oficinas por PK → asignaciones si corresponden
→ pausas → folios si deben bloquearse → escrituras
```

La primera entrega no necesita bloquear asignaciones ni trámites. Para mutaciones propias:

1. Bloquear y releer Usuario; comprobar cuenta activa y rol funcional.
2. Validar argumentos y consultar el comprobante inmutable. Esa lectura no necesita bloquear SolicitudOperador.
3. Leer el contexto necesario bajo el bloqueo de Usuario.
4. Bloquear la oficina de contexto, si existe, sin exigir actividad. Si se necesitan varias oficinas, adquirirlas por PK ascendente antes de pasar a pausas o folios.
5. Bloquear y revalidar la pausa existente o la pausa objetivo.
6. Al crear una pausa con folio actual, bloquearlo después de las categorías anteriores y revalidar el contexto.
7. Guardar cambio efectivo, evento y comprobante, o solo comprobante si el resultado normal no cambia la pausa.

Las lecturas preliminares no adquieren bloqueos fuera de orden. Nunca se adquiere una cuenta después de oficina o folio, ni una oficina después de pausa o folio. Usuario coordina operaciones del mismo operador incluso cuando no existe todavía una pausa; la unicidad condicional protege adicionalmente la pausa abierta en PostgreSQL.

Se probarán pausas simultáneas con claves iguales y distintas, reanudaciones simultáneas y ambos órdenes de pausa frente a reanudación de una pausa concreta. Una pausa nueva que encuentre otra abierta no se convierte en una petición pendiente para crearla después de reanudar. El llamado de la segunda entrega deberá participar en el mismo bloqueo de Usuario.

## Barreras públicas y límites

Los modelos nuevos rechazarán escritura y borrado públicos mediante instancias, querysets, managers por defecto, base e inversos, operaciones masivas y variantes asíncronas. Se conservará la protección de `add`, `set`, `remove` y `clear`, también al seleccionar nuevamente un manager relacionado. La persistencia privada será específica para abrir/cerrar pausa, insertar evento y confirmar solicitud; no habrá una opción pública ni un contexto general para omitir validaciones.

Las claves foráneas protegidas y restricciones garantizan referencias existentes, NULL coherentes, resultados admitidos y unicidades. **SQL directo, deserializadores y APIs internas pueden eludir las barreras del ORM.** Las restricciones no garantizan por sí solas autorización, inmutabilidad ante esas vías, correspondencias entre tablas ni que cada cambio tenga evento y comprobante. Esas garantías corresponden a los servicios y su transacción por las vías admitidas. No se incorporan disparadores SQL ni se afirma una auditoría global completa.

## Archivos previstos y pruebas necesarias

| Archivos previstos | Alcance |
| --- | --- |
| `folios/models.py` | Añadir PausaOperador, EventoDisponibilidad y SolicitudOperador; conservar Folio y EventoFolio sin cambios. |
| `folios/services_disponibilidad.py` | Consultas, contratos, autorización, resultados y mutaciones transaccionales. |
| `folios/managers.py` | Reutilizar y verificar barreras y referencias protegidas existentes; preservar compatibilidad de las relaciones inversas. |
| `folios/migrations/` | Nuevas migraciones únicamente para los tres modelos y sus restricciones, sin reescribir las existentes. |
| Nuevos archivos de pruebas de disponibilidad y concurrencia | Integración, restricciones, exposición por rol, solicitudes, rollback y bloqueos. |
| Documentación nueva de resultados | Registrar ejecución futura y sus límites sin alterar evidencias anteriores. |

La validación posterior utilizó exclusivamente `config.settings_test_migrations`, base `test_atencion_catalogos_migraciones` y usuario `atencion_test`, con conexión real verificada, migraciones reales, `--keepdb --parallel 1 --noinput` y barreras de aislamiento existentes. No se conectó la base normal ni se modificaron privilegios. Los casos reales de estados todavía no implementados conservan su verificación pendiente.

Casos necesarios:

- Motivo obligatorio, texto sin contenido y argumentos inválidos; autorización con datos actuales e independencia de indicadores técnicos.
- Campos obligatorios, NULL coherentes, referencias protegidas, unicidad de pausa abierta y unicidad de eventos y solicitudes con rechazos reales de PostgreSQL.
- Libre y En pausa, reanudación sin folio, exposición mínima por rol y lectura administrativa de pausas históricas.
- Pausas ya abiertas/cerradas, motivo anterior conservado y reanudación de una pausa concreta sin cerrar otra posterior.
- Claves iguales con argumentos iguales o incompatibles; resultados normales sin transición y resultado histórico frente a disponibilidad actual.
- Fallos reales de cambio, evento o comprobante y rollback exterior, sin registros parciales; conservación íntegra de Folio, EventoFolio y eventos CREACION.
- Barreras públicas síncronas, asíncronas y relacionadas, incluida selección repetida del manager inverso.
- Concurrencia con `TransactionTestCase`, conexiones independientes, PIDs distintos, sincronización explícita y espera real comprobada con `pg_blocking_pids`: pausas y reanudaciones con mismas/distintas claves, ambos órdenes entre pausa y reanudación y coordinación con desactivación de cuenta.

La consulta global debe conservarse por construcción sin condiciones de actividad de oficina o asignación. **Los casos reales de Ocupado y contexto desde Llamado se verificarán al integrar la segunda entrega. En atención y notas se verificarán cuando se implementen.** No se ampliará Folio ni se simulará esa implementación para declarar tales casos comprobados ahora.

En la revisión documental inicial no se ejecutaron pruebas de esta primera entrega, no se generaron migraciones ni se modificaron código o bases. Esa evidencia se conserva y se distingue de la implementación posterior.

## Implementación y validación posteriores

Se implementaron los tres modelos, los servicios de consultas por rol, pausa y reanudación, la disponibilidad derivada y la persistencia conjunta de cambio, evento y comprobante. Se reutilizaron las barreras de `folios/managers.py` sin modificarlo; la migración nueva es `folios.0002_pausaoperador_eventodisponibilidad_solicitudoperador_and_more`, sin reescribir migraciones anteriores ni cambiar Folio o EventoFolio.

El [registro 009](../pruebas/009-pausas-disponibilidad-postgresql.md) conserva comandos y resultados: **37 pruebas nuevas satisfactorias, incluidas 12 de concurrencia**, y **140 pruebas satisfactorias de la suite completa que incluyen esas 37**. La prueba de borrado asíncrono se corrigió antes de la ejecución final. `check`, correspondencia modelos/migraciones y formato fueron correctos.

La inspección verificó 3 tablas nuevas, 22 columnas, 19 restricciones y 15 índices; quedaron **22 migraciones aplicadas en pruebas, ninguna pendiente**, y cero datos residuales de aplicación. Se corrigió una comparación del auxiliar dependiente del orden de columnas; no hubo diferencias de esquema. La revisión crítica posterior no encontró defectos, no modificó archivos ni ejecutó nuevas pruebas.

**La aplicación local de `folios.0002` en `atencion_ciudadana` sigue pendiente.** Los casos reales de Ocupado y contexto desde Llamado se verificarán con la segunda entrega; En atención y notas se verificarán cuando se implementen. Los permisos ampliados y demás decisiones funcionales pendientes no se resolvieron durante la implementación.

## Pendientes y segunda entrega

No queda una decisión funcional que bloquee la primera entrega con la exposición mínima propuesta. Permanecen pendientes los permisos ampliados de consulta, la presentación de pausas sin oficina, el significado funcional de Inactivo y el tratamiento de correcciones administrativas que producirían otro folio actual. No se añaden rechazos, liberaciones automáticas ni excepciones administrativas para resolverlo.

La **segunda entrega prevista** es llamado y reserva integrados con pausa y con el límite global de un folio actual en Llamado o En atención por operador, contando todas sus oficinas. Mantendrá cola conjunta, reserva desde Llamado, evento conjunto, solicitudes repetidas y bloqueos compatibles con los servicios existentes. Su diseño e implementación no forman parte de esta primera entrega.

Inicio, notas, cierres y correcciones administrativas siguen fuera del alcance. Los bloqueos provisionales de retirada de asignaciones y salida de OPERADOR de las decisiones 003 y 005 continúan hasta verificar sus reglas definitivas. Se conservan todas las evidencias anteriores.
