# 010 — Primera pantalla funcional de Recepción

- Fecha: 12 de octubre de 2026.
- Estado: alcance aprobado por el usuario, implementado y comprobado en pruebas aisladas; revisión interactiva manual pendiente.
- Evidencia: [registro 012](../pruebas/012-nueva-atencion-recepcion-postgresql.md).

## Autoridad y alcance aprobado

Los [acuerdos vigentes](../acuerdos-vigentes.md), «Recepción y registro», «Roles y acceso» y «Oficinas, trámites y asignaciones», son la autoridad funcional. Se reutilizan la separación de roles de la decisión 001, los catálogos de la 002, las barreras y transacciones de la 003, el registro sin operador de la 004 y el servicio implementado en la [005](005-registro-inicial-de-folios.md). La [009](009-inicio-de-sesion-y-acceso-por-rol.md) aporta acceso, autorización vigente y logout POST con CSRF.

El usuario aprobó convertir `/recepcion/` en Nueva atención, con selección manual y confirmación propia. No se modifican modelos, servicios de negocio, barreras de escritura ni migraciones. No se exige asignación de operadores. La cuenta, la llegada, el UUID, el estado En espera y el operador vacío proceden del servidor.

## Rutas y autorización

| Ruta | Método y comportamiento |
| --- | --- |
| `/recepcion/` | GET muestra Nueva atención. POST `cargar_tramites` valida solo oficina y conserva la captura; POST `registrar` valida y llama al servicio. |
| `/recepcion/tramites/?oficina=…` | GET devuelve identificadores y nombres de trámites habilitados de la oficina elegida; oficina inválida o no disponible devuelve 400. |
| `/recepcion/confirmacion/<uuid>/` | GET muestra exclusivamente un registro realizado por la cuenta conectada. Otra cuenta de Recepción o registro inexistente: 404. |
| `/salir/` | Se conserva el logout existente, exclusivamente POST con CSRF. |

Las tres rutas nuevas o adaptadas usan `requiere_rol(RECEPCION)`: autenticación, cuenta activa y rol vigente, sin permisos derivados de flags técnicos o datos de sesión. Anónimos son redirigidos al acceso; otro rol recibe 403. Las respuestas privadas conservan `never_cache`. La escritura vuelve a autorizar bajo bloqueo dentro de `registrar_folio`, incluso si la cuenta cambia después de comprobar la vista.

## Captura y catálogos dependientes

Nombre completo obligatorio y con contenido; correo opcional, válido y de hasta 254 caracteres si se proporciona; teléfono opcional como texto libre. El formulario conserva la grafía capturada, sin imponer un formato telefónico. Los opcionales omitidos llegan al servicio como cadenas vacías.

Se ofrecen oficinas activas con al menos un trámite activo. El selector de trámite y la consulta JSON filtran por oficina elegida, oficina activa y trámite activo. No hay elección automática. Un catálogo vacío informa que no hay opciones y deshabilita visualmente el registro; el servidor sigue validando cualquier POST.

Sin JavaScript, Cargar trámites usa POST con CSRF y `formnovalidate`. Valida exclusivamente oficina mediante un formulario separado; reconstruye el formulario completo con los valores iniciales recibidos, sin validar todavía nombre o contactos ni crear filas. Al cambiar oficina, un trámite anterior ajeno deja de aparecer como opción.

Con JavaScript, cambiar oficina vacía la selección anterior y solicita sus trámites. Se cancela la petición anterior y se compara una revisión incremental para descartar respuestas atrasadas incluso si llegan después de cancelar. Los nombres se insertan como texto mediante `Option`. Un fallo de red, una respuesta no satisfactoria o HTML de una sesión vencida orientan a usar Cargar trámites, que permanece disponible.

## Registro, errores y confirmación

El POST de registro llama exclusivamente a `registrar_folio` con el actor autenticado y los campos admitidos. Conserva relecturas, bloqueos y el guardado conjunto de folio y evento CREACION. Los campos reservados del servidor enviados por el cliente no se transmiten al servicio. Un rechazo de autorización sigue siendo 403; los `ValidationError` se muestran junto al campo y en un resumen, incluyendo cambios de catálogo posteriores a la validación del formulario. La captura se conserva.

Después del éxito se redirige a la confirmación GET. Muestra ciudadano, oficina, trámite, llegada con zona horaria, estado En espera y responsable del registro, y permite Registrar otra atención. El UUID permanece como clave interna y parámetro de ruta; no se muestra como numeración pública aprobada. No se añade un detalle general ni acciones posteriores. La desactivación posterior del catálogo no impide consultar el comprobante propio.

## Recarga y límite aprobado de duplicados

Recargar la confirmación GET no vuelve a registrar. El botón Registrar atención se deshabilita durante un envío con JavaScript, preservando la acción del POST en un campo oculto; al volver mediante el navegador se restaura. Esta ayuda visual no garantiza un único envío.

**Dos POST válidos crean registros independientes**, aun con los mismos datos del ciudadano. Se aprobó conservar ese comportamiento en esta entrega: no se deduplica por nombre, correo o teléfono, no se reutilizan comprobantes de solicitudes de operadores y no se implementa idempotencia durable para el registro. Un reintento tras perder la respuesta puede crear otra atención. Una garantía durable requeriría un diseño posterior y su verificación transaccional.

## Referencia visual y accesibilidad

Se inspeccionó `/home/lenin/Descargas/FigmaW/nueva-atencion-tinto-v1.svg`, 1440 × 1024, titulado «Nueva atención — propuesta visual institucional». Es referencia de barra lateral, jerarquía, tarjetas y separación entre datos y destino. **No se atribuye aprobación a esa versión concreta**; la paleta `#521F30`, `#70283E` y `#F5F4F2` está respaldada por los acuerdos. No se copia el SVG al repositorio ni se incorporan sus menús de acciones pendientes.

Plantillas Django, CSS local y JavaScript opcional; etiquetas visibles, controles nativos, foco visible, enlace para saltar al contenido, errores asociados a campos y mensajes de carga anunciables. En móvil se apilan barra, campos y acciones. Las capturas revisadas solo acreditan el alcance descrito en el registro 012, sin sustituir la prueba interactiva ni el lector de pantalla.

## Archivos y pendientes

Se añaden `folios/forms.py`, `views.py`, `test_recepcion.py`, tres plantillas en `templates/recepcion/`, `static/css/recepcion.css`, `static/js/recepcion.js` y sus pruebas `recepcion.test.cjs`. Se conectan las rutas en `usuarios/urls.py`, se retira el destino mínimo anterior de `usuarios/views.py` y se adapta una prueba de acceso a Nueva atención. README y registro 012 documentan alcance y preparación.

Pendientes: revisión interactiva en Linux Mint con Brave, flujo con JavaScript deshabilitado en navegador, teclado y foco en la nueva pantalla, lector de pantalla, comportamiento visual de errores y confirmación real. Para ello se necesitan una cuenta activa RECEPCION con contraseña utilizable y oficina/trámite activos en un entorno autorizado; no se prepararon datos manuales ni se inspeccionó la base normal.

El formato público del folio sigue pendiente. Listados, detalle completo, Status, edición, traslados, cierres, llamado, reserva y demás acciones no forman parte de esta entrega.
