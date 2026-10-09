# 002 — Oficinas, trámites y asignaciones de operadores

Fecha: 8 de octubre de 2026.

Estado: base de oficinas y trámites implementada y verificada en PostgreSQL de pruebas; migraciones del proyecto, asignaciones, folios y protecciones dependientes pendientes.

## Autoridad y alcance

Los [acuerdos vigentes](../acuerdos-vigentes.md) son la autoridad de las reglas de negocio y prevalecen sobre este documento. La [decisión 001](001-usuarios-y-asignaciones.md) establece el usuario personalizado, la separación de roles funcionales y la relación muchos a muchos entre operadores y oficinas.

Este documento registra el diseño técnico revisado para representar esos acuerdos y distingue la base de catálogos implementada de las partes todavía propuestas. La distribución entre aplicaciones, los campos, las restricciones y la organización de las validaciones no añaden reglas de negocio.

Actualmente existen `usuarios.Usuario`, basado en `AbstractUser`, con su migración y [validación en PostgreSQL documentadas](../pruebas/001-usuarios-postgresql.md), y los modelos `Oficina` y `Tramite`. Todavía no existen los modelos de asignaciones ni folios. El guardado actual de `Usuario` valida el valor del rol, pero no implementa los bloqueos por asignaciones o folios.

## Etapa implementada y verificada

La base de oficinas y trámites está registrada en `INSTALLED_APPS`: identificadores, nombres obligatorios, estado `activo` y relación obligatoria del trámite con una oficina mediante `PROTECT`. Incluye unicidad global de oficinas y por oficina de trámites sobre `Lower(Trim(nombre))`, incluyendo inactivos, y restricciones de contenido del nombre. El guardado valida nombre y estado, impide cambiar la oficina del trámite y evita sobrescribir una PK creada después de una consulta sin resultado. Se bloquea el borrado individual y por `QuerySet`; `bulk_create()` y `bulk_update()` no están admitidos y `update()` solo acepta un booleano literal para `activo`, con los mismos bloqueos en sus variantes asíncronas.

La suite terminó con **37 pruebas satisfactorias: 19 con PostgreSQL y 18 sin base**, incluida una regresión con dos conexiones reales. Se utilizó exclusivamente `test_atencion_catalogos_revision` con `atencion_test`. `MIGRATE=False` preparó el esquema desde los modelos: se verificaron modelos y restricciones en esa base, **no archivos de migración**. Las migraciones de oficinas y trámites para la base del proyecto todavía no se han generado ni aplicado. Los casos y resultados están en el [registro de validación](../pruebas/002-oficinas-tramites-postgresql.md).

Estas protecciones cubren las vías públicas admitidas de la aplicación; SQL directo, APIs internas y deserializadores pueden omitirlas. No hay disparadores SQL aprobados ni historial de actividad implementado. El booleano `activo` conserva el estado sin provocar cambios automáticos en otras entidades. Asignaciones, folios, pantallas y permisos funcionales siguen pendientes; las reglas que dependen de ellos no se presentan como implementadas.

## Aplicaciones y modelos

- `usuarios`, existente: cuentas, rol y estado de actividad.
- `oficinas`, existente: catálogo de oficinas implementado; asignaciones de operadores pendientes.
- `tramites`, existente: catálogo de trámites y pertenencia a una oficina implementados.

| Modelo | Campos mínimos | Relaciones y estado |
| --- | --- | --- |
| `Oficina` | `id` como clave primaria, `nombre` de texto, `activo` booleano. | Implementado: varios trámites. Las asignaciones siguen propuestas. |
| `Tramite` | `id` como clave primaria, `nombre` de texto, `activo` booleano, `oficina` obligatoria. | Implementado: clave foránea a una sola `Oficina`. |
| `AsignacionOperadorOficina` | `id` como clave primaria, `operador` obligatorio, `oficina` obligatoria, `activo` booleano. | Propuesto, pendiente: claves foráneas a `settings.AUTH_USER_MODEL` y a `Oficina`. |

`AsignacionOperadorOficina` representa la relación muchos a muchos: varias oficinas por operador y varios operadores por oficina. No se impondrá unicidad sobre el operador o la oficina individualmente ni un límite de un operador activo por oficina.

## Restricciones de unicidad

Las restricciones se expresan mediante `UniqueConstraint` de Django. Las de oficinas y trámites están implementadas y verificadas en la base exclusiva de pruebas; la de asignaciones sigue propuesta:

- `Oficina`: unicidad global sobre `Lower(Trim(nombre))`.
- `Tramite`: unicidad sobre la combinación de `oficina` y `Lower(Trim(nombre))`; el nombre puede repetirse en otra oficina.
- `AsignacionOperadorOficina`: unicidad sobre `(operador, oficina)`.

Todas incluyen registros activos e inactivos, sin condición sobre `activo`. La pareja operador/oficina no se puede duplicar para sustituir una asignación desactivada: se reactiva el registro existente.

La expresión de comparación de nombres representa únicamente la equivalencia aprobada entre mayúsculas y minúsculas y la eliminación de espacios exteriores para comparar. No propone cambios en el nombre almacenado ni reglas adicionales sobre acentos, espacios internos o edición de nombres. Se verificaron en PostgreSQL las variantes de nombres de los casos registrados; no se extiende ese resultado a reglas de comparación no aprobadas.

## Conservación y ciclo de vida

- Las oficinas y los trámites no se eliminan físicamente. Su desactivación y reactivación conservan los mismos registros y sus referencias históricas.
- Una oficina inactiva impide nuevos registros, pero permite terminar sus folios pendientes. Puede reactivarse.
- Un trámite inactivo deja de estar disponible para nuevos registros. El administrador puede reactivarlo conservando el mismo registro y su historial. Para admitir nuevos registros, el trámite y su oficina deben estar activos.
- La oficina de un trámite queda fija desde su creación. Si se ofrece en otra oficina, se crea otro registro asociado a ella; el anterior se desactiva cuando deje de ofrecerse en su oficina original, conservando su historial.
- Retirar una oficina a un operador desactiva su asignación, sin eliminarla. Su reactivación utiliza el mismo registro y conserva el historial de las atenciones anteriores.

Se propone conservar las relaciones sin borrados en cascada. El registro de actividad deberá recoger los cambios y sus responsables conforme a los acuerdos; el campo `activo` por sí solo no constituye ese historial.

No se derivan efectos automáticos sobre las asignaciones al desactivar o reactivar cuentas u oficinas. Tampoco se propone finalización o reasignación automática de folios.

## Validaciones según la operación

| Operación | Validación requerida por los acuerdos |
| --- | --- |
| Crear una asignación. | La cuenta destino tiene rol `OPERADOR`, está activa y la oficina está activa; no existe otra asignación de la misma pareja. |
| Reactivar una asignación. | Se utiliza el mismo registro; la cuenta tiene rol `OPERADOR` y tanto la cuenta como la oficina están activas. |
| Desactivar una asignación. | El operador no tiene folios asignados sin finalizar en esa oficina. Los folios en la cola sin operador asignado no bloquean. |
| Cambiar una cuenta de `OPERADOR` a otro rol. | No tiene asignaciones de oficinas activas ni folios asignados sin finalizar, considerando todas sus oficinas. Primero se resuelven los folios conforme a los acuerdos y se desactivan las asignaciones. Se conservan registros e historial. |
| Reactivar asignaciones después de que la cuenta vuelva a `OPERADOR`. | El administrador actúa sobre los mismos registros y se cumplen las condiciones de reactivación ya aprobadas. |
| Registrar una nueva atención. | Recepción selecciona manualmente oficina y después trámite; el servidor comprueba que el trámite pertenece a esa oficina y que ambos están activos. |

Una asignación histórica inactiva puede pertenecer a una cuenta que haya cambiado de rol conforme a los acuerdos. Su conservación no exige que el rol actual siga siendo `OPERADOR`. La clave foránea seguirá apuntando a `Usuario`; no se propone un filtro permanente por rol que impida consultar o conservar esas relaciones históricas.

Las condiciones de rol y actividad se comprueban al crear o reactivar una asignación; no son una orden de desactivación automática ante cambios en las entidades relacionadas.

La gestión administrativa requiere autenticación, cuenta administradora activa y rol funcional `ADMINISTRADOR`. `is_staff` e `is_superuser` son indicadores técnicos independientes y no sustituyen ese rol ni conceden por sí solos las funciones de la aplicación.

La reasignación de folios abiertos de operadores desactivados sigue exclusivamente los acuerdos existentes: operador destino activo de la misma oficina, motivo obligatorio y conservación de oficina, estado, notas, autores e historial. Esta propuesta no amplía esa regla.

## Garantías de PostgreSQL y responsabilidad de la aplicación

Las restricciones de oficinas y trámites están definidas en los modelos y preparadas en la base exclusiva de pruebas: clave foránea, obligatoriedad, contenido del nombre y unicidades de los catálogos. Su aplicación en la base del proyecto sigue pendiente de generar, revisar y aplicar migraciones. La unicidad de la pareja operador/oficina todavía es una propuesta sin implementar. Una vez aplicadas las restricciones correspondientes, PostgreSQL rechazará datos incompatibles incluso si una escritura omite las validaciones de la aplicación.

La aplicación deberá validar la autorización del actor, el rol y actividad del destinatario al crear o reactivar asignaciones, las transiciones de estado, la conservación del registro, la oficina inmutable del trámite y los bloqueos por folios. También deberá conservar el registro de actividad. Estas garantías no se obtienen únicamente con las claves foráneas y restricciones de unicidad propuestas.

Se propone centralizar las operaciones en servicios transaccionales, ejecutar las validaciones explícitamente y coordinar bloqueos de usuario, oficina y asignación entre las operaciones concurrentes relacionadas. Las futuras operaciones de asignación de folios y cambio de estado deberán participar en el mismo protocolo para evitar carreras entre comprobación y escritura.

`clean()` aislado no protege todas las escrituras: `save()` no ejecuta automáticamente `full_clean()`, y `update()`, `bulk_create()` o SQL directo pueden omitir las validaciones del modelo y los servicios. Un `CHECK` ordinario no garantiza condiciones sobre el rol o estado de otras tablas ni sobre los folios relacionados.

Las claves foráneas protectoras tampoco impiden por sí solas eliminar una oficina o un trámite sin referencias. Sin protección adicional en PostgreSQL, las escrituras directas podrían saltarse la prohibición de eliminación física, cambiar la oficina de un trámite o incumplir reglas entre tablas, aunque respeten las claves foráneas y unicidades.

Los disparadores SQL no forman parte de una decisión aprobada en esta propuesta. La necesidad y el mecanismo de una protección adicional frente a escrituras directas deberán evaluarse técnicamente antes de afirmar que PostgreSQL garantiza esas reglas. No se presentan como protecciones ya implementadas o verificadas.

## Dependencia pendiente de folios

Los bloqueos al desactivar asignaciones y al cambiar una cuenta de `OPERADOR` a otro rol están acordados, pero su implementación y verificación siguen pendientes porque los folios todavía no existen en el código.

**No se deben habilitar las operaciones que dependan de esos bloqueos hasta implementar y verificar las protecciones con folios reales.** No se sustituirán por consultas ficticias ni por comprobaciones que siempre indiquen ausencia de folios abiertos. Comprobar solo asignaciones activas no completa la protección del cambio de rol.

Esta dependencia no modifica las reglas de desactivación de cuentas ni la posibilidad de terminar pendientes en oficinas inactivas. No añade excepciones al bloqueo ni nuevas reglas de reasignación.

## Orden de implementación y verificaciones

1. Base de catálogos implementada y verificada en PostgreSQL de pruebas: unicidad global y por oficina, incluyendo inactivos y variantes de mayúsculas y espacios exteriores; conservación al desactivar y reactivar; rechazo de borrado físico y de cambio de oficina por las vías soportadas; límites ante escrituras directas documentados. Queda pendiente generar, revisar, verificar y aplicar las migraciones del proyecto antes de usar esos modelos en su base local.
2. Implementar asignaciones y sus operaciones de creación y reactivación. Verificar varias oficinas por operador, varios operadores por oficina, rechazo de parejas duplicadas, condiciones de rol y actividad, reutilización del mismo registro y conservación de asignaciones históricas inactivas de cuentas que cambiaron de rol legítimamente. Mantener sin habilitar las operaciones dependientes de folios.
3. Implementar los folios, su oficina, operador asignado, estado e historial, así como las operaciones acordadas necesarias para resolverlos. Verificar nuevos registros solo con oficina y trámite activos y la posibilidad de terminar pendientes en una oficina inactiva.
4. Completar y verificar los bloqueos de retirada de asignaciones y cambio de rol. Probar folios asignados sin finalizar, folios finalizados, cola sin operador asignado, alcance por oficina frente al alcance de toda la cuenta y operaciones concurrentes. Habilitar esas operaciones únicamente después de comprobar sus protecciones y la conservación del historial.

Las verificaciones de catálogos ya realizadas se detallan en el registro enlazado; las verificaciones de asignaciones, folios, permisos e historial siguen siendo trabajo futuro. Esta actualización documenta la etapa comprobada, sin cambiar los acuerdos ni implementar las partes pendientes, y no genera ni aplica migraciones.
