# Estado de SETRAM CMMS

Implementación local del 14 de octubre de 2026; catálogos iniciales incorporados el 15 de octubre de 2026.

## Resultado comprobado

- PostgreSQL **CMMS** conectada. Estaba vacía antes de aplicar migraciones; no se eliminó información existente.
- Migraciones `0001` a `0007` aplicadas. La `0007` agrega catálogos de tipos de falla/categorías, clasificación en solicitudes/OT, especificación de repuestos y origen de los elementos.
- Una organización y dos cuentas existentes conservadas al ampliar CMMS. Se conserva la plantilla base de inspección.
- Cero buses ficticios en CMMS. Los datos de las capturas de validación pertenecen a una base temporal separada.
- Servidor local en **http://127.0.0.1:8000**, acceso y archivos Bootstrap/CSS con HTTP 200; `/salud/` confirma base disponible.

## Cobertura funcional

Catálogo modular en **11 dominios**, además de panel principal, calendario, informes y configuración. La correspondencia con los destinos de BusCMMS está en [docs/MODULOS_SETRAM.md](docs/MODULOS_SETRAM.md). La comparación de detalles por cada área, con las diferencias que siguen pendientes, está en [docs/DIFERENCIAS_DETALLE.md](docs/DIFERENCIAS_DETALLE.md). Los menús no se utilizan como medida de equivalencia funcional.

Flota, equipo e invitaciones; solicitudes, OT y tareas; DVIR, inspecciones de taller, listas de verificación y recordatorios; preventivos por fecha/km/horas; programas y biblioteca de tareas; almacén, proveedores y compras; combustible; neumáticos; documentos y auditor documental; patios; jornadas/HOS y recorridos; telemetría; mantenimiento predictivo; cumplimiento, campañas e incidentes; cámaras y observaciones; notificaciones; visibilidad de módulos; presupuestos, contratos, comprobantes y auditoría.

Se implementaron organización y alcance de consulta por rol en servidor, bloqueo de buses por inspección crítica, cierre de OT aprobado, avance de preventivos al cierre, bloqueo transaccional de existencias, deduplicación de formularios y recepción de compras, descargas autorizadas y registro de eventos.

Telemetría utiliza archivos CSV/JSON o una API propia, según la decisión del usuario. La importación y el ingreso por clave validan todo el lote, evitan duplicados y conservan el mayor odómetro/horas. Las claves son revocables y se almacenan como resúmenes SHA256. Las evaluaciones de mantenimiento guardan reglas y fuentes; un riesgo alto/crítico produce recomendaciones convertibles a OT. Un incidente crítico genera OT e inmoviliza el bus. Las tareas pendientes bloquean revisión/cierre de la orden.

La ampliación incluye filtros, tabla/tarjetas, analítica, actividad y PDF en las listas; fichas relacionadas; búsqueda general; ocho apartados y widgets del panel; calendario con cinco vistas; VIN, seguro/registro, vida referencial, galería y QR de bus; licencias y QR de solicitud de ingreso con aprobación manual; turnos de patios; asistente de OT de seis pasos, tareas de biblioteca, horas/costos, presupuesto y comentarios; revisión de solicitudes; compras con varias líneas y recepciones parciales; demandas de reposición; eficiencia por cargas a tanque lleno y conciliación; detalle de neumáticos; once tipos de informes PDF/CSV/ZIP y programación; importación atómica de catálogos; matriz de avisos y umbrales internos.

El servidor local inicia la tarea periódica cada 60 segundos para recordatorios, avisos KPI habilitados, reportes programados y demandas de reposición activadas por repuesto. El auditor extrae texto PDF con tiempo limitado y verifica vencimientos/duplicados. La IA externa requiere configuración y autorización expresa. Las cámaras muestran fuentes configuradas y observaciones manuales; la API propia recibe resultados de un detector externo, con versión de modelo, confianza, cajas y revisión humana. No ejecuta un detector interno.

El 15 de octubre se cargaron en CMMS **26 categorías de referencia, 32 tipos de falla/síntomas, 40 familias de repuestos, 18 tareas y 6 programas de revisión**. Solo las categorías proceden de las opciones visibles de BusCMMS; los demás son una base general de SETRAM. La cuenta consultada mostraba cero repuestos, programas y tareas. Cada alta conserva su origen. No se cargaron precios OEM, stock, mínimos, duraciones, frecuencias ni movimientos ficticios. Los programas requieren adaptación al modelo del bus.

La pantalla `/catalogos/iniciales/` permite revisar y agregar faltantes por grupo; los registros existentes se conservan y una segunda carga comprobada generó cero altas. El tipo de falla prellena campos vacíos y determina el sistema afectado; se conserva al convertir una solicitud en OT. Las categorías sugieren valores en el formulario de repuestos. Guía: [docs/CATALOGOS_INICIALES.md](docs/CATALOGOS_INICIALES.md).

## Validación

**71 pruebas funcionales correctas** en PostgreSQL aislado. Resultado completo: `RESULTADO_PRUEBAS.txt`. A las 64 pruebas anteriores se añadieron siete que verifican previsualización sin escritura, carga con stock cero/origen, reintentos, conservación de datos manuales y ámbito de organización, permisos/visibilidad/CSRF, reversión del lote completo ante errores, clasificación de fallas y conversión a OT, importaciones nuevas y selección de grupos.

**30 pantallas de QA visual**, incluyendo catálogos iniciales, tipos de falla, alta de repuesto y OT prellenada. Se verificaron escritorio, tres roles y móvil de 390 px sin desbordamiento en panel y diez módulos. La selección de falla prellenó título, descripción y sistema; el asistente avanzó al paso de tareas sin guardar una OT. Evidencias en `pruebas_visuales/`; resultado en `pruebas_visuales/resultado.json`. El PostgreSQL temporal se detuvo al terminar.

Se generaron respaldos lógicos de CMMS y se comprobaron sus índices antes de cada ampliación. La ampliación del 14 de octubre conservó los conteos de las 45 tablas previas y alcanzó 59 tablas. La del 15 de octubre agrega dos tablas, para un total de 61; la carga solo añade catálogos, relaciones de plantillas y auditoría. Los conteos operativos se conservaron, sin crear buses, OT, planes ni movimientos. Evidencias: `docs/estado_migracion_detalles.json` y `docs/estado_catalogos_cmms.json`. Respaldos en `.respaldos_cmms/`, excluidos del control de versiones; el índice validado no sustituye una prueba de restauración completa.

La salud, archivos estáticos y rutas nuevas protegidas del servidor reiniciado se verificaron por HTTP: `docs/verificacion_servidor_detalles.json` y `docs/verificacion_catalogos_local.json`. Las API de ingreso rechazan peticiones sin clave; la carga de catálogos rechaza POST sin CSRF. Hay una instancia del servidor y una tarea periódica; cada una utiliza el redirector del entorno virtual y su proceso Python delegado en Windows.

Estas comprobaciones no equivalen a pruebas exhaustivas de seguridad, carga, recuperación o funcionamiento con datos reales de toda la flota.

## Inicio posterior

Ejecutar `iniciar_cmms.cmd`. La cuenta de acceso pertenece a SETRAM; no utiliza la contraseña de PostgreSQL ni la sesión de BusCMMS. `crear_admin.cmd` sirve para la creación inicial cuando no exista administrador. Las nuevas cuentas se crean desde Personal y roles.

## Pendiente de integración o ampliación

La API y la importación de archivos están implementadas; aún deben cargarse datos reales de la flota. El predictivo usa reglas explicables, sin modelo estadístico entrenado. Detector visual interno, OCR, Google OAuth local, mensajes externos, conectores nativos GPS y consumo GNV/electricidad necesitan ampliación. La IA documental opcional no se ha probado con un proveedor real. La API de sesión permite lecturas y transiciones de OT; la API Bearer recibe telemetría o resultados de visión según sus permisos. Los límites y diferencias de cada área se especifican en la comparación de detalles.

La plantilla preoperacional debe revisarse con el equipo SETRAM antes de usarse en operación. El entorno actual es local y de desarrollo. Guía de instalación, roles, API y despliegue: `SETRAM_README.md`.
