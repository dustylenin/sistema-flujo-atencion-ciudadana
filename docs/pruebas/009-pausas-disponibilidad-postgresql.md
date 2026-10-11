# 009 — Pausas y disponibilidad en PostgreSQL de pruebas

Fecha de registro: **11 de octubre de 2026**.

Estado: **primera entrega implementada y revisada en pruebas; aplicación local de `folios.0002` pendiente**.

Este registro documenta las ejecuciones ya realizadas del [diseño 007](../decisiones/007-diseno-pausas-y-disponibilidad.md), conforme a los [acuerdos vigentes](../acuerdos-vigentes.md) y la [decisión 006](../decisiones/006-disponibilidad-y-folio-actual-del-operador.md). Su preparación no repite pruebas ni comandos de Django, no conecta bases y no modifica código, pruebas o migraciones. Conserva las evidencias anteriores y distingue implementación, inspección y revisión crítica posterior.

## Alcance implementado

Se añadieron `PausaOperador`, `EventoDisponibilidad` y `SolicitudOperador`, con referencias `PROTECT`, restricciones de PostgreSQL y las barreras públicas del ORM existentes. La persistencia privada permite abrir una pausa, cerrar exclusivamente su `fin`, insertar eventos y confirmar comprobantes; no habilita guardados arbitrarios.

`folios/services_disponibilidad.py` implementa:

- `consultar_disponibilidad`: identidad y disponibilidad para Recepción; el operador consulta solo su propia disponibilidad, con identificador de pausa abierta y referencia mínima del folio actual.
- `consultar_pausas`: consulta administrativa de motivo, inicio, fin, duración calculada, contexto histórico y eventos, con filtros por operador, fecha, oficina y acción.
- `pausar_operador` y `reanudar_operador`: operaciones del propio operador autenticado, persistido y activo, con rol funcional vigente releído bajo bloqueo. `is_staff` e `is_superuser` no sustituyen la autorización.

La disponibilidad se deriva de la pausa abierta y del folio actual global; no se añaden campos redundantes a Usuario. La consulta de disponibilidad obtiene ambas fuentes en una misma instantánea SQL y no excluye el folio por oficina o asignación inactiva. Sin folio actual, los contextos de folio y oficina quedan ambos NULL; no se elige una oficina arbitraria.

Se conservan motivo, inicio, contexto, eventos y comprobantes originales. Reanudar recibe una pausa concreta: una solicitud retrasada sobre una pausa antigua cerrada no cierra otra posterior. Los reintentos autorizados consultan primero el comprobante: mismos argumentos devuelven el resultado histórico sin nueva transición; argumentos incompatibles para la misma clave se rechazan. Una clave nueva puede confirmar `YA_EN_PAUSA` o `YA_REANUDADA`, sin evento funcional.

Cambio de pausa, evento y comprobante se guardan en la misma transacción y conexión; un fallo de cualquiera o de la transacción exterior revierte el conjunto. El orden relativo de bloqueos es cuentas, oficinas de contexto, pausas y folios, compatible con los servicios existentes. Usuario serializa las operaciones incluso cuando todavía no existe una pausa.

**Folio y EventoFolio conservan código, comportamiento, esquema y eventos CREACION.** No se reescribieron migraciones anteriores. Se mantienen los bloqueos provisionales de retirada de asignaciones y salida de OPERADOR.

## Entorno y aislamiento

| Comprobación | Resultado |
| --- | --- |
| Configuración exclusiva | `config.settings_test_migrations` |
| Base real y `TEST.NAME` | `test_atencion_catalogos_migraciones` |
| Usuario real | `atencion_test` |
| Migraciones reales | `TEST.MIGRATE=True`, `MIGRATION_MODULES={}` |
| Ejecutor | `--keepdb --parallel 1 --noinput` |

Antes de escribir en la base se verificó la identidad mediante conexión real. El primer intento quedó bloqueado por el aislamiento del entorno; el mismo comando, con acceso autorizado, devolvió la identidad esperada:

```bash
.venv/bin/python -B manage.py shell --settings=config.settings_test_migrations -c 'from django.db import connection; assert connection.settings_dict["NAME"] == "test_atencion_catalogos_migraciones"; assert connection.settings_dict["USER"] == "atencion_test"; cursor = connection.cursor(); cursor.execute("SELECT current_database(), current_user"); identity = cursor.fetchone(); assert identity == ("test_atencion_catalogos_migraciones", "atencion_test"), identity; print(identity); cursor.close(); connection.close()'
```

Resultado: `('test_atencion_catalogos_migraciones', 'atencion_test')`. Las inspecciones posteriores volvieron a comprobar esa identidad. Se conservaron las barreras de aislamiento existentes; los auxiliares nuevos exigen además la configuración exacta autorizada. No se conectó `atencion_ciudadana`, no se cambiaron credenciales ni privilegios y no se mostraron secretos.

## Migración y SQL revisados

Se generó una única migración nueva y se revisó su SQL antes de que el ejecutor de pruebas la aplicara:

```bash
.venv/bin/python -B manage.py makemigrations folios --settings=config.settings_test_migrations
.venv/bin/python -B manage.py sqlmigrate folios 0002 --settings=config.settings_test_migrations
```

La migración es `folios/migrations/0002_pausaoperador_eventodisponibilidad_solicitudoperador_and_more.py`. Contiene tres `CreateModel` y ocho `AddConstraint`, exclusivamente sobre los modelos nuevos. El SQL crea tres tablas, sus referencias e índices, cinco CHECK, dos restricciones UNIQUE y un índice único condicional para una sola pausa abierta por operador:

```sql
CREATE UNIQUE INDEX "folios_pausa_abierta_unica"
ON "folios_pausaoperador" ("operador_id") WHERE "fin" IS NULL;
```

Los CHECK comprueban motivo con contenido, orden temporal, contexto conjuntamente NULL o no NULL, operaciones de evento y combinaciones coherentes de operación, argumentos, resultado y evento del comprobante. Las condiciones de NULL son explícitas; los campos obligatorios tienen NOT NULL. Las referencias de PostgreSQL son diferibles y no incluyen borrado en cascada; `PROTECT` actúa en el ORM. El SQL no altera Folio, EventoFolio ni otras tablas existentes.

## Pruebas ejecutadas y resultados

Primero se ejecutaron los dos módulos nuevos con detalle:

```bash
.venv/bin/python -B manage.py test folios.test_disponibilidad folios.test_disponibilidad_concurrencia --settings=config.settings_test_migrations --keepdb --parallel 1 --noinput --verbosity 2
```

El ejecutor aplicó `folios.0002` correctamente. Esa primera ejecución tenía 35 pruebas y terminó con **un error en la prueba de borrado asíncrono**: Django expone `adelete` en el queryset, no en el manager relacionado. Se corrigió la llamada de la prueba, sin cambiar la protección de producción, y se ajustó la invocación de las variantes asíncronas delegadas.

Después se repitieron los módulos nuevos sin `--verbosity 2`: **35 pruebas satisfactorias**. Se completó la cobertura de referencias y barreras y se añadieron dos casos de concurrencia: argumentos incompatibles para la misma clave y una solicitud que espera una transacción exterior revertida. La ejecución final de los módulos fue:

```bash
.venv/bin/python -B manage.py test folios.test_disponibilidad folios.test_disponibilidad_concurrencia --settings=config.settings_test_migrations --keepdb --parallel 1 --noinput
```

Resultado final: **37 pruebas satisfactorias**, incluidas **12 de concurrencia**, sin fallos ni errores. La prueba de borrado asíncrono estaba corregida antes de esta ejecución final.

La cobertura incluye autorización vigente e independencia de flags técnicos, motivo obligatorio, restricciones y coherencia de NULL con rechazos reales de PostgreSQL, unicidades, referencias protegidas, conservación histórica, resultados sin transición, solicitudes repetidas e incompatibles, pausas antiguas frente a nuevas, exposición por rol y consultas sin escrituras. Se provocaron fallos reales en cada escritura de apertura y cierre para comprobar rollback conjunto, además del rollback exterior. Se comprobaron las barreras mediante instancias, managers, querysets, operaciones masivas, variantes asíncronas y todas las relaciones inversas, incluida selección repetida del manager.

Las pruebas de concurrencia utilizan `TransactionTestCase`, conexiones independientes, `pg_backend_pid()` y PIDs distintos, sincronización explícita con eventos y comprobación de espera real mediante `pg_blocking_pids`. Cubren claves iguales y distintas, incompatibilidad de argumentos, rollback exterior, reanudaciones simultáneas, ambos órdenes entre pausa y reanudación, pausa antigua frente a otra abierta, desactivación de cuenta en ambos órdenes y compatibilidad con creación de asignaciones.

Después se ejecutó la suite completa solicitada:

```bash
.venv/bin/python -B manage.py test usuarios config.tests oficinas tramites folios --settings=config.settings_test_migrations --keepdb --parallel 1 --noinput
```

Resultado: **140 pruebas satisfactorias, que incluyen las 37 nuevas**. No se suman los conteos ni se presentan como 177 pruebas distintas. La suite completa emitió una advertencia de `asgiref` sobre una llamada no marcada como asíncrona en pruebas existentes; no hubo fallos ni errores. Los módulos nuevos pasaron por separado sin esa advertencia.

## Comprobaciones e inspección del esquema

Se ejecutaron después de la suite completa:

```bash
.venv/bin/python -B manage.py check --settings=config.settings_test_migrations
.venv/bin/python -B manage.py makemigrations --check --dry-run --settings=config.settings_test_migrations
git diff --check
```

Resultados: `System check identified no issues (0 silenced)` y `No changes detected`. Se revisó el formato de los archivos nuevos con `git diff --no-index --check /dev/null <archivo>`, sin diagnósticos de formato; en esta modalidad el código 1 señala diferencias respecto del archivo vacío. El diff de implementación se revisó completo.

La inspección se ejecutó mediante un auxiliar temporal de lectura:

```bash
.venv/bin/python -B manage.py shell --settings=config.settings_test_migrations -c 'exec(open("/tmp/inspeccionar_entrega_disponibilidad.py").read())'
```

El auxiliar temporal no forma parte del repositorio. Consultó `pg_attribute` con `format_type`, `pg_constraint` y `pg_indexes`; comparó tipos y NULL con los modelos, comprobó restricciones e índices y contó filas. También utilizó `MigrationExecutor` para contar migraciones aplicadas y comprobar el plan frente a los nodos finales, sin ejecutar migraciones.

| Elemento nuevo | Resultado comprobado |
| --- | --- |
| Tablas | 3: `folios_pausaoperador`, `folios_eventodisponibilidad`, `folios_solicitudoperador` |
| Columnas | 22: siete de pausa, cinco de evento y diez de solicitud |
| Restricciones | 19: tres PK, nueve FK, cinco CHECK y dos UNIQUE; todas validadas |
| Índices | 15: tres de PK, nueve de FK y tres únicos, incluido el condicional de pausa abierta |
| Migraciones aplicadas en pruebas | 22 |
| Migraciones pendientes en pruebas | 0 |

La primera inspección comparó las columnas de Folio mediante una lista dependiente del orden declarado. La serialización de claves foráneas en la migración utiliza otro orden y esa comparación produjo un rechazo del auxiliar. Se corrigió para comparar por nombre de columna y se repitió la inspección de lectura: **no hubo diferencias de esquema**. Folio y EventoFolio coinciden en columnas, tipos, NULL y restricciones con `folios.0001_initial`; sus columnas reales también coincidieron con esa definición.

Se confirmaron **cero datos residuales de aplicación** en las doce tablas inspeccionadas: `usuarios_usuario`, sus relaciones `usuarios_usuario_groups` y `usuarios_usuario_user_permissions`, `oficinas_oficina`, `tramites_tramite`, `oficinas_asignacionoperadoroficina`, `oficinas_eventoasignacion`, `folios_folio`, `folios_eventofolio` y las tres tablas nuevas. Los registros técnicos de migraciones y Django no se consideran datos ficticios de aplicación.

## Revisión crítica posterior

Se contrastaron los cinco archivos de implementación con los acuerdos y las decisiones 006 y 007. **No se encontraron defectos que requirieran corrección, no se modificaron archivos y no se ejecutaron nuevas pruebas.** Se revisaron autorización, exposición por rol, instantánea SQL, reintentos, inmutabilidad, persistencia específica, restricciones, atomicidad, orden de bloqueos y barreras públicas.

La revisión posterior comprobó de nuevo la conexión real autorizada y generó el SQL de `folios.0002` con `call_command("sqlmigrate", "folios", "0002", database="default")`, sin aplicarlo. También verificó el formato, el índice vacío, los cinco archivos pendientes y la conservación literal del código anterior de Folio y EventoFolio. Estas comprobaciones de lectura y estáticas no constituyen otra ejecución de las 37 ni de las 140 pruebas.

Al documentar y guardar la entrega se prepararon únicamente los ocho archivos autorizados, se revisó el diff preparado completo y `git diff --cached --check` terminó sin incidencias. Los cinco archivos de implementación conservaron sus hashes durante esta etapa; no se repitieron pruebas ni se conectaron bases.

## Límites y aplicación local pendiente

**`folios.0002` todavía está pendiente en `atencion_ciudadana`.** La última evidencia local conserva `folios.0001_initial`, 21 migraciones aplicadas y plan entonces vacío, en el [registro 008](008-migracion-folios-local.md). No se conectó esa base para implementar, revisar o documentar esta entrega; su aplicación local y comprobación posterior siguen pendientes.

Los casos reales de **Ocupado y contexto desde Llamado** se verificarán al integrar la segunda entrega de llamado y reserva con pausa y el límite global de un folio actual. **En atención y conservación de notas** se verificarán cuando se implementen. No se simularon esos estados para atribuirles verificación en esta entrega. No se implementaron llamado, inicio, notas, cierre, pantallas, Inactivo ni correcciones administrativas.

SQL directo, deserializadores y APIs internas pueden eludir las barreras públicas. Las restricciones no garantizan por sí solas autorización, inmutabilidad ante esas vías, correspondencias entre tablas ni que cada cambio tenga evento y comprobante; esas garantías corresponden a los servicios por las vías admitidas. No hay disparadores SQL ni una auditoría global completa.

La exposición mínima de Recepción no constituye una prohibición funcional definitiva. Siguen pendientes los permisos ampliados, la presentación de pausas sin oficina, el significado funcional de Inactivo y las correcciones administrativas que pudieran producir un segundo folio actual. No se resolvieron esas decisiones en esta entrega.
