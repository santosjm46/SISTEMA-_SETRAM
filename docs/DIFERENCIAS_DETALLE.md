# Comparación de detalles: BusCMMS y SETRAM

Revisión del 14 de octubre de 2026, America/La_Paz. El usuario solicitó revisar las diferencias en todos los módulos. La revisión autenticada volvió a recorrer 34 destinos, incluyendo el alta de bus que estaba abierta en el visor. Evidencias: `auditoria/detalle_20261014_164621/`. Se conserva además la auditoría inicial y sus formularios.

Algunas páginas recientes solo cargaron la navegación dentro del tiempo de espera; no se atribuye a ellas ausencia de funciones. En esos casos se utiliza la evidencia completa guardada en la primera auditoría. La referencia muestra controles visibles; no demuestra cómo valida o automatiza el proveedor sus operaciones. No se enviaron formularios ni se modificaron datos de BusCMMS.

La primera implementación de SETRAM cubría menús y flujos básicos. Esta ampliación agrega controles y operaciones dentro de los módulos. El número de menús no se utiliza como medida de equivalencia funcional.

| Área de referencia | Detalles incorporados en SETRAM | Límites o integración pendiente |
| --- | --- | --- |
| Comenzar | Pasos con conteos de datos reales y enlaces a configuración, flota, equipo, checklist, planes y telemetría | El recorrido interactivo superpuesto de la referencia no se reproduce |
| Panel principal | Ocho apartados, período semana/mes/trimestre, widgets por usuario, accesos y consulta de registros | No se inventan porcentajes de utilización, entregas ni salud sin datos |
| Panel ejecutivo | Períodos, costos con servicios externos, ciclo medio, duración real de reparación y sistemas afectados | MTBF requiere definir y registrar eventos de falla; no se publica una cifra con una flota sin historial |
| Equipo | Filtros por rol, código de funcionario, patio, licencia/categoría/vencimiento, invitaciones, QR, solicitudes y aprobación de ingreso, reactivaciones | Acceso local con usuario/contraseña; Google OAuth requiere configuración propia |
| Alta y ficha de bus | VIN validado, vencimiento de registro/seguro, ingreso al servicio, vida de referencia, cinco fotos, historia relacionada y QR de mantenimiento/inspección | No hay decodificación VIN remota ni reconocimiento de marca/modelo desde fotografía |
| Fleet Pulse | Orden de atención por riesgo, filtro de riesgo, antigüedad, vida restante respecto a una referencia configurada y mantenimiento relacionado | La vida restante es una referencia por años configurada por SETRAM, sin modelo de degradación entrenado |
| Calendario | Día, semana, mes, año y próximos 90 días; filtros por bus/tipo; OT, PM, documentos, inspecciones, recordatorios, requisitos, campañas, recorridos, seguros y registros | Los eventos proceden de los registros locales; no se conectó un calendario externo |
| HOS | Jornadas, descansos, conducción neta, política interna, filtros, analítica, actividad y exportaciones | No certifica cumplimiento de reglas HOS estadounidenses ni normas bolivianas |
| DVIR | Formulario por secciones, ubicación, plantilla inicial, progreso, marcado conforme, hallazgos/firma, filtros por resultado y vínculo con reparación | Se mantiene el flujo explícito defecto → OT; no se cambió automáticamente un defecto menor a un PM recurrente |
| Libro de registro | Ruta, conductor, pasajeros, salida/llegada, odómetros, filtros por período, estados, analítica y actividad | No se implementó despacho de cargas comerciales ajeno a la operación de buses |
| Neumáticos | Medida, fecha/km de montaje, profundidad inicial/actual, reencauches, estado, inversión, umbral configurable, importación y análisis | No se calcula ROI de fabricante sin historial de costos de reencauche y reemplazo |
| Repuestos | Categoría, fabricante, ubicación, existencias, mínimos, valor referencial, importación atómica y demanda automática configurable | Las existencias se cambian por movimientos; importar un catálogo no sobrescribe stock |
| Proveedores | NIT, contacto, dirección, estado, plazo de entrega, condiciones de pago, filtros, importación e historial de compras/partes | No se envían pedidos externos ni correos a proveedores |
| Compras | Varias líneas, recepción por cantidad/línea, pendientes, entradas de almacén, protección contra reintentos y sobre-recepción, recepción completa | No se ejecutan pagos ni compromisos con proveedores externos |
| Combustible | Surtidor, tanque lleno/parcial, consumo L/100 km, conciliación pendiente/verificada/observada, evidencias y análisis | Tarjetas comerciales y descarga de estados de cuenta requieren un conector específico |
| Cumplimiento | Categoría, impacto, responsable, fecha, evidencia, filtros, analítica, calendario y documentos ligados a personas | Los requisitos se ingresan con sus fuentes; no se afirma consultar automáticamente leyes vigentes |
| Campañas y retiros | Tipo, fabricante, fuente/boletín, bus afectado, fecha, estado, OT y evidencia | No se conectaron bases externas de campañas de fabricantes |
| Telemetría | Dispositivos, claves revocables con capacidades, carga CSV/JSON, API propia, fechas/procedencia, posición, km, horas, velocidad, temperatura y fallas | Se conserva la elección del usuario: archivos/API propia; los conectores nativos de fabricantes no se conectaron |
| Auditor documental | PDF, vencimientos, duplicados, trazabilidad, fuente, hallazgos y texto; proveedor IA opcional autorizado por el operador | OCR, clasificación automática y lectura de imágenes requieren ampliación; no hay proveedor IA real configurado |
| Visión | Cámara/video, observaciones, API propia de capturas y detecciones, cajas normalizadas, placa/bus, confianza declarada, motor/fecha y revisión humana | El modelo detector debe conectarse desde la fuente de SETRAM; no se simulan detecciones |
| Adjuntos | Vinculación a bus, persona y OT; documentos privados de personas; descargas autorizadas y vencimientos | JPEG, PNG y PDF; no se habilitaron todos los formatos de la referencia |
| Informes | Once informes con consulta de período, PDF/CSV, ZIP conjunto, programación y descargas privadas de PDFs generados | Hasta 2.000 filas por informe; programación interna sin envío de correo |
| Organización | NIT, dirección, contacto, teléfono, moneda/unidades/zona de SETRAM y conteos | Logo institucional personalizable y operación SaaS multiempresa requieren ampliación |
| Departamentos | Patios activos/inactivos, turnos por día, responsable, horas y registros asociados | No hay planificación automática de dotación de personal |
| Visibilidad | Controles por organización, guardas en rutas/API, menús según rol y administración recuperable | La visibilidad de una función no equivale a certificar todas sus dependencias operativas |
| Facturación | Presupuestos, contratos, comprobantes, referencia de pago y ejecución presupuestaria en Bs | Se adapta al mantenimiento municipal; no se vende la suscripción SaaS de BusCMMS |
| Configuración | Identidad, tarifa por hora, criterios internos de neumáticos/KPI y matriz de avisos por tipo/rol | Avisos internos; SMTP, SMS y otros canales externos no están configurados |
| OT | Asistente de seis pasos, reportante, plantilla, tareas, duración, sistema/taller, presupuesto, cálculo por hora/manual, terceros, notas, comentarios y archivos | El cierre continúa sujeto a revisión y evidencia, con tareas pendientes bloqueantes |
| Solicitudes | Prioridad, revisión, motivo de rechazo, conversión sin duplicados, QR, indicadores y actividad | No se enviaron solicitudes al sistema externo |
| PM | Fecha/km/horas, programa, tareas de biblioteca, OT de ejecución, vencimientos, calendario e historial | La siguiente programación avanza al aprobar el cierre |
| Programas y biblioteca | Procedimientos, tareas reutilizables, frecuencias y aplicación a OT/planes; analítica y registros asociados | Las tareas se gestionan por SETRAM, sin catálogo técnico externo sincronizado |
| Predictivo | Vista general, distribución/tendencia, procedencia, historial, recomendaciones, acciones/OT y retorno estimado con supuestos documentados | Reglas explicables; no es un modelo estadístico entrenado ni una probabilidad de falla |
| Inspección de taller y recordatorios | Formulario por secciones, checklist versionado, firma, flujo de defectos, bandeja, avisos por rol, KPI diarios y actividad | Requiere adaptar las listas de verificación a los procedimientos reales de SETRAM |

## Revisión dentro de cada módulo

Los módulos disponen de vistas de registros, analítica y actividad, filtros de estado/tipo/prioridad/persona/proveedor/patio/fechas cuando corresponden, tabla o tarjetas y PDF/CSV de la consulta. Las fichas enlazan registros relacionados con su ámbito de acceso. Las consultas, API y exportaciones comparten filtros y organización/rol.

En el asistente de OT, los primeros cinco pasos agrupan información básica, tareas/duración, datos adicionales, costos/presupuesto y notas/evidencia; el sexto muestra la revisión antes de guardar. Los pasos no envían datos hasta la confirmación final. Las plantillas crean tareas de trabajo y las tareas pendientes bloquean revisión/cierre.

La importación de catálogos admite buses, neumáticos, repuestos, proveedores y programas. Se requieren columnas de la plantilla e identificadores internos para relaciones. Cada archivo se procesa atómicamente, valida organización y guarda su SHA256 para evitar repetir una importación.

Las demandas de repuestos se generan solo al habilitar esa regla en cada parte. La demanda pendiente se conserva sin duplicados y requiere una acción del supervisor para crear la compra. Las recepciones parciales utilizan un token por formulario y no permiten superar lo pendiente.

Las solicitudes QR de equipo no crean una cuenta activa: guardan la petición y una contraseña con hash hasta la aprobación del administrador. Solo permiten solicitar Técnico o Conductor. La contraseña no se muestra en fichas ni exportaciones; al decidir la solicitud se elimina el hash de la petición. Las reactivaciones requieren decisión y revisión de identidad.

La API de visión acepta capturas con hasta 50 objetos y necesita una clave habilitada para `vision`. Registra motor declarado, fecha, caja normalizada, confianza y vínculo con un bus de la organización. Un evento repetido no crea duplicados; contenido distinto bajo la misma identidad se rechaza. La fuente debe proporcionar el resultado del detector: la interfaz no atribuye a SETRAM un análisis que no se ejecutó.

## Validación y datos

La ampliación del 14 de octubre pasó 64 pruebas y 26 capturas en PostgreSQL temporal, con datos exclusivos de QA. Las migraciones `0005` y `0006` se aplicaron a CMMS después de generar un respaldo lógico y comprobar su índice. La incorporación de catálogos del 15 de octubre amplió la validación a 71 pruebas y 30 pantallas, con migración `0007` y 122 elementos de catálogo; su origen se detalla en [CATALOGOS_INICIALES.md](CATALOGOS_INICIALES.md). Los conteos operativos se conservaron y las rutas del servidor reiniciado se verificaron por HTTP. Evidencias: `RESULTADO_PRUEBAS.txt`, `pruebas_visuales/resultado.json`, `docs/estado_migracion_detalles.json`, `docs/estado_catalogos_cmms.json`, `docs/verificacion_catalogos_local.json` y `ESTADO_SETRAM.md`.

La revisión por función debe continuar para capacidades que dependen de modelos, fuentes externas o políticas de operación. Esas dependencias se indican en la tabla; no se presentan como integraciones conectadas.
