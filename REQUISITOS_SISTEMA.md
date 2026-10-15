# Base de requisitos para nuestro sistema de mantenimiento

Propuesta derivada de la revisión de interfaz de BusCMMS. No supone que se hayan comprobado sus reglas internas. La revisión de usuario real y las pruebas funcionales siguen pendientes.

## Prioridad de implementación

| Prioridad | Capacidad | Criterio verificable |
|---|---|---|
| P0 | Organizaciones, usuarios y permisos | Ningún rol puede consultar o modificar objetos de otra organización. Las operaciones se validan en el servidor, incluidos adjuntos y exportaciones. |
| P0 | Activos, solicitudes y OT | Identificadores únicos por organización, historial de estado y asignaciones; reglas explícitas de apertura, ejecución, bloqueo, revisión y cierre. |
| P0 | Inspecciones y defectos | Plantillas versionadas, resultados trazables y proceso explícito para defectos críticos y retorno del activo al servicio. |
| P0 | Preventivos | Frecuencia por fecha, kilometraje u horas; vencimientos calculados con zona horaria y unidades de la organización. |
| P0 | Auditoría y consistencia | Actor y cambios registrados; operaciones relacionadas atómicas y protección contra duplicados por reintentos. |
| P0 | Panel e indicadores | No mostrar 100% cuando no hay denominador sin explicar «No aplica»; idénticos filtros y fórmulas en tarjeta, alerta y exportación. |
| P0 | Idioma y configuración regional | Ninguna clave de traducción visible; moneda y unidades coherentes en formularios, reportes y exportaciones. |
| P1 | Inventario, proveedores y compras | Reserva, consumo y devolución asociados a OT; recepción parcial y conciliación de costos y existencias. |
| P1 | Documentos y alertas | Vencimientos, categorías, visibilidad por rol y enlaces temporales autorizados. |
| P1 | API y reportes | Contrato versionado, paginación, filtros, permisos por ámbito y errores estructurados. Las credenciales de integración son distintas de la sesión interactiva. |
| P2 | Telemática y predicción | Procedencia y fecha de los datos, unidades y explicación de recomendaciones; funcionamiento definido cuando faltan datos. |
| Condicional | HOS y reglas regulatorias | Habilitar solo cuando correspondan a la operación y jurisdicción; validar requisitos específicos antes de implementarlos. |

## Flujos a validar con usuarios

Conductor: seleccionar activo asignado, completar inspección, declarar defecto y seguir su resolución. Técnico: aceptar tarea, registrar trabajo, repuestos, horas y evidencia, y solicitar revisión. Supervisor: priorizar, asignar, revisar y cerrar según política. Administrador: configurar organización, roles, catálogos, unidades y acceso a integraciones.

Estos roles son una propuesta. Deben adaptarse al tamaño de la organización y confirmarse con el usuario; no equivalen a las capacidades reales de las cuentas de BusCMMS.

## Modelo mínimo propuesto

Organización, departamento, usuario, pertenencia y rol; activo y lecturas de uso; plantilla y versión de inspección; ejecución de inspección y defecto; solicitud, OT, tareas, asignaciones y transiciones; plan preventivo y ejecución; repuesto, almacén, movimiento y consumo; proveedor, compra y recepción; documento, vencimiento y evento de auditoría.

Cada entidad operativa debe tener un ámbito de organización explícito. Moneda, distancias, horas, fechas y precisión de cantidades deben definirse antes de diseñar reportes o integraciones. El historial debe conservar quién cambió una lectura, un vencimiento o una clasificación y por qué.

## Pruebas de aceptación prioritarias

1. Un técnico intenta abrir por URL una OT de otro técnico y de otra organización: el resultado coincide con la política aprobada y no filtra datos.
2. Un conductor intenta administrar usuarios y exportar costos: el servidor rechaza las operaciones si su rol no las permite.
3. Una inspección con defecto crítico activa el flujo definido y conserva la evidencia de corrección y aprobación.
4. Dos técnicos consumen simultáneamente el último repuesto: no hay existencias negativas ni consumos duplicados.
5. Se reenvía la misma solicitud por pérdida de conexión: no se duplica la OT ni el movimiento asociado.
6. Un preventivo vence al alcanzar su umbral; al completar el servicio se conserva el historial y se calcula la siguiente fecha o lectura conforme a la regla.
7. Una organización vacía muestra estados sin datos coherentes; no inventa aprobación, utilización ni disponibilidad medida.
8. Las alertas y el informe de un mismo período usan la misma fuente y definición.
9. Cambiar idioma no deja claves internas; cambiar unidades no altera los valores físicos almacenados ni mezcla etiquetas.
10. Restaurar una copia de seguridad recupera datos y adjuntos con un procedimiento probado y tiempos definidos antes de producción.
