# 001 — Usuarios y asignaciones de oficinas

Fecha: 5 de octubre de 2026.

Estado: decisión aprobada; implementación pendiente.

## Contexto

Los [acuerdos vigentes](../acuerdos-vigentes.md) son la fuente principal de las reglas aprobadas. Cada cuenta tiene un único rol, las asignaciones las gestiona el administrador y un operador puede tener varias oficinas. La organización inicial contempla un operador por oficina y conserva la posibilidad de varios para el crecimiento.

El proyecto dispone de una estructura inicial de Django. La aplicación funcional todavía no está implementada y no se han ejecutado migraciones. Esta decisión registra la propuesta corregida aprobada para orientar el trabajo posterior.

## Decisión aprobada

- Utilizar un modelo personalizado `Usuario` basado en `AbstractUser`. Configurarlo como `AUTH_USER_MODEL` antes de la primera migración, conservando el acceso mediante usuario y contraseña.
- Incorporar un único campo `rol`, obligatorio, con los valores `ADMINISTRADOR`, `RECEPCION` u `OPERADOR`. Los grupos y permisos técnicos de Django no representarán roles funcionales adicionales.
- Mantener el rol `ADMINISTRADOR` separado de `is_staff` e `is_superuser`. `is_staff` se refiere al acceso al panel técnico de Django para una cuenta activa; `is_superuser` concede los permisos del mecanismo de autorización de Django. Ninguno concederá automáticamente acceso a las funciones de las pantallas propias. Un administrador funcional puede tener ambos indicadores en `False`.
- Representar la relación muchos a muchos entre operadores y oficinas mediante `AsignacionOperadorOficina`, con referencias al usuario y a la oficina.
- Garantizar la unicidad del par operador–oficina. No imponer unicidad sobre la oficina sola ni un límite obligatorio de operadores activos por oficina. Contemplar uno al lanzamiento es una organización inicial, no una prohibición técnica de una segunda asignación.
- Permitir que únicamente el administrador gestione asignaciones y que estas correspondan únicamente a usuarios con rol `OPERADOR`. El operador no seleccionará ni modificará sus oficinas desde su panel.
- Comprobar en el servidor autenticación, cuenta activa y rol autorizado para cada acción o consulta protegida. Cuando corresponda a una operación del operador, comprobar también su asignación a la oficina del folio. Aplicar estas comprobaciones a listas, detalles y acciones, incluidos accesos directos; ocultar opciones en la interfaz no sustituye la autorización. Los indicadores técnicos no eximen de estas comprobaciones.
- Reservar al administrador funcional la creación de cuentas y el establecimiento o cambio de contraseñas desde Usuarios. Utilizar los mecanismos de Django, incluidos `set_password()` y sus validadores. El registro de actividad conservará el responsable de la acción, sin registrar claves ni sus hashes. No incorporar cambio obligatorio de contraseña temporal ni rutas de cambio o recuperación por autoservicio.
- Utilizar `is_active` para desactivar y reactivar cuentas. La desactivación bloqueará el acceso y conservará el historial, en lugar de eliminar la cuenta y sus registros asociados.

## Justificación

`AbstractUser` conserva la infraestructura de autenticación de Django y permite expresar el rol único del sistema en un modelo propio. Separar el rol funcional de los indicadores técnicos evita que estos otorguen funciones ajenas a los acuerdos.

La relación muchos a muchos admite varias oficinas por operador y varios operadores por oficina. La unicidad del par evita asignaciones duplicadas sin convertir la organización inicial en un límite técnico no aprobado. La gestión administrativa y la autorización en el servidor respetan las responsabilidades acordadas.

El uso de los mecanismos de contraseña de Django y la desactivación mediante `is_active` permiten conservar la trazabilidad sin almacenar claves en los registros de actividad.

## Implementación pendiente

Esta aprobación no implica que existan los modelos, sus validaciones, las comprobaciones de permisos ni el registro de actividad. Quedan pendientes la implementación del modelo de usuario y las asignaciones, su configuración en Django y las migraciones posteriores.

También siguen pendientes la instalación y preparación de PostgreSQL y la verificación de la conexión, las pantallas y la implementación de las reglas de atención ya aprobadas. La configuración inicial de PostgreSQL por variables de entorno ya existe; este documento no la modifica.

Cualquier límite operativo adicional de operadores por oficina y su tratamiento al reactivar cuentas requerirían una decisión posterior. No se incorpora tal límite como regla aprobada.

En esta etapa solo se actualiza documentación: no se modifica código ni configuración, ni se generan o ejecutan migraciones.
