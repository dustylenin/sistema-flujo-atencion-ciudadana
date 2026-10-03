# Visión del producto

## Contexto y problema

Una dependencia atiende ciudadanos mediante una red de oficinas. El recorrido comienza en recepción y continúa con un operador de la oficina correspondiente, hasta que se registra el resultado de la atención.

El problema que se busca resolver es mantener una visión consistente de ese recorrido: quién registró al ciudadano, cuándo llegó, qué trámite solicitó, a qué oficina se dirigió, quién lo atendió y qué ocurrió durante la atención. Las notas y las incidencias deben conservarse para que la información no dependa de un único texto que se sobrescribe.

No se presupone un sistema previo ni un método actual de trabajo. El proyecto define la solución deseada a partir del flujo proporcionado.

## Objetivo general

Administrar el flujo interno de atención ciudadana y conservar un historial trazable de cada atención, con acceso controlado según el rol y los permisos del usuario.

## Objetivos específicos

- Facilitar el registro en recepción sin exigir correo electrónico ni teléfono.
- Identificar el trámite y la oficina de destino mediante catálogos administrables.
- Permitir a los operadores trabajar en una o varias oficinas según sus autorizaciones.
- Registrar automáticamente los participantes y los tiempos relevantes de la atención.
- Conservar las notas como entradas independientes, vinculadas con su autor y momento de registro.
- Documentar incidencias, resultados no concretados y transferencias excepcionales sin perder el recorrido previo.
- Preparar la información para un posible análisis futuro de notas e incidencias, sin incorporar IA en la versión 1.

## Usuarios y responsabilidades

| Usuario | Necesidad y responsabilidad |
| --- | --- |
| Administrador | Mantener los catálogos de oficinas y trámites; administrar usuarios, roles y permisos de acceso a oficinas. |
| Recepcionista | Capturar los datos del ciudadano, seleccionar trámite y oficina y registrar su llegada para dejarlo en espera. |
| Operador de oficina | Acceder a las atenciones de sus oficinas autorizadas, iniciar la atención, agregar información y registrar su resultado. |

El ciudadano es la persona atendida. En esta versión no se contempla un acceso al sistema para ciudadanos.

El inicio de sesión es común a los tres roles. La navegación posterior y las acciones disponibles dependen del rol y los permisos. Tener acceso a una oficina no concede acceso a todas las demás.

## Alcance de la versión 1

### Registro y seguimiento

Cada registro de atención incluye nombre completo obligatorio, correo y teléfono opcionales, trámite y oficina seleccionados. El sistema registra al usuario de recepción y la fecha y hora de llegada.

La atención recorre normalmente los estados de espera, atención en curso y trámite finalizado. El operador registra notas de texto libre y el sistema conserva quién atendió, el inicio, el fin y el resultado.

### Configuración

Las oficinas y los trámites se administran desde el sistema. Oficina de Registro de Marca y Oficina de Buró de Crédito son ejemplos iniciales, no requisitos de un catálogo fijo. No se definen aquí trámites concretos ni procesos particulares de esas oficinas.

### Historial y excepciones

Las notas se agregan al historial y no sustituyen las anteriores. Cada entrada conserva usuario, fecha y hora. Las incidencias y los trámites no concretados se registran como parte de la atención.

Las transferencias entre oficinas son excepcionales y deben conservar el origen, el destino y la trazabilidad de las atenciones y notas previas. Sus reglas operativas específicas quedan pendientes de definición.

## Fuera del alcance de la versión 1

- Citas programadas.
- Funciones de inteligencia artificial, incluidos el análisis automático de notas e incidencias y las recomendaciones generadas por modelos.

## Posibles extensiones

- Gestión de citas programadas.
- Análisis de notas e incidencias mediante IA, sujeto a una definición posterior de objetivos, permisos y tratamiento de datos.

Estas extensiones no son requisitos ni compromisos de entrega de la versión 1.

## Criterios de éxito

- Recepción puede registrar una atención con nombre, trámite y oficina, sin correo ni teléfono.
- Los catálogos pueden cambiar desde administración sin modificar el código de aplicación.
- Un operador puede atender en cualquiera de sus oficinas autorizadas y no puede atender en oficinas sin permiso.
- El historial permite reconstruir participantes, tiempos, notas, incidencias, transferencias y resultado de la atención.
- La finalización o el resultado no concretado quedan registrados de forma explícita.
