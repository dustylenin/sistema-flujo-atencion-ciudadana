# 012 — Primera integración funcional de pantallas de Operador

Fecha de aprobación del alcance: **14 de octubre de 2026**.

Estado actualizado al **14 de octubre de 2026**: **integración implementada y verificada en PostgreSQL aislado; comprobación visual pendiente; DEMO recuperado**. El [registro 017](../pruebas/017-pantallas-operador-postgresql.md) documenta resultados, ajuste de la prueba de acceso y recuperación.

## Autoridad y alcance

El usuario aprobó implementar la propuesta de integración de las dos pantallas con los [acuerdos vigentes](../acuerdos-vigentes.md) y las decisiones [004](004-cola-y-responsabilidad-de-folios.md), [006](006-disponibilidad-y-folio-actual-del-operador.md), [007](007-diseno-pausas-y-disponibilidad.md), [008](008-diseno-llamado-y-reserva.md), [009](009-inicio-de-sesion-y-acceso-por-rol.md) y [011](011-lecturas-autorizadas-de-operador.md). Se conservan los patrones de Recepción de la [010](010-nueva-atencion-recepcion.md).

Se preparan únicamente Cola de atención, Atención actual y las acciones de llamar siguiente, pausar y reanudar. No cambian contratos de servicios, modelos, permisos, barreras ni migraciones. No se incorporan inicio, notas, finalización, denegación, historial, filtros ni selección de oficina o ciudadano para llamar.

La evidencia anterior de los servicios y lectores está en el [registro 016](../pruebas/016-lecturas-operador-postgresql.md): 31 pruebas nuevas incluidas en la regresión de 273 Django y 4 JavaScript. Esos resultados no validaban estas pantallas: su verificación propia y posterior está en 017.

## Rutas, autorización y datos

| Ruta | Método | Función |
| --- | --- | --- |
| `/operacion/` | GET | Cola de atención; conserva el destino de login y el nombre `usuarios:operacion`. |
| `/operacion/actual/` | GET | Folio actual propio, sin recibir un UUID de folio. |
| `/operacion/llamar/` | POST | `llamar_siguiente`, sin oficina, ciudadano ni operador destino. |
| `/operacion/pausar/` | POST | `pausar_operador` con motivo obligatorio. |
| `/operacion/reanudar/` | POST | `reanudar_operador` sobre la pausa concreta del formulario. |

Solo Cola de atención y Atención actual aparecen como entradas de navegación. Cerrar sesión conserva su formulario POST existente. Las páginas rechazan POST; las acciones rechazan GET y otros métodos. Todas usan `requiere_rol(OPERADOR)` y `never_cache`, con autenticación y cuenta/rol vigentes por el acceso existente. Los flags técnicos no sustituyen el rol. Los servicios vuelven a comprobar autorización con la base al ejecutarse; las lecturas y escrituras reciben exclusivamente `request.user`.

Cola usa `consultar_pendientes_operador`: hasta 50 ciudadanos, oficina, trámite, llegada original con fecha/zona y estado En espera. La continuación utiliza su cursor validado; se ofrecen Siguiente página, Volver al inicio y Actualizar cola. No se muestran un total global, posiciones globales ni una numeración pública inventada. Un cursor inválido devuelve 400 con un enlace para volver al inicio. Catálogos desactivados no ocultan pendientes si existe asignación activa.

Atención actual usa `consultar_folio_actual_operador`, global sobre el propio responsable, independiente de actividad de catálogos o asignaciones posteriores. Muestra ciudadano, oficina, trámite, llegada, estado y responsable propio. No recibe un folio u operador destino ni amplía la proyección con contactos, notas o fechas no disponibles.

Ambas páginas usan `consultar_disponibilidad(actor=request.user, operador_id=request.user.pk)` sin cambiar el contrato. Libre ofrece solicitar el llamado y pausar; Ocupado conserva el folio y permite pausar; En pausa ofrece reanudar y conserva el folio si existe. Los vacíos de cola y folio son explícitos; acceder sin asignaciones no concede capacidad de llamado. La presentación de pausa es genérica y no muestra motivo histórico, inicio o duración, que este lector no expone.

Las lecturas pueden observar instantes diferentes. Si las referencias de folio de disponibilidad y detalle discrepan, se invita a actualizar y se deshabilita visualmente el llamado. **La pantalla no garantiza que una acción vaya a ser aceptada**: incluso un formulario mostrado como habilitado se evalúa con los servicios de escritura vigentes. Llamar desde otra página de la cola sigue seleccionando el primero global. No se habilita EN_ATENCION ni se incorpora una operación de cierre para liberar al responsable en esta entrega.

## Formularios e idempotencia

Los formularios contienen un token firmado, no cifrado, con `actor_id`, `operacion`, `solicitud_id` UUID, un destino de retorno cerrado y `pausa_id` cuando corresponde. La firma usa un ámbito específico de esta interfaz. No incluye datos personales del ciudadano, motivo de pausa ni permisos. El POST valida firma, estructura, tipos, cuenta, operación, UUID y destino. La pausa objetivo debe ser un entero positivo solo para REANUDAR. Tokens inválidos, ajenos o destinados a otra operación producen 400 sin invocar la escritura.

Cada formulario nuevo genera una clave distinta, respetando el ámbito compartido `(operador, solicitud_id)` de los comprobantes. Los formularios enlazados a un POST no generan claves. No se añade vencimiento funcional al token: formularios antiguos siguen sujetos a CSRF, autenticación, firma y revalidación del servicio, sin ampliar permisos. Una intención no procesada se evalúa contra el estado actual; una ya confirmada conserva su resultado original.

- Doble envío o respuesta perdida: misma clave y argumentos, devolviendo el comprobante original sin repetir la transición.
- Reutilización con otros argumentos: se muestra el `ValidationError` del servicio, sin crear una clave de reemplazo.
- Motivo: obligatorio y con contenido; `strip=False` conserva exactamente el texto enviado, incluidas las separaciones iniciales/finales, conforme a la comparación de comprobantes existente.
- Reanudar: conserva la pausa firmada. Un campo POST adicional no la sustituye; reintentar una pausa antigua no cierra una posterior. El servicio también rechaza pausas ajenas.
- Otra intención deliberada: nace de un formulario nuevo obtenido al volver a una de las páginas; no hay reintentos automáticos con claves nuevas.

Los campos POST adicionales no se transmiten como selección, clave alternativa, operador, pausa o destino. Se utiliza exclusivamente la intención validada y los argumentos admitidos del formulario. La firma es una protección de interfaz, no sustituye las comprobaciones transaccionales ni concede acceso por sí sola.

## Respuestas, mensajes y errores

Las acciones usan POST con CSRF y las respuestas confirmadas siguen POST → redirección → GET. Un llamado confirmado redirige a Atención actual; los otros resultados vuelven al destino firmado, limitado a `usuarios:operacion` o `usuarios:operador_actual`. No se usan `next`, destinos POST libres ni Referer para redirigir.

Los mensajes distinguen cada resultado nuevo, incluidos los que no cambian el estado (`EN_PAUSA`, `OCUPADO`, `SIN_ASIGNACIONES`, `SIN_PENDIENTES`, `YA_EN_PAUSA`, `YA_REANUDADA`). Una repetición informa **Solicitud ya procesada**, **Resultado original** y **No se ejecutó otra transición**, sin presentarlo como disponibilidad actual. Se sustituyen los mensajes anteriores de acciones de Operador para que un doble POST antes de seguir la redirección no acumule una afirmación de transición nueva; se mantienen mensajes de otras funciones.

Los formularios inválidos y los `ValidationError` del servicio se muestran con estado 400 en una plantilla de revisión que conserva el token y el motivo, sin generar claves ni releer negocio. Con una intención inválida no se ofrece reenviarla: se enlaza a una página permitida. Un `DatabaseError` devuelve 503 con el mismo formulario y orientación a reintentarlo sin cambiar datos, compatible con una respuesta perdida después de confirmar. No se afirma que ese error demuestre rollback. `PermissionDenied` conserva el 403 y CSRF su rechazo estándar.

## Diseño y accesibilidad

Se conservan la paleta institucional `#521F30`, `#70283E`, `#F5F4F2`, las tarjetas, la identidad SF y la estructura de Recepción. Se revisó el contenido de los SVG locales de 1440 × 1024 en `/home/lenin/Descargas/FigmaW/`:

- `cola-operador-pendientes-tinto-v1.svg`.
- `folio-llamado-tinto-v1.svg`.
- `atencion-actual-tinto-v1.svg`.
- `pausa-operador-tinto-v1.svg`.
- `operador-en-pausa-tinto-v1.svg`.

Son referencias dentro del alcance: no se copian al repositorio ni se incorporan sus controles de funciones pendientes, contactos o métricas ausentes de los lectores actuales. La aprobación de la paleta y estructura procede de los acuerdos; no se atribuye una aprobación adicional a cada versión concreta de SVG.

La navegación, la paginación, los tres formularios y la pausa mediante `details/summary` funcionan con HTML nativo. Hay etiquetas visibles, identificadores únicos por operación, errores asociados a campos, resumen de errores con enlaces, mensajes anunciables, foco visible, enlace para saltar al contenido y orden natural con Tab. En móvil se apilan acciones y tarjetas; la tabla conserva encabezados y una región desplazable con teclado.

JavaScript es opcional: evita visualmente un segundo envío del mismo formulario, marca el envío, restaura el botón al volver y enfoca mensajes o errores. No cambia tokens, claves, motivos o destinos ni ejecuta peticiones o reintentos. La garantía de idempotencia sigue perteneciendo a los comprobantes de los servicios.

## Archivos y validación posterior

| Archivos | Alcance implementado |
| --- | --- |
| `folios/forms_operador.py` | Intenciones firmadas y formularios de las tres acciones. |
| `folios/views_operador.py` | GET de las dos páginas, POST delegados, errores, mensajes y redirecciones. |
| `usuarios/urls.py`, `usuarios/views.py` | Rutas de Operador y retirada del destino mínimo anterior. |
| `templates/operador/` | Base, cola, actual, revisión de solicitud y parciales de formularios/disponibilidad. |
| `static/css/operador.css` | Complemento adaptable sobre los estilos existentes de Recepción. |
| `static/js/operador.js`, `operador.test.cjs` | Ayuda opcional y cuatro pruebas verificadas. |
| `folios/test_operador.py` | 35 pruebas HTTP verificadas, con aislamiento PostgreSQL existente. |
| `usuarios/test_acceso.py` | Expectativas reforzadas sobre la nueva cola y `no-store`, manteniendo los rechazos entre roles. |
| README y esta decisión | Estado y alcance, separados de las evidencias anteriores. |

Las pruebas HTTP verificaron CSRF real, sesiones y roles vigentes, flags técnicos, métodos/cache, tokens manipulados o ajenos, destinos cerrados, formulario inválido, conservación del motivo, doble envío, mensajes históricos, respuesta perdida, reanudación antigua, resultados sin transición y folios ajenos. También cubrieron paginación, lectura sin escrituras de negocio, catálogos desactivados, folio propio sin asignaciones y controles HTML sin JavaScript. Las regresiones existentes de acceso y Recepción se incluyeron en la pasada final de 308 pruebas Django.

La preparación inicial se limitó a verificaciones sin conexión: sintaxis, importaciones, resolución de rutas, compilación y renderizado en memoria de plantillas y revisión del diff; entonces no se ejecutaron suites ni se conectaron bases. La validación posterior conservó DEMO conforme a los registros [014](../pruebas/014-validacion-llamado-y-reserva-postgresql.md) y [016](../pruebas/016-lecturas-operador-postgresql.md), con un respaldo completo nuevo y privado, manifiesto y recuperación revisados antes del runner.

Las verificaciones iniciales de sintaxis, importaciones, cinco rutas, seis plantillas e identificadores HTML fueron correctas, con conexiones bloqueadas. Esa evidencia se conserva separada de las pruebas posteriores y no constituye revisión visual.

Pasaron **35 pruebas HTTP nuevas**, **4 JavaScript de Operador** y **4 JavaScript existentes de Recepción**. La primera regresión completa ejecutó 308 casos y detectó dos subfallos de un caso de acceso ampliado: intentaba autenticar al operador con una sesión de Recepción ya abierta. El servidor devolvía correctamente 403. Se corrigió el fixture para usar un cliente nuevo y comprobar su ingreso; no se relajaron permisos ni expectativas de rechazo. Pasó el caso corregido y después la **regresión completa de 308 pruebas Django, incluidas las 35 nuevas**. No se encontraron defectos que exigieran cambios a la lógica de pantallas, formularios o servicios. Los detalles y ejecuciones están en 017.

DEMO se recuperó tras ambos ciclos, incluido el fallido, y se verificó finalmente en una conexión independiente de solo lectura: 17 tablas de datos idénticas al manifiesto, próximas asignaciones originales de 15 secuencias, esquema conservado y 23 migraciones sin pendientes. La prueba existente de migración reaplicó 0003 en cada regresión; la recuperación conservó el historial resultante y su secuencia, sin cargar el historial antiguo. `check` y correspondencia modelos/migraciones fueron correctos. No se conectó la base normal ni se añadieron funcionalidades, modelos o migraciones. Antes de otro runner debe repetirse la preservación de DEMO.

La comprobación visual e interactiva en escritorio y móvil, con teclado, foco, errores y JavaScript deshabilitado queda pendiente. No se identifican decisiones funcionales nuevas que bloqueen esta integración. Se conservan fuera de alcance las funciones y decisiones pendientes de 011. Esta etapa termina sin commit ni push.
