# 015 — Aplicación local de llamado y reserva

- Fecha: **12 de octubre de 2026**.
- Código comprometido: **`974e06baf8ecb38f5045e01f62374bb1151bed3a`**.
- Configuración exclusiva: **`config.settings`**.
- Identidad real antes de escribir y al finalizar: **`atencion_ciudadana / atencion_app`**, PostgreSQL **16.15**.
- Estado: **`folios.0003_llamado_y_reserva` aplicada; 23 migraciones y ninguna pendiente**.

Se siguieron la revisión previa de solo lectura, la [decisión 008](../decisiones/008-diseno-llamado-y-reserva.md) y la [validación aislada 014](014-validacion-llamado-y-reserva-postgresql.md). La presente ejecución aplica exclusivamente el esquema en la base normal y comprueba su conservación. Las pruebas de 014 permanecen como evidencia anterior: no se repitieron ni se atribuyen a la base normal.

## Condiciones previas

Git estaba limpio en `main`, en el commit indicado. Se comprobó el backend PostgreSQL y el único alias `default`, con `config.settings`, NAME y USER esperados. Las consultas previas usaron `default_transaction_read_only=on` y transacciones `REPEATABLE READ, READ ONLY`; la identidad real también confirmó `session_user=atencion_app`. Se normalizaron fechas a UTC.

El primer intento de conexión dentro del aislamiento falló. El acceso local autorizado permitió completar la inspección y la aplicación sin cambiar credenciales ni permisos.

Se inspeccionaron los procesos del equipo por argumentos y directorio del proyecto para detectar `runserver`, `gunicorn`, `uvicorn`, `daphne` y `uwsgi`; no aparecieron servidores del proyecto. Los puertos 8000 y 8001 no aceptaban conexiones TCP en loopback IPv4/IPv6. `pg_stat_activity` confirmó **cero conexiones ajenas a la base normal** antes del respaldo, después de él y antes de aplicar. Estas comprobaciones se repitieron antes de la escritura; no se detuvieron procesos ni se alteró DEMO.

El historial era consistente: **22 migraciones aplicadas** y plan completo exactamente:

```text
folios.0003_llamado_y_reserva, hacia adelante
```

Las columnas, tipos y nulabilidad coincidieron con el estado histórico de las migraciones aplicadas; las restricciones declaradas estaban presentes. Las restricciones públicas estaban validadas y los índices válidos y preparados. Las cuatro columnas nuevas todavía no existían y no había colisiones con los seis índices previstos.

Se evaluaron los tres CHECK nuevos mediante SQL sobre las columnas originales, proyectando las referencias futuras como NULL con sus tipos previstos. No se usaron consultas de modelos actuales que requirieran columnas inexistentes. Hubo **cero incompatibilidades**, incluidos resultados SQL desconocidos, y cero grupos que violaran la unicidad global de folio actual. Las tablas de folios, eventos y solicitudes estaban vacías; esa comprobación no constituye una nueva prueba de conservación histórica con registros de esas tablas.

El archivo local de 0003 fue idéntico byte por byte al comprometido en Git y su SHA-256 coincidió con la huella privada registrada durante la validación aislada. El SQL generado mediante `sqlmigrate` también fue idéntico al SQL conservado en el directorio privado de 014 y coincidió con su huella. La entrega comprometida añadió únicamente 0003 entre los archivos de migraciones; no reescribió los anteriores.

Sus **18 operaciones** son 3 RemoveConstraint, 4 AddField, 6 AlterField, 1 AddIndex y 4 AddConstraint. No contienen RunPython, RunSQL, DeleteModel ni RemoveField. El SQL no contiene DELETE, TRUNCATE ni eliminación de tablas o columnas. Sustituye tres CHECK y recrea la FK de `pausa_resultado` conservando su referencia; los cambios de choices no producen SQL físico. La migración es atómica.

## Respaldo completo y manifiesto privado

Se creó un directorio nuevo fuera del repositorio, sin sobrescribir respaldos:

```text
/home/lenin/respaldo-normal-llamado-20261012-1gwm0az4/
```

Respaldo completo en formato custom:

```text
atencion_ciudadana.dump
```

- Directorio **0700**; respaldo, manifiesto y auxiliares **0600**.
- Tamaño: **67 786 bytes**.
- SHA-256 del archivo: **`1c90877d48bb0977835d0898093522927f909280caa80f85cb02e16d66113bca`**.
- Incluye esquema, datos de las **18 tablas**, valores de las **16 secuencias** e historial de migraciones; conserva propietarios y permisos de objetos de la base.
- `pg_restore --list` terminó con salida 0.
- `pg_restore --file=/dev/null` completó la lectura con salida 0.
- La extracción de datos a memoria mediante `pg_restore --data-only --file=-` terminó con salida 0; no se conectó a una base ni se ejecutó el SQL extraído.

`pg_dump` usó un snapshot exportado desde la transacción de inspección, con zona UTC. Los bloques COPY de las 18 tablas coincidieron con los conteos y huellas de filas ordenadas del manifiesto; los valores `last_value/is_called` de las 16 secuencias también coincidieron con los del respaldo. Esto incluye los datos completos de Usuario y sesión, sin mostrarlos.

**No se probó una restauración**. La lectura y correspondencia del respaldo no acreditan por sí solas una recuperación ante cualquier fallo.

El directorio conserva `manifiesto.json`, `catalogo.toc`, `0003.sql`, `sha256.txt`, `aplicar_llamado_normal.py`, `aplicacion.log`, `verificacion-final.json`, `check.log` y `makemigrations.log`. El manifiesto contiene las columnas originales, conteos y huellas privadas de filas, historial con fechas UTC, esquema y definiciones, asociación, propietario y estado de secuencias. Todos permanecen fuera de Git; no se publicaron credenciales, datos personales, sesiones ni hashes de cuentas.

Antes de aplicar se volvió a verificar tamaño, huella, catálogo y lectura completa del respaldo. Los datos, secuencias, historial y esquema actuales todavía coincidían con el manifiesto, y el archivo y SQL conservaban sus huellas.

## Aplicación exclusiva

El auxiliar privado invocó Django desde la raíz del proyecto con `DJANGO_SETTINGS_MODULE=config.settings`:

```python
call_command(
    "migrate", "folios", "0003_llamado_y_reserva", interactive=False
)
```

Se confirmó nuevamente la identidad normal, modo de escritura y plan de una sola migración. La sesión de aplicación usó UTC, `lock_timeout=5s` y `statement_timeout=60s`. No se usaron `--fake`, `--fake-initial` ni desactivación de restricciones.

Resultado, salida 0:

```text
Applying folios.0003_llamado_y_reserva... OK
```

Se aplicó una sola vez; no hubo fallos de migración, recuperación ni reejecuciones.

## Verificación posterior de solo lectura

Se cerró la conexión de escritura y se abrió nuevamente con `default_transaction_read_only=on`, UTC y transacción de lectura. Se confirmó otra vez la identidad normal y ausencia de conexiones ajenas.

- **23 migraciones aplicadas**, historial consistente y plan completo vacío.
- Cuatro columnas nullable nuevas: `asignacion_autorizante_id` y `operador_responsable_id` bigint en EventoFolio; `evento_folio_resultado_id` bigint y `folio_resultado_id` UUID en SolicitudOperador.
- `datos_iniciales` sigue siendo JSONB y ahora admite NULL; `pausa_resultado_id` conserva bigint y admite NULL.
- Columnas, tipos y nulabilidad coinciden con el estado histórico final; las restricciones declaradas están presentes y las FK apuntan a las tablas y columnas esperadas.
- Las **cuatro FK nuevas** están validadas, son diferibles e inicialmente diferidas, y sus referencias anteriores permanecen NULL.
- Los **tres CHECK de coherencia** están presentes y validados; ninguna restricción pública quedó sin validar.
- Los **seis índices nuevos** están válidos y preparados, con columnas, unicidad y predicados esperados: cuatro de FK, `folios_cola_en_espera` y `folios_folio_actual_unico`.
- Se conservan las unicidades de CREACION por folio y operador/solicitud. El literal EN_ATENCION del índice global no habilita ese estado.
- Las columnas, restricciones e índices de las tablas distintas de Folio, EventoFolio y SolicitudOperador son idénticos al esquema previo.
- La migración y el SQL generado conservan las huellas de la validación aislada.

## Conservación de datos, credenciales y secuencias

Se compararon las **17 tablas de aplicación** mediante conteos y huellas de filas ordenadas, usando todas sus columnas originales y fechas en UTC. **Todas coinciden** con el manifiesto previo. Se incluyó la fila completa de la cuenta administradora, con su contraseña almacenada y demás credenciales y atributos, sin mostrarlos. Se confirmó que sigue existiendo una cuenta activa ADMINISTRADOR.

| Registros conservados | Cantidad antes y después |
| --- | ---: |
| Usuarios | 1 ADMINISTRADOR activo |
| Sesiones | 1 |
| Tipos de contenido | 14 |
| Permisos | 56 |
| Oficinas, trámites, asignaciones y eventos de asignación | 0 en cada tabla |
| Folios, eventos de folio, pausas, eventos de disponibilidad y solicitudes | 0 en cada tabla |
| Grupos y relaciones de permisos/grupos | 0 en cada tabla |

Las **15 secuencias de aplicación** conservan exactamente `last_value`, `is_called`, tipo, valor inicial, incremento, límites, caché, ciclo, propietario y asociación. No se llamó `nextval`, no se reiniciaron secuencias ni se crearon registros de prueba.

El cambio esperado se distingue expresamente:

- Las **22 filas anteriores de `django_migrations`**, incluidos sus identificadores y fechas normalizadas a UTC, permanecen idénticas.
- Se añadió exclusivamente el registro de `folios.0003_llamado_y_reserva`, con identificador **23**.
- `django_migrations_id_seq` pasó de **last_value=22, is_called=true** a **last_value=23, is_called=true**. Su definición, propietario y asociación se conservaron.

## Checks y estado documental

Después de la aplicación se ejecutaron con `config.settings` y conexión de solo lectura:

```python
call_command("check")
call_command("makemigrations", check_changes=True, dry_run=True, interactive=False)
```

Resultados, salida 0:

- `System check identified no issues (0 silenced).`
- `No changes detected`.

Se corrigieron en README las frases que aún presentaban llamado/reserva, sus pruebas y los casos de Ocupado/contexto desde Llamado como pendientes; se actualizó el estado local y se enlazó este registro. También se corrigió la descripción de Recepción como destino mínimo y la referencia general a ingreso/salida manual pendientes, distinguiendo la evidencia ADMINISTRADOR ya registrada.

No se modificaron código ni migraciones. No se ejecutó el runner de pruebas, crearon cuentas/catálogos/folios, restauraron respaldos ni limpiaron datos. No se conectó ni alteró el entorno DEMO; los respaldos de la base aislada permanecen independientes.

**Pendientes:** lecturas autorizadas y pantallas de Operador, inicio de atención, notas, cierre/finalización, correcciones administrativas y las demás decisiones funcionales pendientes de 008. La aplicación del esquema no habilita esas acciones ni constituye una nueva validación funcional del servicio en la base normal.

El cierre deja únicamente los cambios documentales de README y este registro, **sin commit ni push**. Antes de otra ejecución del runner aislado debe repetirse la conservación de DEMO conforme al registro 014.
