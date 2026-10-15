# SETRAM CMMS · módulos y correspondencia

La ampliación por campos, pestañas y flujos está detallada en [DIFERENCIAS_DETALLE.md](DIFERENCIAS_DETALLE.md). Incluye asistente de OT, fichas relacionadas, importaciones de catálogos, compras con varias líneas y recepción parcial, QR con aprobación, reportes PDF/programados, preferencias de avisos y recepción de resultados de visión por API propia.

Desde el 15 de octubre se dispone también de [catálogos iniciales](CATALOGOS_INICIALES.md): categorías observadas en BusCMMS y una base general de fallas, repuestos, tareas y programas de SETRAM. Los grupos y sus orígenes están separados; la cuenta consultada no contenía repuestos ni biblioteca de tareas para exportar.

Ampliación del 14 de octubre de 2026. Se utiliza el inventario obtenido en la auditoría autenticada de BusCMMS, conservado en `auditoria/revision_administrador_20261014_103322/menus.json`. El inventario contiene 32 destinos; las inspecciones se revisaron adicionalmente. Esta correspondencia organiza los menús de SETRAM y describe sus funciones actuales. No equivale a reproducir todos los servicios comerciales del proveedor.

| Destino de BusCMMS | Menú de SETRAM | Función local |
| --- | --- | --- |
| Comenzar | Comenzar / Configuración inicial | Pasos de configuración con conteos de registros reales |
| Panel de control | Panel de control | Ocho apartados, períodos, preferencias de widgets e indicadores reales |
| Executive Dashboard | Panel ejecutivo | Disponibilidad, reparación media, costos y distribución de fallas |
| Miembros del equipo | Personal y roles / Invitaciones / Aprobaciones | Cuatro roles, licencias, QR de solicitud, aprobación y reactivación |
| Management | Buses y flota | VIN, registro/seguro, asignación, vida útil, galería y ficha relacionada |
| Fleet Pulse | Fleet Pulse / Estado técnico | Estado, riesgo, antigüedad, vida referencial y alertas por bus |
| Calendario de flota | Calendario de flota | Día/semana/mes/año/agenda, filtros por bus y múltiples fuentes |
| HOS | HOS / Jornadas de conducción | Inicio, fin, descansos, horas netas y umbral interno configurable |
| Registros DVIR | Registros DVIR | Inspección pre/postoperacional, checklist versionado y generación de OT |
| Libro de registro | Libro de registro / Recorridos | Ruta, conductor, pasajeros, salida/llegada y odómetros |
| Gestión de neumáticos | Neumáticos | Serie, medida, montaje/km, profundidad, reencauche e inversión |
| Repuestos | Repuestos / Movimientos / Demandas | Catálogo importable, ubicación, reposición y consumos transaccionales |
| Suppliers | Proveedores | Contactos, vigencia, plazo, condiciones y registros relacionados |
| Purchase Orders | Compras / Líneas / Recepciones | Varias líneas, recepción parcial/completa y existencias sin duplicación |
| Combustible | Combustible | Surtidor, conciliación y eficiencia entre cargas a tanque lleno |
| Cumplimiento | Cumplimiento y vencimientos | Requisitos con fuente, responsable, plazo y evidencia; alertas documentales |
| Retiros del mercado | Campañas y retiros del fabricante | Registro de boletines, bus afectado, OT y evidencia al cierre |
| Telemática | Telemetría y ubicación | Lecturas GPS, posición, km, horas, velocidad, refrigerante y códigos de falla |
| Auditor IA | Auditor documental / IA | Extracción PDF, alertas locales y proveedor de IA opcional con consentimiento |
| Auditor de visión en vivo | Visión / Cámaras / Detecciones | Visor, observaciones manuales y resultados externos por API con revisión |
| Attachments | Documentos y vencimientos | Archivos de bus, funcionario, OT o generales; descarga autorizada |
| Informes | Informes / Programación / Descargas | Once tipos, CSV/PDF/ZIP, períodos y generación interna programada |
| Detalles de organización | Detalles de organización | Identidad, NIT, dirección, contacto, BOB, kilómetros y La Paz |
| Departamentos | Patios y departamentos / Turnos | Estado, responsable y horarios por día |
| Visibilidad de módulos | Visibilidad de módulos | Activación por organización, comprobada también en URLs y API |
| Billing / Upgrade | Facturación y pagos | Adaptación al CMMS municipal: comprobantes, presupuestos y contratos; no venta de suscripciones |
| Configuración | Configuración | Tarifa, umbrales internos, preferencias de avisos por tema/rol |
| Órdenes de trabajo | Órdenes / Tareas / Comentarios | Asistente de seis pasos, horas, presupuesto, costos, evidencia y cierre |
| Solicitudes de mantenimiento | Solicitudes de mantenimiento | Revisión/rechazo con motivo y conversión a OT sin duplicados |
| Programaciones PM | Mantenimiento preventivo | Planes por fecha, km y horas de motor; siguiente vencimiento al cierre |
| Service Programs & Tasks | Programas de servicio / Biblioteca de tareas | Procedimientos reutilizables y tareas de OT con horas y resultados |
| AI Predictive Maintenance | Mantenimiento predictivo | Evaluaciones explicables, cobertura de datos, recomendaciones y conversión a OT |
| Inspecciones (revisión adicional) | Informes de inspección / Listas de verificación / Recordatorios | Inspección de taller, plantillas y avisos internos periódicos |

Se añaden también incidentes de seguridad, dispositivos, claves de integración y notificaciones. Los menús se agrupan por dominio y se despliegan pulsando su nombre en la barra lateral. Los conductores y técnicos ven únicamente los módulos y registros autorizados para su rol.

## Telemetría

SETRAM utilizará archivos o una API propia, según la decisión del usuario. En **Telemetría → Importar CSV/JSON**, administradores y supervisores pueden descargar la plantilla CSV y cargar un archivo UTF-8 de hasta 1 MB y 200 lecturas. CSV admite coma o punto y coma; los decimales utilizan punto y las fechas incluyen zona horaria. JSON acepta la misma estructura de la API o una lista de lecturas. El archivo no necesita una clave de integración: se autoriza mediante la sesión del operador. Se registra la importación y, si alguna fila es inválida, se revierte todo el lote.

1. En **Telemetría → Dispositivos**, registra un identificador externo único, su bus y origen.
2. En **Integraciones y API**, un administrador crea una clave. Se muestra una vez; en la base se guarda su resumen SHA256. Puede revocarse desde el mismo módulo.
3. El proveedor o adaptador envía un lote JSON al endpoint siguiente. Una clave solo puede escribir en su organización y en dispositivos activos. El lote se guarda atómicamente. Los reintentos del mismo evento no duplican lecturas; reutilizar el evento con valores distintos se rechaza. Lecturas históricas no reducen odómetro ni horas de motor.

```http
POST /api/v1/telemetria/ingest/
Authorization: Bearer <clave-de-integracion>
Content-Type: application/json
```

```json
{"readings":[{"device_id":"GPS-BUS-001","event_id":"evento-unico-001","measured_at":"2026-10-14T12:00:00-04:00","latitude":"-16.5000000","longitude":"-68.1500000","odometer":"25000.0","engine_hours":"1400.0","speed":"0.0","temperature":"85.0","fault_code":""}]}
```

Ejemplo de formato, no datos operativos. `odometer` y la fecha con zona horaria son obligatorios; coordenadas se proporcionan juntas. Hasta 200 lecturas y 1 MB por lote. El endpoint devuelve identidades de lectura, indicador de repetición y conteo de nuevas. Otros endpoints de lectura conservan sesión y CSRF.

Las opciones Samsara y Geotab identifican el origen de datos normalizados; no ejecutan conectores nativos. La conexión real requiere identificar al proveedor y adaptar su protocolo. Sin datos recibidos, la pantalla muestra ausencia de lecturas.

`GET /api/v1/telemetria/` utiliza sesión autenticada y devuelve bus, dispositivo, evento, fecha, coordenadas, km, horas, velocidad, refrigerante y falla. Aplica el mismo alcance por rol que la pantalla. CSV exporta esos campos para revisar lecturas; la plantilla de importación utiliza los nombres de columna del protocolo de ingreso.

## Evaluaciones de mantenimiento

La primera implementación usa **Reglas SETRAM v1**, con índice de priorización de 0 a 100. Evalúa estado operativo, inspecciones críticas pendientes, OT abiertas, preventivos vencidos, incidentes, campañas y telemetría de las últimas 24 horas. Guarda las señales, sus puntos y fuentes en cada evaluación. El índice no es una probabilidad de avería ni un modelo entrenado.

Si faltan datos, el índice queda nulo. El nivel alto/crítico genera una recomendación pendiente, evitando duplicar recomendaciones activas. Un supervisor puede convertirla en OT o descartarla con una justificación. Una regla de temperatura de refrigerante a partir de 105 °C pide revisar la especificación del fabricante; no sustituye umbrales específicos por modelo de bus.

Para un modelo estadístico se necesitarán historial validado de fallas, reparaciones y sensores, definición de etiquetas, evaluación retrospectiva y calibración por familia de bus. No se atribuyen resultados de ese tipo a esta versión.

## Avisos e inspecciones

`servidor_local.py` inicia un proceso de recordatorios que revisa cada 60 segundos los vencimientos de inspección. Los avisos quedan en la bandeja del responsable y en el contador de la barra superior. Una ocurrencia no se duplica; un período acumulado genera un aviso y avanza a la siguiente fecha futura. Se puede ejecutar por separado:

```powershell
.\.venv\Scripts\python.exe manage.py procesar_recordatorios
.\.venv\Scripts\python.exe manage.py procesar_recordatorios --continuo --intervalo 60
```

La automatización es interna; no envía correos, SMS ni WhatsApp. En producción, el proceso continuo debe supervisarse como servicio separado.

## Documentos y visión

El auditor local calcula SHA256, detecta duplicados dentro de la organización, revisa vencimientos y extrae texto PDF mediante pypdf en un subproceso con límite de 15 segundos. Lee hasta 10 páginas y 30.000 caracteres. Escaneos, imágenes, archivos cifrados o extracción fallida requieren revisión humana; no hay OCR implementado.

La IA externa está deshabilitada por defecto. Para habilitarla, configurar localmente `SETRAM_AI_ENABLED=true`, `SETRAM_AI_API_KEY` y `SETRAM_AI_MODEL` y reiniciar. Solo se llama si el operador marca expresamente la casilla que autoriza el envío de hasta 6.000 caracteres extraídos. No se envía el archivo completo ni credenciales del sistema. Se usa Responses con salida estructurada y `store=false`; no se ha probado con un proveedor real en esta instalación. Referencia de implementación: [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses).

El visor de cámaras reproduce una fuente accesible desde el navegador. RTSP exige un gateway de video; HTTPS y controles del navegador pueden impedir fuentes incompatibles. Además de observaciones manuales, `/api/v1/vision/ingest/` recibe eventos de una cámara activa de la organización con clave Bearer que tenga el permiso `vision`. Guarda versión declarada del modelo, fecha, confianza y cajas normalizadas; rechaza conflictos, valida el lote y permite revisar detecciones. No ejecuta un modelo de visión. El esquema de ingreso se muestra en Integraciones y API.

## Arquitectura modular

`cmms/modules/` contiene once dominios: flota, personal, mantenimiento, inspecciones, inventario, operación, documentos, administración, telemetría, predictivo y seguridad. Cada dominio publica su `registry.py`. Los dominios nuevos separan también modelos, servicios, vistas y rutas. `portal/` agrupa las vistas de inicio y paneles.

`cmms/registry.py` compone el catálogo y comprueba claves únicas. `cmms/module.py` concentra permisos, visibilidad y alcance por organización/rol. El núcleo existente permanece en `core_models.py`; `models.py` importa el núcleo y los modelos de los dominios para conservar etiquetas de Django y tablas existentes. Formularios y CRUD compartidos evitan repetir acceso y auditoría. Las reglas transaccionales de cada dominio se incorporan mediante `modules/hooks.py` y acciones explícitas.

Para añadir un módulo: definir modelo y restricciones, importar el modelo en el puente, registrar catálogo/roles, implementar el alcance necesario, añadir servicios/rutas/plantillas si necesita pantalla propia, generar migración y probar flujos y permisos. No basta con crear un enlace de menú.

## Límites que siguen vigentes

Consumo GNV/electricidad, Google OAuth local, OCR, detección visual interna, predictivo entrenado, envío externo de mensajes y conectores nativos de proveedores requieren ampliación. HOS registra horas y umbrales internos; no certifica cumplimiento normativo. Los informes limitan cada consulta a 2.000 filas y los catálogos cada importación a 200 filas/1 MB. La aplicación sigue siendo un entorno local de desarrollo, pendiente de pruebas de carga, recuperación y despliegue con HTTPS para producción. Los límites de cada área están en [DIFERENCIAS_DETALLE.md](DIFERENCIAS_DETALLE.md).
