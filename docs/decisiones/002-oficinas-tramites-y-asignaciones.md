# 002 — Oficinas, trámites y asignaciones de operadores

Fecha: 8 de octubre de 2026.

Estado: propuesta revisada, pendiente de implementación.

## Autoridad y alcance

Los [acuerdos vigentes](../acuerdos-vigentes.md) son la autoridad de las reglas de negocio y prevalecen sobre este documento. La [decisión 001](001-usuarios-y-asignaciones.md) establece el usuario personalizado, la separación de roles funcionales y la relación muchos a muchos entre operadores y oficinas.

Este documento registra la propuesta técnica revisada para representar esos acuerdos. La distribución entre aplicaciones, los campos, las restricciones y la organización de las validaciones son propuestas de implementación; no añaden reglas de negocio.

Actualmente existe `usuarios.Usuario`, basado en `AbstractUser`, con su migración y [validación en PostgreSQL documentadas](../pruebas/001-usuarios-postgresql.md). Todavía no existen los modelos de oficinas, trámites, asignaciones ni folios. El guardado actual de `Usuario` valida el valor del rol, pero no implementa los bloqueos por asignaciones o folios.

## Aplicaciones y modelos propuestos

- `usuarios`, existente: cuentas, rol y estado de actividad.
- `oficinas`, propuesta: catálogo de oficinas y asignaciones de operadores.
- `tramites`, propuesta: catálogo de trámites y pertenencia a una oficina.

| Modelo | Campos mínimos propuestos | Relaciones |
| --- | --- | --- |
| `Oficina` | `id` como clave primaria, `nombre` de texto, `activo` booleano. | Tiene varios trámites y varias asignaciones. |
| `Tramite` | `id` como clave primaria, `nombre` de texto, `activo` booleano, `oficina` obligatoria. | Clave foránea a una sola `Oficina`. |
| `AsignacionOperadorOficina` | `id` como clave primaria, `operador` obligatorio, `oficina` obligatoria, `activo` booleano. | Claves foráneas a `settings.AUTH_USER_MODEL` y a `Oficina`. |

`AsignacionOperadorOficina` representa la relación muchos a muchos: varias oficinas por operador y varios operadores por oficina. No se impondrá unicidad sobre el operador o la oficina individualmente ni un límite de un operador activo por oficina.

## Restricciones de unicidad propuestas

Se proponen restricciones en PostgreSQL, expresadas mediante `UniqueConstraint` de Django:

- `Oficina`: unicidad global sobre `Lower(Trim(nombre))`.
- `Tramite`: unicidad sobre la combinación de `oficina` y `Lower(Trim(nombre))`; el nombre puede repetirse en otra oficina.
- `AsignacionOperadorOficina`: unicidad sobre `(operador, oficina)`.

Todas incluyen registros activos e inactivos, sin condición sobre `activo`. La pareja operador/oficina no se puede duplicar para sustituir una asignación desactivada: se reactiva el registro existente.

La expresión de comparación de nombres representa únicamente la equivalencia aprobada entre mayúsculas y minúsculas y la eliminación de espacios exteriores para comparar. No propone cambios en el nombre almacenado ni reglas adicionales sobre acentos, espacios internos o edición de nombres. La implementación deberá verificar que las expresiones y la configuración de comparación de PostgreSQL reproduzcan los acuerdos.

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

Una vez implementadas y aplicadas las restricciones propuestas, PostgreSQL garantizará la existencia de las entidades referenciadas mediante claves foráneas, la obligatoriedad mediante `NOT NULL` y las tres unicidades descritas. Estas restricciones también rechazarán datos incompatibles cuando una escritura omita las validaciones de la aplicación.

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

1. Implementar los catálogos de oficinas y trámites, sus relaciones y restricciones. Verificar unicidad global y por oficina, incluyendo inactivos y variantes de mayúsculas y espacios exteriores; conservación al desactivar y reactivar; rechazo de borrado físico y de cambio de oficina por las vías de escritura soportadas. Documentar los límites ante escrituras directas.
2. Implementar asignaciones y sus operaciones de creación y reactivación. Verificar varias oficinas por operador, varios operadores por oficina, rechazo de parejas duplicadas, condiciones de rol y actividad, reutilización del mismo registro y conservación de asignaciones históricas inactivas de cuentas que cambiaron de rol legítimamente. Mantener sin habilitar las operaciones dependientes de folios.
3. Implementar los folios, su oficina, operador asignado, estado e historial, así como las operaciones acordadas necesarias para resolverlos. Verificar nuevos registros solo con oficina y trámite activos y la posibilidad de terminar pendientes en una oficina inactiva.
4. Completar y verificar los bloqueos de retirada de asignaciones y cambio de rol. Probar folios asignados sin finalizar, folios finalizados, cola sin operador asignado, alcance por oficina frente al alcance de toda la cuenta y operaciones concurrentes. Habilitar esas operaciones únicamente después de comprobar sus protecciones y la conservación del historial.

Estas verificaciones son trabajo futuro; este documento no afirma resultados ni añade una suite de pruebas. Su registro no implementa modelos, permisos, servicios o pantallas, ni genera o aplica migraciones.
