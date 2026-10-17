# 013 — Diseño de inicio de atención del folio propio

Fecha de cierre del diseño: **15 de octubre de 2026**.

Estado actualizado al **15 de octubre de 2026**: **backend validado en PostgreSQL aislado; 0004 aplicada únicamente allí y DEMO recuperado. Interfaz de inicio preparada; pruebas HTTP, regresión y comprobación manual de esta integración pendientes. Aplicación de 0004 en la base normal pendiente**. El [registro 019](../pruebas/019-inicio-atencion-postgresql.md) conserva resultados, incidencias y recuperación anteriores; las preparaciones sin conexión se registran por separado.

## Autoridad y alcance

Los [acuerdos vigentes](../acuerdos-vigentes.md), «Recorrido de atención» y «Pausas», son la fuente principal. Se conservan la responsabilidad desde Llamado de la [decisión 004](004-cola-y-responsabilidad-de-folios.md), el folio actual global de la [006](006-disponibilidad-y-folio-actual-del-operador.md), los comprobantes y bloqueos de la [007](007-diseno-pausas-y-disponibilidad.md) y la [008](008-diseno-llamado-y-reserva.md), las lecturas de la [011](011-lecturas-autorizadas-de-operador.md) y la integración existente de la [012](012-integracion-pantallas-operador.md).

Esta decisión cierra únicamente el diseño de **Llamado → En atención** y registra su backend y posterior preparación de interfaz. No incluye notas, finalización, denegación, traslados, correcciones administrativas u otras acciones. Las evidencias previas a 019 no validan el backend de inicio; 019 tampoco valida su nueva interfaz. Los avisos antiguos sobre llamado pendiente en documentos funcionales conservan su contexto; la implementación existente se describe en 008, 011 y 012.

## Reglas funcionales aprobadas

1. Para pasar de Llamado a En atención, el operador debe haber cerrado su pausa. Reanudar no inicia automáticamente. Un comprobante `EN_PAUSA` conserva su resultado al repetir la misma clave; iniciar después requiere una nueva intención explícita.
2. La autorización para iniciar deriva de la responsabilidad vigente sobre el folio actual propio, con cuenta activa y rol funcional `OPERADOR`. **No se exige nuevamente asignación activa a la oficina.** Esto no modifica la prohibición de retirar asignaciones con folios asignados sin finalizar ni los requisitos para recibir nuevos folios.

La reserva y la responsabilidad comienzan al llamar; iniciar registra otro momento, sin reasignar. Se conservan llegada original, responsable, datos del registro, oficina, trámite e historial. Catálogos desactivados no impiden continuar el folio propio. El máximo sigue siendo un folio actual por operador entre todas sus oficinas; iniciar no libera capacidad ni llama a otro ciudadano.

Cuenta inactiva y rol distinto de `OPERADOR` impiden iniciar aunque exista un folio a cargo. `is_staff` e `is_superuser` no sustituyen el rol. La visibilidad del folio propio sin asignación activa, aprobada en 011, es un permiso de consulta: la escritura exige además propiedad, estado y pausa conforme a esta decisión. Un estado histórico con asignación inactiva no habilita su retirada por vías públicas; las protecciones provisionales de 003 se conservan.

Los nombres de contratos, campos, resultados sin transición, representación de auditoría, restricciones y migración descritos a continuación son decisiones técnicas para esta entrega, separadas de las dos reglas funcionales aprobadas.

## Servicio y resultado

Servicio implementado en `folios/services_inicio.py` y validado en PostgreSQL aislado conforme al registro 019:

```python
iniciar_atencion(
    *,
    actor: Usuario,
    folio_id: UUID | str,
    solicitud_id: UUID | str,
) -> ResultadoInicio
```

`actor` procede del contexto autenticado del servidor. `folio_id` fija el folio concreto mostrado; no es una selección libre de ciudadano ni una orden de operar sobre cualquier folio. El servicio exige que sea el actual propio. No recibe oficina, responsable destino, fecha, estado ni alias de base.

`ResultadoInicio` es una dataclass inmutable y materializada:

| Campo | Contenido |
| --- | --- |
| `solicitud_id` | UUID normalizado de la petición. |
| `operacion` | Siempre `INICIAR`. |
| `resultado` | `INICIADA`, `YA_EN_ATENCION` o `EN_PAUSA`. |
| `folio_id` | UUID del objetivo confirmado, no NULL en los tres resultados. |
| `evento_id` | Identificador de EventoFolio solo para `INICIADA`; NULL en los demás. |
| `confirmada_en` | Fecha con zona horaria conservada en el comprobante. |
| `repetida` | Indica recuperación del comprobante existente. |

El resultado describe la petición histórica. No devuelve disponibilidad almacenada ni deduce el estado presente a partir de un comprobante. La fecha de inicio visible se obtiene del lector propio, no de una lectura diferida del resultado.

## Orden de evaluación y errores

Todo ocurre en el alias de escritura de Folio y dentro de una sola `transaction.atomic()`:

1. Verificar identidad autenticada y persistida en ese alias. Bloquear y releer Usuario; exigir cuenta activa y rol `OPERADOR`, incluso para recuperar un comprobante histórico. No confiar en una instancia antigua ni en flags técnicos.
2. Validar y normalizar ambos UUID. Buscar el comprobante por `(operador, solicitud_id)` y comparar operación y argumentos, incluido el folio objetivo. Si coincide, devolver el original con `repetida=True`, sin escrituras y **antes de evaluar propiedad, estado o pausa actuales**. Si difiere, `ValidationError`.
3. Para una clave nueva, localizar el folio solicitado y su oficina como contexto preliminar. Folio inexistente produce `ValidationError`; responsable distinto del actor produce `PermissionDenied`, sin devolver datos del ciudadano. No sustituir el objetivo por otro folio actual.
4. Adquirir los bloqueos descritos abajo y revalidar propiedad, oficina y estado con datos actuales. Solo se admiten los estados actuales `LLAMADO` y `EN_ATENCION`; los demás producen `ValidationError`. El índice global garantiza que el folio propio en esos estados sea el único actual. Un cambio de contexto fuera del protocolo se rechaza sin escrituras.
5. Aplicar los resultados en este orden:

| Condición de solicitud nueva autorizada | Resultado | Escrituras |
| --- | --- | --- |
| Folio propio ya `EN_ATENCION`. | `YA_EN_ATENCION`. | Solo comprobante; conserva fecha y no genera evento. |
| Folio propio `LLAMADO` y pausa abierta. | `EN_PAUSA`. | Solo comprobante; conserva folio y pausa. |
| Folio propio `LLAMADO` sin pausa abierta. | `INICIADA`. | Estado y fecha de inicio, evento INICIO y comprobante. |

`YA_EN_ATENCION` precede a la pausa porque no intenta otra transición: puede confirmar que el mismo folio ya está iniciado aunque el operador haya pausado después. Ninguna rama cierra pausas. Errores de identidad, autorización o validación no dejan comprobante. Un fallo de persistencia revierte todas las escrituras.

## Idempotencia y comprobantes anteriores

Se extiende `SolicitudOperador`, sin otra tabla ni otro ámbito de claves. Se mantienen la unicidad `(operador, solicitud_id)` y los comprobantes inmutables insertados directamente con resultado definitivo.

- Añadir operación `INICIAR` y resultados `INICIADA` y `YA_EN_ATENCION`; reutilizar `EN_PAUSA`. Los tamaños actuales de operación (8) y resultado (16) son suficientes.
- Añadir `folio_objetivo`, FK UUID a Folio, nullable, `PROTECT`, mediante `FoliosForeignKey` y con `related_name="solicitudes_inicio_objetivo"`. Será no NULL únicamente para INICIAR.
- Reutilizar `folio_resultado` y `evento_folio_resultado`, sin cambiar el significado de los eventos de disponibilidad ni sus referencias.
- Ampliar `buscar_solicitud` en `folios/solicitudes.py` para comparar también el objetivo. Los servicios PAUSAR, REANUDAR y LLAMAR usarán objetivo NULL; conservarán sus argumentos, constructores y persistencia específicos.

El CHECK de solicitudes conserva las ramas existentes y les exige explícitamente `folio_objetivo IS NULL`. Para INICIAR exige: motivo, pausa objetivo, pausa resultado y evento de disponibilidad NULL; objetivo y folio resultado no NULL e iguales; resultado admitido y evento de folio no NULL solo para INICIADA. YA_EN_ATENCION y EN_PAUSA exigen evento de folio NULL. Se usarán comprobaciones explícitas de NULL para evitar aceptar combinaciones por el valor SQL desconocido.

La correspondencia entre comprobante, operador, folio y evento INICIO se valida en el servicio; un CHECK no compara tablas distintas. `confirmada_en` no se modifica al repetir. El mismo UUID pertenece a un ámbito distinto si cambia el operador; cambiar operación u objetivo dentro del mismo ámbito es incompatible.

Casos que el contrato debe conservar:

- Doble envío y respuesta perdida: misma clave y objetivo devuelven el original, sin otra fecha ni evento.
- Dos claves distintas sobre el mismo folio: una inicia; la posterior confirma YA_EN_ATENCION.
- EN_PAUSA seguido de reanudación: la misma clave sigue devolviendo EN_PAUSA. Solo una nueva intención explícita, con nueva clave, puede iniciar.
- Formulario antiguo aún no procesado: evalúa el folio firmado contra el estado presente. Si ya no es el actual propio, se rechaza; nunca inicia el que lo sustituyó.
- Solicitud confirmada antigua: recupera su resultado original tras reautorizar identidad, actividad y rol, aunque el estado o responsabilidad del folio hayan cambiado después. Esto permite consultar el comprobante propio, no ejecutar otra transición sobre ese folio.
- Comprobantes previos de llamado o disponibilidad: conservan valores, referencias y comportamiento de reintento. Una clave suya no se reutiliza para iniciar.

## Transición, tiempos y auditoría atómica

Añadir a Folio `inicio_atencion`, DateTimeField nullable y no editable. Solo INICIADA establece conjuntamente `estado=EN_ATENCION` e `inicio_atencion=instante_del_servidor`; no vuelve a guardar el responsable ni otros campos. La fecha no se reemplaza con claves nuevas ni repetidas.

Añadir operación `INICIO` a EventoFolio. Su evidencia será:

- Folio, actor y responsable histórico: `actor = operador_responsable = responsable vigente` bajo bloqueo.
- Transición `LLAMADO → EN_ATENCION` y fecha igual a `inicio_atencion`.
- Nueva FK `oficina_contexto` a Oficina, nullable y `PROTECT`, mediante `FoliosForeignKey` con `related_name="eventos_inicio"`. Para INICIO será obligatoria y corresponderá a la oficina del folio bajo bloqueo; conserva ese contexto sin depender de asignaciones posteriores.
- `datos_iniciales=NULL` y **`asignacion_autorizante=NULL`** para INICIO. No se busca una asignación activa ni se exige encontrar una referencia histórica para autorizar el inicio.

La asignación autorizante existente conserva su significado y valores en LLAMADO; puede estar inactiva después sin invalidar aquella evidencia. CREACION conserva su JSON. No se renombra ni reutiliza esa FK como autorización del inicio. Los nombres inversos existentes se conservan para evitar cambios ajenos al alcance.

El CHECK de eventos ampliará las ramas existentes: oficina contexto NULL en CREACION y LLAMADO; para INICIO, anterior explícitamente no NULL e igual a LLAMADO, nuevo EN_ATENCION, responsable no NULL e igual al actor, oficina contexto no NULL, datos iniciales y asignación autorizante NULL. Se mantiene la unicidad de CREACION. No se añade unicidad permanente de INICIO por folio: el bloqueo y el cambio de estado impiden duplicación en esta entrega sin imponer restricciones sobre futuros recorridos fuera de alcance.

Un mismo instante con zona horaria se usa en fecha de inicio, evento INICIO y confirmación del comprobante INICIADA. La coherencia temporal se valida con llegada original y eventos previos del folio; no se inventan tiempos históricos ni se ajustan silenciosamente. El CHECK de Folio exigirá también `inicio_atencion >= llegada_original` cuando tenga inicio. La igualdad entre registros y el orden respecto del llamado se verifican en el servicio.

Estado, fecha, evento y comprobante se guardan en la misma transacción y conexión. Un fallo en cualquiera o rollback exterior revierte el conjunto. El evento no se difiere a `on_commit` ni a una tarea. `confirmada_en` registra un instante del servidor, no acredita por sí sola el commit de una transacción exterior.

## Bloqueos y concurrencia

Se conserva el orden relativo de 007 y 008:

```text
Usuario → oficinas por PK → asignaciones si corresponden
→ pausas si se bloquean → folio → escrituras
```

Para inicio se bloquean **Usuario → oficina del objetivo → folio** mediante `select_for_update()`, revalidando después de esperar. Las lecturas preliminares no bloquean el folio antes de la oficina. No se bloquean asignaciones ni trámites ni se filtra actividad del catálogo. No se adquiere después otra oficina o cuenta; un contexto cambiado fuera del protocolo provoca rechazo.

La pausa se consulta con datos actuales bajo el bloqueo de Usuario, sin necesitar bloquear su fila: pausa y reanudación participan en ese mismo bloqueo, incluso cuando no existe una pausa abierta. No se usa la consulta pública de disponibilidad para autorizar la escritura. No se seleccionan pendientes ni se usa `skip_locked`.

El bloqueo de Usuario serializa inicio, llamado, pausa, reanudación y cambios de cuenta del mismo operador. Si pausa gana, inicio confirma EN_PAUSA; si inicio gana, una pausa posterior conserva el folio En atención. Si reanudación gana, una solicitud nueva puede iniciar; si inicio en pausa gana, su comprobante seguirá EN_PAUSA. Llamado conserva OCUPADO tras iniciar, o EN_PAUSA si corresponde. Otro operador no puede iniciar el objetivo ajeno.

Se mantiene `folios_folio_actual_unico`, que ya incluye LLAMADO y EN_ATENCION entre todas las oficinas. No se modifica la selección ni el orden de bloqueo de todas las oficinas que utiliza llamado. Los servicios públicos siguen siendo la vía de escritura; SQL directo y APIs internas pueden eludir las barreras del ORM, y las restricciones no sustituyen la autorización ni garantizan por sí solas auditoría entre tablas.

## Restricciones y estado de migración

La migración es [**`folios.0004_inicio_de_atencion`**](../../folios/migrations/0004_inicio_de_atencion.py), dependiente de 0003. Se generó inicialmente en memoria con apertura de conexiones bloqueada y posteriormente se aplicó y verificó **solo en `test_atencion_catalogos_migraciones / atencion_test`**, con respaldo nuevo y preservación de DEMO. El registro 019 detalla las reversiones y reaplicaciones de las pruebas de migración aisladas. **Su aplicación en la base normal sigue pendiente; esa base no se conectó.** No se reescribieron 0001–0003 ni se modificó 0004 después de aplicarla.

1. Añadir `inicio_atencion` a Folio, `oficina_contexto` a EventoFolio y `folio_objetivo` a SolicitudOperador, todos nullable y sin reconstrucción de datos históricos.
2. Ampliar choices de Folio con EN_ATENCION, de EventoFolio con INICIO y de solicitudes con las operaciones/resultados descritos; los tamaños actuales admiten esos valores.
3. Sustituir el CHECK de Folio para admitir exactamente: EN_ESPERA sin responsable ni inicio; LLAMADO con responsable y sin inicio; EN_ATENCION con responsable e inicio no NULL. Añadir coherencia de fecha respecto de llegada original.
4. Ampliar los CHECK de eventos y solicitudes con las combinaciones explícitas anteriores, conservando válidas sus ramas históricas. Mantener índices, unicidades, FK protegidas y barreras de escritura pública, también managers inversos y variantes asíncronas.

Todos los folios existentes En espera o Llamado conservan estado, responsable y llegada; `inicio_atencion` queda NULL. Los eventos previos conservan íntegramente sus datos y `oficina_contexto` queda NULL. Los comprobantes anteriores conservan claves, resultados, fechas y referencias; `folio_objetivo` queda NULL, incluido LLAMAR, cuyo resultado no se convierte en argumento objetivo.

La validación aislada verificó operaciones y SQL de la migración, restricciones e índices válidos, conservación de datos y compatibilidad de reintentos. No se planifica un retroceso que elimine evidencia de inicios ya registrados: una reversión tras usar el nuevo estado requerirá evaluación específica de preservación, sin borrar o convertir datos para hacerla pasar.

## Cobertura de backend y pruebas de interfaz pendientes

| Grupo | Cobertura necesaria |
| --- | --- |
| Servicio y autorización | Llamado propio pasa a En atención; fecha del servidor y resultado inmutable. Actores anónimos, no persistidos, de otro alias, inactivos o de rol distinto; instancias obsoletas y todas las combinaciones de flags, también al repetir. Folio inexistente, ajeno o con estado incompatible. |
| Responsabilidad y pausa | Inicio propio sin asignación activa, mediante fixture histórico aislado sin habilitar retirada; catálogos desactivados. Pausa impide iniciar y no cambia el folio; reanudar no inicia; misma clave conserva EN_PAUSA y una nueva intención permite iniciar. Pausar tras iniciar conserva fecha, responsable y estado; reanudar deriva Ocupado. |
| Idempotencia | Doble envío, respuesta perdida, claves iguales y distintas, objetivos/operaciones incompatibles, ámbitos por operador y solicitudes antiguas confirmadas/no procesadas. YA_EN_ATENCION con pausa posterior no altera el inicio. Reintentos de todos los comprobantes anteriores conservan sus resultados. |
| Atomicidad e integridad | Fallo en actualización, evento o comprobante y rollback exterior; ausencia de registros parciales. Rechazos PostgreSQL por NULL incoherentes, fechas inválidas, actor distinto, referencias inexistentes y segundo folio actual. Correspondencias entre tablas y UPDATE limitado; FK PROTECT y barreras públicas/inversas/asíncronas. |
| Concurrencia real | TransactionTestCase PostgreSQL, conexiones y PIDs distintos, sincronización explícita y espera comprobada con pg_blocking_pids. Dos inicios con misma/distinta clave; inicio frente a llamado, pausa, reanudación y desactivación/cambio de rol, en ambos órdenes; rollback del primer contendiente. Dos operadores y folio ajeno; oficinas compartidas/disjuntas, coordinación con asignaciones y catálogos sin inversión de bloqueos. |
| Migración y preservación | De 0003 al esquema nuevo con En espera, Llamado, CREACION/LLAMADO, pausas abiertas/cerradas y comprobantes de todos los resultados anteriores. Comparar todos los valores y referencias existentes, comprobar campos nuevos NULL y repetir comprobantes tras migrar; no basta comparar conteos. |
| Lecturas y regresión | Folio propio En atención con fecha de inicio en la misma instantánea autorizada; proyección inmutable y sin escrituras, independencia de asignaciones/catálogos y permisos de disponibilidad conservados. Llamado sigue bloqueado por capacidad global. Ajustar expectativas que hoy rechazan EN_ATENCION y las pruebas de migración para que su limpieza recupere el esquema vigente, sin dejarlas en 0003. |
| HTTP e interfaz posterior | Métodos, CSRF, rol vigente, no-store, firma, objetivo concreto, tokens antiguos de otras operaciones, doble POST, mensajes históricos, errores 400/403/503, mismo token al reintentar y ausencia de redirecciones abiertas. Flujo con y sin JavaScript, foco, teclado y adaptación. |

Los fixtures de cambio de rol o asignación inactiva no habilitan operaciones públicas hoy bloqueadas. Las futuras pruebas usarán exclusivamente infraestructura aislada y preservación previa del estado vigente, sin atribuir al inicio las pruebas anteriores.

Los **48 casos de backend** son 26 funcionales y de restricciones en `test_inicio.py`, 20 de concurrencia en `test_inicio_concurrencia.py` y 2 de migración en `test_migracion_inicio.py`. Quedaron verificados tras corregir el auxiliar del fixture de migración y están incluidos en la regresión de 356 casos satisfactoria del registro 019. La cobertura HTTP de inicio, la lectura de su fecha y su integración visual no formaron parte de aquella validación: se preparan ahora, sin ejecutarlas. El lector existente conserva su contrato y su comprobación con el estado En atención pasó en aquella etapa.

## Integración preparada en Atención actual

POST `/operacion/iniciar/`, protegido por rol OPERADOR, CSRF y `never_cache`, delega exclusivamente en `iniciar_atencion` con `request.user`, UUID de solicitud y folio firmados. GET `/operacion/actual/` continúa sin selección por UUID ni escrituras. No se modifican los servicios existentes, sus contratos, modelos o migraciones.

El botón **Iniciar atención** aparece solo en Atención actual para el folio Llamado propio, sin pausa ni discrepancias entre lecturas. En pausa se ofrece reanudar y se explica que iniciar requiere otra acción explícita; no hay envío encadenado. En atención se muestran el estado y la fecha de inicio con zona horaria. No se exigen asignaciones activas para habilitar el botón; el servicio revalida identidad, cuenta, rol, responsabilidad, estado y pausa bajo sus bloqueos al recibir el POST.

El lector existente no expone `inicio_atencion` y conserva su contrato. `folios/lecturas_inicio_operador.py` añade una proyección complementaria propia, inmutable y materializada: folio, estado y fecha se consultan junto con la cuenta activa y el rol OPERADOR en una sola sentencia SQL, sin exigir asignaciones ni actividad de catálogos. La vista compara folio y estado con el detalle mostrado; una fecha ausente o discrepante pide actualizar y no se atribuye a otro folio.

La intención firmada de INICIAR incluye actor, operación, solicitud UUID, folio UUID concreto, destino cerrado y pausa objetivo NULL. No se admiten campos POST alternativos para sustituirlos. Se conservan el salt y la estructura de cinco campos de los tokens existentes de LLAMAR, PAUSAR y REANUDAR mediante validación específica por operación; no se les exige `folio_id`. No se añade caducidad funcional que invalide comprobantes antiguos.

Las respuestas confirmadas siguen POST → redirección → GET a Atención actual. Los mensajes distinguen INICIADA, YA_EN_ATENCION y EN_PAUSA nuevos del «Resultado original» de un comprobante repetido; repetir no afirma otra transición. Un error 400 conserva token y argumentos válidos; un 503 invita a repetir la misma petición sin afirmar si hubo commit. Un token inválido no ofrece reenviarlo. Permisos y CSRF mantienen su rechazo 403. No se reenvía una petición de inicio ni se reemplaza su clave automáticamente al reanudar o ante un error. Cada formulario nuevo de inicio genera otra clave, pero su envío requiere la acción explícita del operador. Tras EN_PAUSA, ese formulario permite expresar otra intención después de reanudar; repetir el token anterior conserva EN_PAUSA. La pantalla y el servicio no sustituyen nunca el folio objetivo de una intención antigua.

Se reutilizan formularios HTML y ayuda JavaScript opcional de 012, sin reintentos automáticos ni cambios al script. El POST nativo funciona sin JavaScript; el botón conserva foco visible y ocupa el ancho disponible en ventana estrecha. La navegación mantiene únicamente Cola de atención y Atención actual. No se incorporan otras acciones ni datos adicionales de pausas.

## Entrega documental inicial y conservación de DEMO

La entrega documental inicial modificó únicamente acuerdos, esta decisión y la referencia breve de README. No modificó código, modelos, pruebas ni migraciones ni ejecutó comandos de Django, pruebas u operaciones de base de datos. Entonces quedaron pendientes implementación, migración, pruebas y botón. No quedan decisiones funcionales pendientes para este inicio dentro del alcance descrito; las demás acciones conservan sus pendientes previos.

El estado vigente de DEMO procede de la comprobación manual del [registro 018](../pruebas/018-comprobacion-manual-operador.md): folio Llamado a cargo de `operador_demo`, otro pendiente y las pausas de esa sesión. La preparación documental y de código no tocó esa base. La validación posterior de 019 capturó y recuperó ese estado desde un respaldo nuevo, sin cargar respaldos anteriores a la sesión manual. Antes de otra validación deberá preservarse nuevamente el estado vigente o utilizarse otra base aislada que no lo altere.

## Preparación del backend — 15 de octubre de 2026

Se preparó `iniciar_atencion` con identidad persistida, relectura de cuenta y rol bajo bloqueo antes de recuperar comprobantes; objetivo UUID concreto y responsabilidad vigente sin consultar asignaciones; prioridad YA_EN_ATENCION sobre pausa para solicitudes nuevas; EN_PAUSA histórico y nueva intención explícita para iniciar después. La transición escribe únicamente estado e inicio; evento INICIO y comprobante se insertan en la misma transacción. La evidencia temporal se compara con llegada y eventos previos sin exigir un evento histórico para autorizar ni reconstruir fechas.

| Archivo | Cambio preparado |
| --- | --- |
| `folios/services_inicio.py` | Servicio, resultados inmutables y persistencia privada específica de inicio. |
| `folios/models.py`, `folios/migrations/0004_inicio_de_atencion.py` | Tres campos nullable, estados/resultados nuevos y CHECK ampliados; unicidad global y comprobantes previos conservados. |
| `folios/solicitudes.py` | Comparación del folio objetivo; NULL por defecto conserva los contratos de llamado y disponibilidad. |
| `folios/services_disponibilidad.py` | Comentario actualizado; no cambian consultas, permisos ni mutaciones existentes. |
| `folios/test_inicio.py`, `test_inicio_concurrencia.py`, `test_migracion_inicio.py` | Casos funcionales, restricciones, reintentos anteriores, concurrencia real y conservación completa de valores/referencias desde 0003; fallo simulado de DDL y recuperación del esquema vigente. |
| `folios/test_migracion_llamado.py` | Limpieza registrada antes de retroceder; restaura todas las hojas actuales del grafo, incluso si falla setUp, en lugar de dejar el esquema en 0003. La prueba nueva de migración utiliza el mismo criterio. |
| `folios/test_llamado.py`, `test_lecturas_operador.py`, `test_operador.py` | Se admite EN_ATENCION sin debilitar unicidad ni coherencia de fecha; lectura sigue sin iniciar y la pantalla no incorpora formulario de inicio. |

Verificaciones realizadas sin configuración local ni credenciales: compilación de sintaxis de 72 archivos Python en memoria, importación de servicio y módulos de pruebas sin invocar casos ni runner, checks de modelos con `databases=[]`, grafo de migraciones sin conflictos y comparación mediante `MigrationLoader(None)` y `MigrationAutodetector` sin diferencias entre modelos y migraciones. Se compilaron en memoria los cinco CHECK de Folio, EventoFolio y SolicitudOperador a SQL PostgreSQL, sin ejecutar sentencias. La apertura de conexiones y cursores estuvo bloqueada explícitamente; no hubo intentos de conexión. Se revisó el diff y el formato con `git diff --check`. Estas verificaciones no acreditan ejecución del servicio, SQL real, contención PostgreSQL ni preservación efectiva tras migrar.

**Al finalizar aquella preparación** seguían pendientes la aplicación de 0004, los 48 casos nuevos, la regresión, la inspección posterior y la interfaz. En esa etapa no se ejecutaron suites ni operaciones de base, migraciones, servidores o restauraciones; no se hizo commit ni push. El backend requiere el esquema de 0004 para ejecutarse. La validación posterior se registra a continuación y no se atribuye a las verificaciones sin conexión.

## Validación aislada — 15 de octubre de 2026

El [registro 019](../pruebas/019-inicio-atencion-postgresql.md) documenta revisión completa del servicio, CHECK, SQL, bloqueos y reintentos, identidad real aislada, puertos 8000/8001 detenidos, ausencia de conexiones ajenas y respaldo nuevo privado de 18 tablas y 16 secuencias. 0004 se aplicó una vez antes del runner: 24 migraciones y ninguna pendiente, datos/secuencias de aplicación conservados y tres campos nuevos NULL.

La primera ejecución de 48 casos pasó los 26 funcionales/de restricciones y los 20 de concurrencia. Los dos de migración fallaron antes de construir sus datos por colisión entre el argumento `nombre` del auxiliar `insertar` y el campo homónimo de Oficina. Se cambió únicamente ese argumento a `modelo`; no se relajaron expectativas ni se modificaron servicio, restricciones o migración. Pasaron los dos casos corregidos y después la **regresión completa de 356 pruebas Django, incluidas las 48 nuevas**, además de 8 pruebas JavaScript existentes. `check` y correspondencia modelos/migraciones fueron correctos.

Se realizaron dos recuperaciones selectivas, también después de la pasada fallida, seguidas de comprobaciones independientes de solo lectura: 17 tablas de datos idénticas al manifiesto nuevo, 15 próximas asignaciones originales y valores nuevos NULL. Se conservaron el esquema de 0004, todas las restricciones validadas, índices válidos y el historial y secuencia de migraciones resultantes. Se confirmó un Llamado propio de `operador_demo` y un pendiente. El registro detalla también las correcciones del auxiliar privado de verificación, sin cambios en el dump o datos recuperados.

**Aplicación de 0004 en la base normal pendiente; no se conectó ni modificó esa base.** Rutas, formularios, botón, fecha de inicio e integración visual seguían pendientes en aquella validación. No se reiniciaron servidores ni se hizo commit o push durante ella. Respaldo, manifiesto, recuperación y registros privados permanecen fuera de Git.

## Preparación de interfaz sin conexión — 15 de octubre de 2026

Se prepararon formularios, ruta, vista, plantilla, estilo y lectura complementaria propios, junto con **36 casos en `folios/test_inicio_operador.py`**. Cubren inicio y fecha, preservación, asignaciones/catálogos inactivos, rol/cuenta vigentes incluso para comprobantes históricos, flags, folio ajeno, CSRF real, firmas manipuladas o ajenas, UUID y objetivo concreto, doble POST, respuesta perdida, errores 400/403/503, métodos/cache y destinos internos. También contemplan EN_PAUSA repetido tras reanudar, nueva intención explícita, YA_EN_ATENCION antes de pausa, formularios antiguos, tokens previos de las tres operaciones, HTML nativo y discrepancias de lectura. Se ajustó una expectativa HTTP anterior: ahora corresponde ofrecer inicio al mostrar un Llamado propio sin pausa; las demás garantías se conservan.

Se comprobaron sin conexión la sintaxis de 73 archivos Python, importación del módulo nuevo, checks de modelos/URL/plantillas sin bases, resolución de ruta, compilación de plantillas, correspondencia de modelos/migraciones en memoria, formatos de tokens y renderizado con datos sintéticos de Llamado, pausa y En atención. La configuración fue sintética, sin cargar credenciales; apertura de conexiones y cursores bloqueadas, con **cero invocaciones**. Estas comprobaciones no ejecutan los 36 casos ni acreditan comportamiento HTTP o PostgreSQL.

**Pendientes:** ejecutar los casos nuevos y la regresión en infraestructura aislada con preservación nueva del DEMO vigente, comprobar manualmente teclado/foco, ventana estrecha y flujo sin JavaScript; aplicar 0004 en la base normal en una etapa autorizada. Las **356 pruebas Django, incluidas las 48 de backend, y las 8 JavaScript satisfactorias** siguen siendo evidencia anterior de 019; no se repitieron ni validan esta interfaz. En esta preparación no hubo suites, operaciones de base, aplicación/reversión de migraciones, servidores ni restauraciones. DEMO se conserva sin tocar y no se hizo commit ni push.
