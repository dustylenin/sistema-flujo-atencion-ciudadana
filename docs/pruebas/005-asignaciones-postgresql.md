# 005 — Asignaciones de operadores en PostgreSQL de pruebas

Fecha de implementación, revisión y registro: 10 de octubre de 2026.

Estado: **creación y reactivación implementadas y revisadas en pruebas; aplicación de las dos migraciones nuevas a la base local pendiente**.

Este registro documenta las ejecuciones ya realizadas de la [decisión 003](../decisiones/003-servicios-de-asignacion-y-actividad.md), conforme a los [acuerdos vigentes](../acuerdos-vigentes.md) y la [decisión 002](../decisiones/002-oficinas-tramites-y-asignaciones.md). Su elaboración no ejecuta pruebas ni comandos de Django, no conecta ni modifica bases y conserva intactas las evidencias anteriores.

## Alcance implementado

`AsignacionOperadorOficina` y `EventoAsignacion` están en `oficinas`. Se permiten varias oficinas por operador y varios operadores por oficina, con pareja única incluso inactiva, referencias `PROTECT` y pareja inmutable por las vías públicas admitidas del ORM.

Los servicios `crear_asignacion` y `reactivar_asignacion` exigen un actor procedente del contexto autenticado, administrador funcional activo. Dentro de la transacción vuelven a consultar y bloquear su cuenta; `is_staff` e `is_superuser` no conceden autorización. Crear o reactivar efectivamente exige operador con rol `OPERADOR`, cuenta activa y oficina activa, comprobados bajo bloqueo.

Los resultados son `CREADA`, `REACTIVADA`, `YA_ACTIVA`, `REQUIERE_REACTIVACION` y `ASIGNACION_INEXISTENTE`. Los resultados sin cambios no escriben ni generan eventos. Reactivar conserva la PK y los eventos anteriores.

Asignación y evento se guardan en la misma transacción y conexión: un fallo del evento revierte también la creación o reactivación. Los eventos durables de `CREACION` y `REACTIVACION` conservan actor, fecha y estado anterior/nuevo, sin edición ni borrado públicos. El CHECK exige `NULL` anterior únicamente para creación; reactivación exige anterior `False` explícitamente no nulo y nuevo `True`.

El orden de bloqueos es cuentas del actor y operador por PK ascendente, sin duplicados; oficina; asignación existente. El bloqueo del operador serializa creaciones de una pareja aún inexistente. Las operaciones futuras relacionadas deberán compartir este protocolo.

## Entorno y aislamiento

| Comprobación | Resultado |
| --- | --- |
| Configuración exclusiva | `config.settings_test_migrations` |
| Base real y `TEST.NAME` | `test_atencion_catalogos_migraciones` |
| Usuario real | `atencion_test` |
| Migraciones | `TEST.MIGRATE=True`, `MIGRATION_MODULES={}` |
| Ejecutor | `--keepdb --parallel 1 --noinput` |

Antes de las ejecuciones se confirmó mediante conexión real `current_database()` y `current_user`, sin mostrar secretos. Se mantuvieron las barreras existentes y la lista explícita de los dos nombres autorizados de bases de pruebas; no se aceptó cualquier prefijo `test_`. La primera base de pruebas y `atencion_ciudadana` no se conectaron ni modificaron en esta etapa. No se cambiaron privilegios.

## Comandos y resultados

Desde la raíz del repositorio se ejecutó la suite completa:

```bash
.venv/bin/python -B manage.py test usuarios config.tests oficinas tramites --settings=config.settings_test_migrations --keepdb --parallel 1 --noinput --verbosity 2
```

Resultado final de esa ejecución: **74 pruebas satisfactorias**, con `check` sin incidencias. Incluye las 42 pruebas anteriores y 32 nuevas del alcance de asignaciones y protecciones de usuarios. **Esta ejecución ocurrió antes del ajuste final de sincronización de las pruebas de concurrencia.** Las 42 pruebas anteriores no se atribuyen por sí solas a esta implementación.

La revisión crítica posterior detectó una debilidad de cobertura: la barrera inicial podía permitir ejecuciones casi secuenciales y el mismo actor podía serializar ambos servicios, ocultando un problema del bloqueo del operador. Se reforzaron las pruebas de creación y reactivación con administradores distintos, conexiones independientes identificadas por `pg_backend_pid()`, pausa antes de persistir la primera transición y comprobación de espera real de la segunda sobre el operador mediante `pg_blocking_pids`. La tercera prueba del grupo verifica la relectura del estado de actor, operador y oficina después de esperar sus bloqueos.

Después del ajuste se ejecutó únicamente el grupo afectado:

```bash
.venv/bin/python -B manage.py test oficinas.test_asignaciones.AsignacionesConcurrenciaTests --settings=config.settings_test_migrations --keepdb --parallel 1 --noinput --verbosity 2
```

Resultado: **3 pruebas satisfactorias**, `check` sin incidencias y ninguna migración pendiente de aplicar por el ejecutor. **No se repitió la suite completa después de ese ajuste.** Los actores distintos corresponden a las dos pruebas de servicios simultáneos; la tercera coordina un servicio con cambios concurrentes de estado.

Las comprobaciones de implementación y revisión incluyeron:

```bash
.venv/bin/python -B manage.py check --settings=config.settings_test_migrations
.venv/bin/python -B manage.py makemigrations --check --dry-run --settings=config.settings_test_migrations
.venv/bin/python -B manage.py showmigrations --settings=config.settings_test_migrations
.venv/bin/python -B manage.py migrate --plan --settings=config.settings_test_migrations
git diff --check
```

Resultados comprobados: `check` sin incidencias; `makemigrations --check --dry-run` sin cambios; `showmigrations` con todas aplicadas y `migrate --plan` sin operaciones pendientes. La revisión posterior volvió a comprobar la correspondencia modelos/migraciones y `git diff --check`; también revisó espacios en los archivos nuevos mediante `git diff --no-index --check /dev/null <archivo>`, sin incidencias. La identidad de la conexión exclusiva se confirmó nuevamente antes de las tres pruebas afectadas. En la preparación de esta entrega se revisó el diff completo de los trece archivos autorizados y `git diff --cached --check` terminó sin incidencias; no se repitieron pruebas ni comprobaciones con base de datos.

## Migraciones, esquema y datos

Se añadieron únicamente:

| Migración | Operaciones revisadas |
| --- | --- |
| `oficinas.0002_asignacionoperadoroficina_eventoasignacion_and_more` | Crea asignaciones y eventos; añade unicidad de pareja y CHECK de estados del evento. |
| `usuarios.0002_alter_usuario_options` | Fija managers base y por defecto en el estado de migraciones; no altera tablas mediante SQL. |

Sus operaciones y SQL se revisaron antes de aplicarlas en pruebas. No se reescribieron migraciones existentes, no se usó `--fake` ni `--fake-initial` y no se desactivaron migraciones. Quedaron **20 migraciones reales aplicadas**: doce de `auth`, dos de `contenttypes`, una de `sessions`, dos de `usuarios`, dos de `oficinas` y una de `tramites`. El historial coincidió con los archivos y el plan quedó vacío.

La inspección de lectura verificó tablas, columnas, nulabilidad, referencias, unicidad y CHECK de los dos modelos nuevos; también sus ocho restricciones y siete índices, validados y válidos respectivamente. Las pruebas provocaron rechazos reales de PostgreSQL por pareja duplicada, estados incoherentes, referencias inválidas y valores nulos obligatorios. El fallo real de inserción de un evento comprobó el rollback de creación y reactivación.

Al finalizar la implementación se comprobaron **cero filas residuales** en `usuarios_usuario`, `oficinas_oficina`, `tramites_tramite`, `oficinas_asignacionoperadoroficina` y `oficinas_eventoasignacion`. Las pruebas posteriores de concurrencia usaron `TransactionTestCase` con limpieza de fixtures. Los registros inactivos se prepararon únicamente como fixtures mediante persistencia interna, sin habilitar retirada funcional ni crear folios ficticios.

## Protecciones y pendientes

Las barreras cubren escritura y borrado públicos de asignaciones/eventos mediante instancias, querysets, managers por defecto, base y relacionados, incluidas las variantes asíncronas. No hay una opción pública para omitirlas; los servicios usan persistencia privada específica después de autorizar y validar.

`Usuario.save()` bloquea la salida efectiva de `OPERADOR`, consultando y bloqueando el rol persistido. Respeta `update_fields`, conserva escrituras de contraseñas y actividad, protege instancias reconstruidas y PK explícitas, y evita sobrescribir una cuenta insertada concurrentemente tras una lectura sin resultado. Se rechazan actualizaciones masivas del rol e inserciones masivas con sobrescritura por conflicto, también por vías asíncronas.

**Retirada y salida de `OPERADOR` permanecen bloqueadas provisionalmente**, incluso sin asignaciones activas. Sus reglas definitivas requieren folios reales y pruebas del protocolo compartido; no se presentan como implementadas. Desactivar cuentas u oficinas no introduce efectos automáticos sobre asignaciones.

**Las dos migraciones nuevas siguen pendientes en `atencion_ciudadana`**, cuya última evidencia conserva las 18 migraciones de la etapa de catálogos. No se comprobó ni alteró esa base durante esta etapa.

SQL directo, deserialización y APIs internas pueden eludir las barreras del ORM. PostgreSQL garantiza referencias, unicidad y coherencia de estados, pero esas restricciones no garantizan autorización, inmutabilidad de la pareja, conservación absoluta ni que cada escritura tenga un evento. No hay disparadores aprobados. Estos eventos cubren exclusivamente creación/reactivación: **la auditoría global sigue pendiente**, junto con folios, pantallas y demás operaciones funcionales.
