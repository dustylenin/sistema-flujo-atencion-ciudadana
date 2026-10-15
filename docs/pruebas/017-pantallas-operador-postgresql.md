# 017 — Validación de pantallas de Operador y recuperación DEMO

- Fecha: **14 de octubre de 2026**.
- Alcance: integración de la [decisión 012](../decisiones/012-integracion-pantallas-operador.md), con los [acuerdos vigentes](../acuerdos-vigentes.md).
- Punto de partida: `main` en `9fd4d278c9c00b84a4e5adad93e8a234c0224c64`, con la integración preparada en 16 archivos sin guardar en un commit. No se descartaron cambios.
- Configuración exclusiva: **`config.settings_test_migrations`**.
- Identidad real previa y final: **`test_atencion_catalogos_migraciones / atencion_test`**, con `session_user` y propietario `atencion_test`.
- No se conectó ni modificó la base normal. No se hizo commit ni push.

## Revisión previa y acceso afectado

Se revisaron formularios, vistas, rutas, plantillas, JavaScript, las 35 pruebas HTTP nuevas y las pruebas existentes de acceso. Se contrastaron firma y estructura de tokens, vínculo con actor/operación, destinos cerrados, UUID y pausa concreta, CSRF, `never_cache`, conservación exacta del motivo y claves ante errores y reintentos. Los servicios conservan autorización vigente y comprobantes; no se amplían datos ni permisos.

Los mensajes de repetición indican resultado original y ausencia de otra transición. Se comprobaron doble POST antes de seguir la redirección, resultado bloqueado repetido después de reanudar y respuesta perdida tras confirmar, sin una transición duplicada. Reanudar un formulario antiguo no cierra una pausa posterior. Las páginas no garantizan aceptación de una acción por lo leído previamente.

Se reforzaron dos métodos existentes de `usuarios/test_acceso.py`: comprobar que el destino OPERADOR usa la nueva Cola de atención, permite ir a Atención actual y no ofrece inicio, y verificar `no-store` en ambas páginas. Se mantuvieron las comprobaciones 200/403 entre roles y las demás garantías de sesión, CSRF y flags. La clase conserva **25 casos**, incluidos en la regresión completa; no son pruebas nuevas adicionales a las 35 HTTP de Operador.

## Respaldo nuevo, manifiesto y barreras

Se leyó el [registro 016](016-lecturas-operador-postgresql.md) y se revisó su auxiliar privado de preservación. Se preparó una copia adaptada al runner HTTP/JavaScript, sin ejecutar los respaldos o manifiestos anteriores ni introducir un paso de migración previo a las pruebas.

Directorio nuevo fuera del repositorio:

```text
/home/lenin/validacion-pantallas-operador-20261014-scuqxbug/
```

Contiene privadamente `validar_pantallas.py`, `test_atencion_catalogos_migraciones.dump`, `manifiesto.json`, catálogos TOC, datos extraídos, `recuperacion.sql`, resultados y registros. Permisos **0700** en el directorio y **0600** en sus archivos. Las contraseñas PostgreSQL de prueba se transmitieron exclusivamente en memoria al entorno de los subprocesos; no se publicaron credenciales, datos personales, hashes de cuentas ni el manifiesto.

Antes de escribir se comprobaron alias único PostgreSQL, NAME y TEST.NAME aislados idénticos, usuario exclusivo, TEST.MIGRATE=True y MIGRATION_MODULES vacío, junto con las barreras PostgreSQL actuales de las clases de pruebas. La conexión real, usuario de sesión y propietario coincidieron con lo esperado. Había **23 migraciones aplicadas y plan vacío**, índices válidos y restricciones validadas.

Se verificaron puertos **8000 y 8001 detenidos** en IPv4/IPv6, ausencia de servidores del proyecto y **cero conexiones ajenas** a la base aislada. Las guardas se repitieron entre fases; no se abrió DEMO para revisión manual ni se ejecutaron otros escritores durante el procedimiento. El acceso local se autorizó para las comprobaciones de sockets y PostgreSQL requeridas por el aislamiento.

El respaldo completo nuevo en formato custom tiene **74 816 bytes**. `pg_dump` utilizó un snapshot exportado desde una transacción **REPEATABLE READ, READ ONLY**, con representación UTC. `pg_restore --list`, lectura completa hacia `/dev/null` y extracción de datos a memoria terminaron correctamente. Los COPY del dump coincidieron con columnas, conteos y huellas de filas ordenadas de las **18 tablas** del manifiesto; los valores/is_called de las **16 secuencias** también coincidieron. Se conservaron esquema, restricciones, índices, historial, definiciones/asociaciones de secuencias y huellas de archivos de migración, sin imprimir sus datos.

## Recuperación revisada antes del runner

La recuperación selectiva siguió el procedimiento comprobado de 016: **17 bloques COPY de tablas de datos y 15 ALTER SEQUENCE RESTART**, excluyendo `django_migrations` y su secuencia. Se revisaron el TOC, las columnas y datos seleccionados, las guardas de identidad/historial y la huella del archivo de recuperación antes de preparar las tablas para pruebas.

El archivo usa constraints diferidas, TRUNCATE explícito **CONTINUE IDENTITY RESTRICT**, COPY con identificadores originales, reinicios transaccionales y comprobación inmediata de restricciones. No carga esquema ni historial antiguo del dump, no usa CASCADE, setval, desactivación de restricciones o triggers, eliminación de bases o migraciones simuladas. Los siguientes valores de secuencias se calcularon desde last_value/is_called, se comprobaron contra límites y máximos de IDs y se verificaron sin llamar nextval.

El runner quedó dentro de un bloque `try/finally` con recuperación también ante fallos. Cada ciclo revalidó respaldo, manifiesto, esquema y datos DEMO antes de vaciar solo las 17 tablas de datos. En la repetición se compararon las próximas asignaciones de secuencias y se respetó el historial resultante de la primera regresión.

## Ejecuciones y resultados

```bash
.venv/bin/python -B manage.py test folios.test_operador --settings=config.settings_test_migrations --keepdb --parallel 1 --noinput --verbosity 2
node --check static/js/operador.js
node static/js/operador.test.cjs
.venv/bin/python -B manage.py test usuarios config.tests oficinas tramites folios --settings=config.settings_test_migrations --keepdb --parallel 1 --noinput --verbosity 2
node --check static/js/recepcion.js
node static/js/recepcion.test.cjs
```

| Ejecución | Resultado real |
| --- | --- |
| HTTP nuevo de Operador | **35 pruebas satisfactorias**, 4,036 s; salida 0. |
| JavaScript de Operador | **4 pruebas satisfactorias**, cero fallos, cancelaciones u omisiones; salida 0. |
| Primera regresión Django | **308 casos ejecutados**, 48,171 s; salida 1 por dos subfallos de un método de acceso ampliado. |
| JavaScript existente de Recepción | **4 pruebas satisfactorias**, cero fallos, cancelaciones u omisiones; salida 0. |
| Caso de acceso corregido | **1 prueba satisfactoria**, 1,916 s; salida 0. |
| Regresión final Django | **308 pruebas satisfactorias**, 48,503 s; salida 0. Incluye las 35 nuevas y los 25 casos existentes de acceso. |
| Sintaxis JavaScript de Operador y Recepción | Correcta; ambas salidas 0. |

Son **308 casos Django distintos** en la regresión final y **8 pruebas JavaScript distintas**. Las 35 nuevas están incluidas en 308, no se suman como casos distintos. No se repitieron las suites HTTP nuevas o JavaScript tras corregir exclusivamente el fixture de acceso: se repitió ese caso y la regresión completa.

### Fallo encontrado y corrección

`test_respuestas_de_acceso_y_destino_no_se_almacenan_en_cache` conservaba la sesión de Recepción de su primera parte y llamaba al login para entrar como Operador. El login existente redirige una cuenta ya autenticada a su destino; no cambia de cuenta. Las peticiones a `/operacion/` y `/operacion/actual/` seguían siendo de Recepción y recibieron correctamente **403**, frente al 200 esperado por la ampliación de la prueba.

Se corrigió la ampliación usando un **Client nuevo**, autenticando al Operador y comprobando su redirección antes de verificar 200 y `no-store` en ambas páginas. No se cambiaron las vistas de acceso, los permisos o los servicios ni se aceptó 403 como éxito. Las comprobaciones existentes de rechazo entre roles permanecen intactas. El caso corregido y la regresión final pasaron. **No se identificaron defectos que exigieran correcciones a la lógica de pantallas, formularios o JavaScript preparada.**

La cobertura nueva verificó CSRF real, sesiones y roles vigentes, combinaciones de flags, firma/actor/operación/estructura de tokens, destinos cerrados, datos de formulario inválidos, claves y motivo conservados, doble envío y respuesta perdida, reanudación antigua, folios ajenos, catálogos desactivados, paginación y ausencia de escrituras de negocio en GET. La regresión incorporó las pruebas existentes de Recepción, disponibilidad, llamado, concurrencia y migración.

Registros privados principales:

```text
operador-http-m0ci02bd.log
operador-js-4-toog5f5l.log
regresion-completa-q2m0aby4.log
recepcion-js-4-6dq9n7qx.log
operador-http-m32m6m4s.log
regresion-completa-f1xe7z_2.log
```

## Recuperación DEMO tras el fallo y al finalizar

Se realizaron **dos ciclos de recuperación selectiva**, uno después de la regresión fallida y otro después del caso corregido y la regresión satisfactoria. Ambos terminaron con salida **0** mediante `psql -X --set=ON_ERROR_STOP=1 --single-transaction --file=<recuperacion.sql>`. Antes de cada recuperación se comprobó el esquema y se capturaron privadamente el historial vigente y su secuencia.

Las verificaciones de ambos ciclos y una verificación final independiente de solo lectura confirmaron:

- **17 tablas de datos idénticas al manifiesto previo**, por columnas, conteos y huellas: cuentas, sesiones, catálogos, relaciones, folios y evidencia incluidos.
- **15 secuencias de datos con las próximas asignaciones originales**, misma definición, propietario y asociación. Se compara la próxima asignación, pues RESTART puede dejar is_called=False; no se llama nextval para verificar.
- **Esquema original conservado**, restricciones validadas, índices válidos y preparados, archivos de migración sin cambios.
- **23 migraciones aplicadas y ninguna pendiente**, mismo conjunto de migraciones que al inicio. Cada recuperación conservó exactamente las filas e identificadores/fechas del historial y la secuencia capturados inmediatamente antes, sin cargar el historial antiguo.
- Cuenta RECEPCION activa sin flags técnicos y oficina/trámite DEMO activos y compatibles, sin mostrar datos de cuentas.
- Cero conexiones ajenas y puertos 8000/8001 detenidos. No se inició una revisión visual.

La prueba de migración existente reaplicó 0003 en ambas regresiones. Solo ese registro cambió de identificador/fecha y `django_migrations_id_seq` pasó de **26 a 28** durante los runners. La recuperación no lo revirtió: preservó el historial resultante, como se solicitó. No se añadieron migraciones ni se restauró esquema antiguo.

Esto acredita recuperación real de los datos seleccionados sobre el esquema vigente, también después del fallo de pruebas; no una restauración completa del esquema ni una garantía ante cualquier fallo del servidor. **DEMO está recuperado: antes de otro runner debe repetirse su preservación.** Respaldo, manifiesto, SQL y registros permanecen privados y fuera de Git.

## Checks finales, archivos y límites

Después de recuperar se ejecutaron exclusivamente con conexión de solo lectura y configuración aislada:

```bash
PGOPTIONS='-c default_transaction_read_only=on' .venv/bin/python -B manage.py check --settings=config.settings_test_migrations
PGOPTIONS='-c default_transaction_read_only=on' .venv/bin/python -B manage.py makemigrations --check --dry-run --settings=config.settings_test_migrations
git diff --check
```

`check`: **sin incidencias**. Correspondencia modelos/migraciones: **No changes detected**. Formato y enlaces locales correctos. No se agregaron funcionalidades, modelos o migraciones ni se modificaron servicios de negocio. El auxiliar privado se adaptó tras el fallo para repetir solo el caso corregido y la regresión; sus funciones de preservación y recuperación no cambiaron.

La entrega conserva los archivos preparados: `folios/forms_operador.py`, `views_operador.py`, `test_operador.py`; `usuarios/urls.py` y `views.py`; las seis plantillas en `templates/operador/`; `static/css/operador.css`, `static/js/operador.js` y `operador.test.cjs`. Esta validación añade los cambios de `usuarios/test_acceso.py`, este registro 017 y las actualizaciones de decisión 012 y README.

**Comprobación visual e interactiva pendiente**: escritorio/móvil, teclado, foco, presentación de errores y navegación con JavaScript deshabilitado en navegador. Las pruebas HTTP y JavaScript no sustituyen esa revisión. Inicio, notas, finalización, denegación, historial y filtros siguen fuera de alcance. Sin commit ni push; no se incorporan archivos privados a Git.
