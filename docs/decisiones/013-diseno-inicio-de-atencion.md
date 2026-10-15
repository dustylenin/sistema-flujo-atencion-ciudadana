# 013 — Diseño de inicio de atención del folio propio

Fecha de cierre del diseño: **15 de octubre de 2026**.

Estado: **diseño técnico documentado con las dos reglas funcionales aprobadas; implementación, generación y aplicación de la migración, pruebas e integración de interfaz pendientes**.

## Autoridad y alcance

Los [acuerdos vigentes](../acuerdos-vigentes.md), «Recorrido de atención» y «Pausas», son la fuente principal. Se conservan la responsabilidad desde Llamado de la [decisión 004](004-cola-y-responsabilidad-de-folios.md), el folio actual global de la [006](006-disponibilidad-y-folio-actual-del-operador.md), los comprobantes y bloqueos de la [007](007-diseno-pausas-y-disponibilidad.md) y la [008](008-diseno-llamado-y-reserva.md), las lecturas de la [011](011-lecturas-autorizadas-de-operador.md) y la integración existente de la [012](012-integracion-pantallas-operador.md).

Esta decisión cierra únicamente el diseño de **Llamado → En atención**. No implementa código ni incluye notas, finalización, denegación, traslados, correcciones administrativas u otras acciones. Las evidencias anteriores no validan el inicio. Los avisos antiguos sobre llamado pendiente en documentos funcionales conservan su contexto; la implementación existente se describe en 008, 011 y 012.

## Reglas funcionales aprobadas

1. Para pasar de Llamado a En atención, el operador debe haber cerrado su pausa. Reanudar no inicia automáticamente. Un comprobante `EN_PAUSA` conserva su resultado al repetir la misma clave; iniciar después requiere una nueva intención explícita.
2. La autorización para iniciar deriva de la responsabilidad vigente sobre el folio actual propio, con cuenta activa y rol funcional `OPERADOR`. **No se exige nuevamente asignación activa a la oficina.** Esto no modifica la prohibición de retirar asignaciones con folios asignados sin finalizar ni los requisitos para recibir nuevos folios.

La reserva y la responsabilidad comienzan al llamar; iniciar registra otro momento, sin reasignar. Se conservan llegada original, responsable, datos del registro, oficina, trámite e historial. Catálogos desactivados no impiden continuar el folio propio. El máximo sigue siendo un folio actual por operador entre todas sus oficinas; iniciar no libera capacidad ni llama a otro ciudadano.

Cuenta inactiva y rol distinto de `OPERADOR` impiden iniciar aunque exista un folio a cargo. `is_staff` e `is_superuser` no sustituyen el rol. La visibilidad del folio propio sin asignación activa, aprobada en 011, es un permiso de consulta: la escritura exige además propiedad, estado y pausa conforme a esta decisión. Un estado histórico con asignación inactiva no habilita su retirada por vías públicas; las protecciones provisionales de 003 se conservan.

Los nombres de contratos, campos, resultados sin transición, representación de auditoría, restricciones y migración descritos a continuación son decisiones técnicas para esta entrega, separadas de las dos reglas funcionales aprobadas.

## Servicio y resultado

Servicio previsto en `folios/services_inicio.py`:

```python
iniciar_atencion(
    *,
    actor: Usuario,
    folio_id: UUID | str,
    solicitud_id: UUID | str,
) -> ResultadoInicio
```

`actor` procede del contexto autenticado del servidor. `folio_id` fija el folio concreto mostrado; no es una selección libre de ciudadano ni una orden de operar sobre cualquier folio. El servicio exige que sea el actual propio. No recibe oficina, responsable destino, fecha, estado ni alias de base.

`ResultadoInicio` será una dataclass inmutable y materializada:

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

## Restricciones y migración pendiente

La migración prevista es **`folios.0004_inicio_de_atencion`**, dependiente de 0003; el nombre queda sujeto a que no aparezca otra migración antes de implementar. **No se ha generado ni aplicado**. No se reescriben 0001–0003.

1. Añadir `inicio_atencion` a Folio, `oficina_contexto` a EventoFolio y `folio_objetivo` a SolicitudOperador, todos nullable y sin reconstrucción de datos históricos.
2. Ampliar choices de Folio con EN_ATENCION, de EventoFolio con INICIO y de solicitudes con las operaciones/resultados descritos; los tamaños actuales admiten esos valores.
3. Sustituir el CHECK de Folio para admitir exactamente: EN_ESPERA sin responsable ni inicio; LLAMADO con responsable y sin inicio; EN_ATENCION con responsable e inicio no NULL. Añadir coherencia de fecha respecto de llegada original.
4. Ampliar los CHECK de eventos y solicitudes con las combinaciones explícitas anteriores, conservando válidas sus ramas históricas. Mantener índices, unicidades, FK protegidas y barreras de escritura pública, también managers inversos y variantes asíncronas.

Todos los folios existentes En espera o Llamado conservan estado, responsable y llegada; `inicio_atencion` queda NULL. Los eventos previos conservan íntegramente sus datos y `oficina_contexto` queda NULL. Los comprobantes anteriores conservan claves, resultados, fechas y referencias; `folio_objetivo` queda NULL, incluido LLAMAR, cuyo resultado no se convierte en argumento objetivo.

La revisión posterior incluirá operaciones y SQL de la migración, validez de restricciones, conservación de datos y compatibilidad de reintentos. No se planifica un retroceso que elimine evidencia de inicios ya registrados: una reversión tras usar el nuevo estado requerirá evaluación específica de preservación, sin borrar o convertir datos para hacerla pasar.

## Pruebas previstas, todavía no implementadas ni ejecutadas

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

## Integración posterior en Atención actual

Añadir POST `/operacion/iniciar/`, protegido por rol OPERADOR, CSRF y `never_cache`, que delegue exclusivamente en el servicio con `request.user`. Mantener GET `/operacion/actual/` sin selección por UUID ni escrituras.

El botón **Iniciar atención** aparecerá para el folio Llamado propio cuando no haya pausa. En pausa se ofrecerá reanudar y se explicará que iniciar requiere otra acción explícita; no habrá envío encadenado. En atención se mostrará el estado y la fecha de inicio, ampliando únicamente la proyección propia del lector 011. No se exigen asignaciones activas para habilitar el botón; el servicio revalida las condiciones al recibir el POST.

La intención firmada de INICIAR incluirá actor, operación, solicitud UUID, folio UUID concreto y destino cerrado. No se admitirán campos POST alternativos para sustituirlos. Se conservarán el salt y la estructura válidos de los tokens existentes de LLAMAR, PAUSAR y REANUDAR mediante validación específica por operación; no se les exigirá el nuevo campo. No se añadirá caducidad funcional que invalide comprobantes antiguos.

Mantener POST → redirección → GET a Atención actual y resultados históricos diferenciados. Un error conserva token y clave; un 503 invita a repetir la misma petición sin afirmar si hubo commit. No se reenvía una petición de inicio ni se reemplaza su clave automáticamente al reanudar o ante un error. Cada formulario nuevo de inicio genera otra clave, pero su envío requiere la acción explícita del operador. Tras EN_PAUSA, ese formulario permite expresar otra intención después de reanudar. La pantalla y el servicio no sustituyen nunca el folio objetivo de una intención antigua. Las discrepancias entre lecturas de disponibilidad y detalle invitan a actualizar, sin prometer aceptación del POST.

Se reutilizarán formularios HTML y ayuda JavaScript opcional de 012, sin reintentos automáticos. La interfaz no incorporará otras acciones ni expondrá datos adicionales de pausas.

## Estado documental y conservación de DEMO

Esta entrega modifica únicamente acuerdos, esta decisión y la referencia breve de README. No modifica código, modelos, pruebas ni migraciones; no ejecuta comandos de Django, pruebas u operaciones de base de datos. **Implementación, migración, pruebas y botón permanecen pendientes.** No quedan decisiones funcionales pendientes para este inicio dentro del alcance descrito; las demás acciones conservan sus pendientes previos.

El estado vigente de DEMO procede de la comprobación manual del [registro 018](../pruebas/018-comprobacion-manual-operador.md): folio Llamado a cargo de `operador_demo`, otro pendiente y las pausas de esa sesión. Se conserva sin inspección nueva de base ni restauración de respaldos anteriores. Antes de una futura validación deberá preservarse nuevamente ese estado o utilizarse otra base aislada que no lo altere; esta decisión no autoriza limpieza ni recuperación de un estado anterior.
