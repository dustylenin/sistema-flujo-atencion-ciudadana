# 003 — Servicios de asignación y registro de actividad

Fecha: 10 de octubre de 2026.

Estado: **diseño revisado; implementación y pruebas pendientes**.

## Autoridad y alcance

Los [acuerdos vigentes](../acuerdos-vigentes.md) prevalecen sobre este diseño. Se reutilizan el modelo, la multiplicidad, las reglas de ciclo de vida y la dependencia de folios de la [decisión 002](002-oficinas-tramites-y-asignaciones.md). Este documento concreta creación y reactivación de asignaciones y sus eventos durables; no añade reglas funcionales.

Todavía no existen estos modelos, servicios, eventos ni sus protecciones en el código. Las **42 pruebas anteriores** corresponden a usuarios, catálogos y configuración de migraciones, documentadas en el [registro 003 de pruebas](../pruebas/003-migraciones-postgresql.md); **no verifican este diseño**. La aplicación de las migraciones de catálogos a la base local se conserva en el [registro 004](../pruebas/004-migraciones-catalogos-local.md).

Retirada de asignaciones y cambio desde `OPERADOR` a otro rol seguirán sin habilitarse hasta implementar y verificar las comprobaciones completas con folios reales. Pantallas, asignaciones de folios y auditoría general quedan fuera del alcance inmediato.

## Modelos propuestos en oficinas

Ambos modelos se ubicarían en `oficinas/models.py`.

| Modelo | Campos y relaciones |
| --- | --- |
| `AsignacionOperadorOficina` | `id`, `operador` obligatorio hacia `settings.AUTH_USER_MODEL`, `oficina` obligatoria hacia `Oficina` y `activo` booleano obligatorio. Ambas claves foráneas con `PROTECT`. |
| `EventoAsignacion` | `id`, `asignacion` y `actor` obligatorios, ambos con `PROTECT`; el actor referencia `settings.AUTH_USER_MODEL`. `fecha` asignada por el servidor con zona horaria, `operacion`, `activo_anterior` y `activo_nuevo`. |

La asignación tiene `UniqueConstraint(operador, oficina)` sin condición sobre `activo`. Un operador puede tener varias oficinas y una oficina varios operadores; ninguno de los dos campos es único individualmente. La pareja de un registro existente es inmutable y su borrado público se rechaza. Reactivar reutiliza el mismo registro y su PK; no se crea una pareja duplicada para sustituir una asignación inactiva.

El evento admite únicamente `CREACION` y `REACTIVACION`. `activo_anterior` permite `NULL` solo para creación; `activo_nuevo` es obligatorio. Se propone una restricción de coherencia entre operación y estados:

| Operación | Estado anterior | Estado nuevo |
| --- | --- | --- |
| `CREACION` | `NULL`: no existía asignación. | `True`. |
| `REACTIVACION` | `False`. | `True`. |

Cada cambio efectivo inserta un evento nuevo, sin editar los anteriores. Las referencias protegidas, la pareja inmutable y la conservación de eventos mantienen el historial aunque se reutilice la misma asignación. Los eventos no admiten edición ni borrado por las vías públicas.

**Este registro cubre únicamente creación y reactivación de asignaciones; no es la auditoría completa del sistema.** No sustituye el futuro historial de folios ni el registro de otras acciones, retiradas o cambios de cuentas y catálogos.

## Servicios y autorización

En `oficinas/services.py` se proponen estas firmas:

```python
crear_asignacion(*, actor, operador_id, oficina_id) -> ResultadoAsignacion
reactivar_asignacion(*, actor, operador_id, oficina_id) -> ResultadoAsignacion
```

`actor` procede del contexto autenticado del servidor, no de un identificador libre enviado por el cliente. El servicio exige autenticación, vuelve a cargar y bloquea la cuenta del actor en la base y comprueba su estado actual: debe existir, tener `is_active=True` y rol funcional `ADMINISTRADOR`. Los valores de un objeto previamente cargado no sustituyen esa consulta. `is_staff` e `is_superuser` no conceden esta autorización ni permiten omitirla.

Para crear o reactivar efectivamente, se comprueba bajo bloqueo que la cuenta destino tiene rol `OPERADOR`, está activa y que la oficina está activa. Estas condiciones se aplican a la operación; no obligan a modificar registros históricos cuando una cuenta u oficina cambia de estado. Desactivar cuentas u oficinas no desactiva automáticamente asignaciones.

## Resultados explícitos y operaciones sin cambios

`ResultadoAsignacion` contendría `estado`, `asignacion_id` y `evento_id`, permitiendo identificadores ausentes cuando corresponda.

| Servicio y situación | Estado del resultado | Escrituras y evento |
| --- | --- | --- |
| Crear una pareja inexistente, cumpliendo requisitos. | `CREADA`. | Asignación activa nueva y evento `CREACION`. |
| Reactivar una pareja inactiva, cumpliendo requisitos. | `REACTIVADA`. | Misma asignación/PK activa y evento `REACTIVACION`. |
| Cualquiera de los servicios encuentra la pareja ya activa. | `YA_ACTIVA`. | Sin escrituras ni evento; se devuelve la PK existente. |
| Crear encuentra una pareja existente inactiva. | `REQUIERE_REACTIVACION`. | Sin escrituras ni evento; se devuelve la PK existente. |
| Reactivar no encuentra la pareja. | `ASIGNACION_INEXISTENTE`. | Sin escrituras ni evento; sin PK de asignación. |

Todos los resultados requieren autorización del actor. Los incumplimientos de autorización o de los requisitos para un cambio efectivo se rechazan explícitamente, sin persistir cambios. Una pareja activa no se duplica y no se registra una reactivación ficticia. **Las operaciones sin cambios no generan eventos** ni corrigen automáticamente el estado de la asignación o de sus referencias.

## Transacción, bloqueos y concurrencia

Cada servicio utiliza una sola `transaction.atomic()` y la misma conexión para autorización, lecturas de validación, asignación y evento. El orden común de bloqueos mediante `select_for_update()` será:

1. Cuentas del actor y del operador, por PK ascendente y sin duplicados.
2. Oficina.
3. Asignación existente de la pareja, si existe.

Después de adquirir cada bloqueo se utilizan los valores actuales de la base. Bloquear la cuenta del operador también serializa creaciones concurrentes de una pareja todavía inexistente; bloquear únicamente la asignación no cubriría ese caso. La restricción única sigue siendo la garantía final de que no haya dos registros de la pareja.

El cambio y el evento se guardan juntos: un error al insertar el evento revierte la creación o reactivación, y un error en la asignación impide guardar el evento. No se difiere el evento a `on_commit` ni a una tarea posterior. Si existe una transacción exterior, ambos cambios quedan sujetos al resultado de esa transacción.

Las operaciones relacionadas sobre rol o actividad de cuentas, estado de oficinas y asignaciones deberán compartir el orden y protocolo de bloqueos. Las futuras operaciones de asignación/finalización de folios, retirada y cambio de rol deberán incorporarse a ese protocolo antes de habilitarse, para evitar carreras entre comprobación y escritura. Bloquear filas solo en estos dos servicios no completa las futuras garantías entre entidades.

## Vías públicas de escritura y límites

Para asignaciones y eventos se propone rechazar la persistencia directa mediante `save`, `create`, `update`, `get_or_create`, `update_or_create`, `bulk_create`, `bulk_update` y borrado individual o por queryset. Los métodos mixtos se rechazan aunque pudieran limitarse a devolver un registro existente; las lecturas usarán métodos de lectura.

Se cubren también `asave`, `acreate`, `aupdate`, `aget_or_create`, `aupdate_or_create`, `abulk_create`, `abulk_update` y `adelete`. Managers por defecto, base e inversos compartirán las restricciones. No se heredará para asignaciones el permiso de los catálogos de ejecutar `update(activo=...)`, porque permitiría retirar o reactivar sin el servicio.

Los servicios utilizarán primitivas privadas de persistencia, específicas para cada transición y ejecutadas después de autorizar y validar dentro de la transacción. No habrá parámetros públicos para omitir validaciones ni un contexto amplio que permita escrituras arbitrarias. Si posteriormente se ofrecen servicios asíncronos, envolverán la operación síncrona completa, conservando autorización, bloqueos y atomicidad.

Estas protecciones cubren las vías públicas admitidas del ORM. **SQL directo, deserialización y APIs internas pueden omitirlas**; las restricciones de base garantizan referencias, unicidad y coherencia de estados del evento, pero no la autorización ni que toda escritura tenga evento. No se proponen disparadores ni se atribuye una garantía completa frente a esas vías.

## Bloqueos provisionales y reglas definitivas

La implementación inicial deberá rechazar la retirada, incluida cualquier escritura pública de `activo=False`, y el cambio efectivo desde `OPERADOR` hacia otro rol. La ausencia del modelo de folios no se tratará como ausencia comprobada de folios pendientes.

Actualmente `Usuario.save()` solo valida que el rol pertenezca a los valores admitidos. La protección propuesta deberá consultar y bloquear la fila existente y comparar el rol persistido con el que realmente se escribiría, incluso para instancias reconstruidas o con PK explícita. Se respetará `update_fields`: guardar únicamente contraseña o actividad no constituye un cambio de rol.

El queryset de usuarios rechazará `update(rol=...)`, `bulk_update` del rol y las inserciones masivas que puedan sobrescribirlo por conflicto. `create`, `get_or_create`, `update_or_create`, `create_user` y `create_superuser` deberán conservar la comprobación de la fila existente mediante `save`; también se cubrirán sus variantes asíncronas, incluidas las heredadas del manager. Los managers base y por defecto no podrán abrir una vía alternativa. Este diseño no habilita una nueva gestión funcional de cuentas.

| Operación | Bloqueo provisional | Regla definitiva pendiente de folios |
| --- | --- | --- |
| Retirar asignación. | Rechazo explícito; no se habilita la desactivación. | Bloquear si el operador tiene folios asignados sin finalizar en esa oficina. La cola sin operador asignado no bloquea. |
| Cambiar desde `OPERADOR` a otro rol. | Rechazo explícito, incluso si no hay asignaciones activas. | Bloquear si conserva asignaciones activas o folios asignados sin finalizar en cualquiera de sus oficinas. |

Una asignación histórica inactiva puede referenciar una cuenta cuyo rol actual sea distinto de `OPERADOR`. No se impone un filtro permanente por rol que impida conservar o consultar ese historial. Reactivarla exige cumplir nuevamente los requisitos de la operación. Comprobar solo asignaciones activas no sustituirá la comprobación definitiva de folios.

## Implementación y pruebas previstas

El alcance mínimo futuro comprende los dos modelos, servicios de creación/reactivación, registro durable, autorización, restricciones de escritura y bloqueos provisionales. No incluye retirada funcional, cambio desde `OPERADOR`, folios ni pantallas.

Se prevén cambios en `oficinas/models.py`, nuevos `oficinas/managers.py` y `oficinas/services.py`, `usuarios/models.py`, `usuarios/managers.py`, sus pruebas y las migraciones correspondientes cuando se autorice implementar. Este documento no crea ninguno de esos archivos ni genera migraciones.

Las pruebas se ejecutarán en PostgreSQL exclusivo de pruebas, con migraciones reales y aislamiento existente. Deberán cubrir:

- Varias oficinas por operador y varios operadores por oficina; unicidad incluyendo parejas inactivas y referencias protegidas.
- Autorización del actor autenticado, activo y administrador funcional, con relectura de estado actual; rechazo de permisos derivados únicamente de `is_staff` o `is_superuser`.
- Rol y actividad del operador, actividad de la oficina y ausencia de efectos automáticos sobre asignaciones al desactivar cuentas u oficinas.
- Los cinco resultados explícitos, ausencia de eventos para operaciones sin cambios y conservación de PK al reactivar.
- Conservación de eventos previos, actor, fecha, operación y estados; rechazo de edición y borrado públicos.
- Fallo al guardar el evento con rollback conjunto de asignación y evento, también dentro de una transacción exterior.
- Rechazo de las vías públicas de escritura, managers y variantes asíncronas; bloqueo provisional de retirada y cambio de rol, incluyendo instancias reconstruidas, PK explícita y escrituras parciales.
- Conservación y consulta de asignaciones históricas inactivas de cuentas con otro rol, sin presentarlas como reactivables mientras incumplan los requisitos.
- Concurrencia real con conexiones independientes: creación simultánea de una pareja, reactivación simultánea con un solo evento efectivo y coordinación con cambios del estado del actor, operador y oficina.

La reactivación partirá de un registro histórico inactivo preparado exclusivamente como fixture de pruebas, sin habilitar retirada ni simular folios. Las pruebas completas de los bloqueos definitivos deberán esperar a folios reales y al protocolo compartido. **Ninguna de estas pruebas se presenta como ejecutada o satisfactoria en esta etapa de diseño.**
