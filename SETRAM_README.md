# SETRAM CMMS

Aplicación local para gestión de buses, construida con Django 6, Bootstrap 5.3.8 y PostgreSQL. Configurada para BOB, kilómetros, litros de diésel y America/La_Paz. La base de trabajo es **CMMS**, con nombre en mayúsculas. Los archivos del visor y la auditoría de BusCMMS se conservan separados.

## Instalación y acceso

1. PostgreSQL debe estar activo y la base `CMMS` creada.
2. Ejecuta `powershell -ExecutionPolicy Bypass -File .\instalar_cmms.ps1`.
3. Introduce las credenciales de PostgreSQL en la ventana local. Se guardan en `.env`, excluido del control de versiones.
4. El instalador aplica migraciones aditivas de Django, crea la organización SETRAM y una plantilla base que debe adaptarse a la operación. No carga buses ni registros ficticios.
5. Crea tu administrador en la siguiente ventana: esa contraseña es exclusiva de SETRAM CMMS.
6. Ejecuta `iniciar_cmms.cmd` y abre **http://127.0.0.1:8000**.

También puedes abrir `conectar_postgres.cmd` para guardar la conexión. Cambiar la conexión requiere reiniciar el servidor. Las tablas de la aplicación usan prefijo `cmms_`; no se elimina ni se migra automáticamente información de otros sistemas. Se debe inspeccionar la base antes de la primera migración si contiene tablas con esos nombres.

## Módulos disponibles

La versión modular amplía este inventario con telemetría y API por clave, mantenimiento predictivo mediante reglas explicables, jornadas/HOS, recorridos, cumplimiento, campañas del fabricante, incidentes, recordatorios automáticos internos, auditoría documental, visor de cámaras, invitaciones, presupuestos y contratos. Consulta **[correspondencia completa con BusCMMS](docs/MODULOS_SETRAM.md)** para la cobertura y configuración de cada función.

La revisión de detalles en todos los módulos está en **[comparación de campos y flujos](docs/DIFERENCIAS_DETALLE.md)**. Las listas incluyen búsqueda, filtros, tabla/tarjetas, analítica, actividad y PDF según permisos. Las fichas muestran registros relacionados; la búsqueda del encabezado consulta los módulos autorizados. El panel tiene ocho apartados, períodos y preferencias de widgets por usuario.

La base CMMS incluye catálogos iniciales: 26 categorías observadas en BusCMMS y, preparados para SETRAM, 32 tipos de falla/síntomas, 40 familias de repuestos, 18 tareas y 6 programas sin frecuencias asignadas. Cada registro conserva su origen. Los costos, stock y mínimos comienzan en cero; las referencias OEM y compatibilidades deben completarse por modelo. El administrador dispone de `/catalogos/iniciales/` para revisar y cargar faltantes sin sobrescribir registros. Consulta [CATALOGOS_INICIALES.md](docs/CATALOGOS_INICIALES.md).

- Panel con disponibilidad actual, inspecciones del mes, OT e indicadores de planes vencidos y existencias bajas. Sin registros se muestra «Sin datos».
- Flota: código, VIN validado, placa, marca, modelo, año, capacidad, odómetro/horas, ruta, energía, patio, conductor, vigencia de registro/seguro y vida útil referencial. Galería de hasta cinco fotos por bus, archivos JPG/PNG de hasta 10 MB y QR que conserva el control de acceso.
- Personal con roles Administrador, Supervisor, Técnico y Conductor; código de funcionario, departamento y licencia. QR para solicitar ingreso como conductor/técnico, aprobación manual de identidad y solicitudes de reactivación. Cambio de contraseña propio en `/perfil/clave/`.
- Inspecciones con plantillas versionadas, resultado por punto, hallazgos y firma por nombre. El resultado se deriva de los puntos; un defecto genera OT y un defecto crítico inmoviliza el bus.
- Solicitudes con revisión y motivo de rechazo, convertibles a OT sin duplicados. Asistente de OT de seis pasos: datos básicos, tareas/duración, información adicional, costos/presupuesto, notas/evidencia y revisión. Tareas de biblioteca/programa, responsable, categoría de falla, mano de obra manual o por horas, costos externos, comentarios, consumo de repuestos y aprobación de cierre.
- Programas de servicio reutilizables y preventivos por fecha, km u horas de motor, generación de OT sin duplicados y avance del siguiente vencimiento al aprobar el cierre.
- Repuestos, proveedores y movimientos de almacén. Entradas y salidas usan bloqueo transaccional para evitar existencias negativas; las salidas se imputan a una OT.
- Compras con una primera línea y líneas adicionales; recepciones parciales/completas por línea, cantidades pendientes y entradas de almacén sin duplicación por reintentos. Las demandas automáticas de reposición se activan por repuesto; un responsable debe autorizar la creación de la OC local.
- Combustible diésel en litros y Bs con odómetro, surtidor, marca de tanque lleno y conciliación. Eficiencia en L/100 km entre dos cargas a tanque lleno, incluyendo cargas parciales intermedias. GNV y buses eléctricos necesitan módulos de consumo en sus propias unidades.
- Neumáticos con medidas, montaje/km, profundidad inicial/actual y reencauches; documentos de bus, funcionario u OT con descarga autorizada y vencimientos; patios con turnos y responsables.
- Calendario día/semana/mes/año/agenda con filtros por bus y fuente. Once tipos de informes, consulta por período, CSV/PDF, ZIP de PDF y generación interna programada. Cada informe admite hasta 2.000 registros.
- Auditoría de altas, ediciones, exportaciones y cambios de estado.

## Reglas de acceso

Administrador gestiona configuración y usuarios. Supervisor gestiona operación y aprueba cierres. Técnico ve sus OT asignadas, sus inspecciones/solicitudes, buses vinculados a sus OT o recordatorios, recursos de almacén y documentos aplicables; puede editar la resolución de sus OT, completar tareas y enviarlas a revisión, pero no cerrarlas. Conductor consulta buses asignados y sus registros de inspecciones, solicitudes, combustible, jornadas y recorridos. Los datos de telemetría y evaluaciones se limitan a buses visibles para cada rol; la bandeja de avisos siempre es privada de su destinatario. Ambos roles operativos ven plantillas activas y documentos generales de la organización. Cada consulta limita organización y ámbito antes de buscar un identificador, incluso en CSV, API y archivos.

Las listas de técnicos pueden contener buses de OT históricas asignadas; no representan una restricción únicamente a trabajo en curso. No hay eliminación de registros operativos en la interfaz. La desactivación de cuentas y de planes/plantillas conserva historia.

## Interfaz programática

API de sesión, versión inicial:

```text
GET /api/v1/buses/
GET /api/v1/ordenes/?pagina=1&estado=en_progreso
GET /api/v1/ordenes/42/
POST /api/v1/ordenes/42/estado/
Content-Type: application/json
{"estado":"revision"}
```

El POST de estado requiere sesión autenticada, cookie CSRF y encabezado `X-CSRFToken`. Las respuestas de lectura incluyen valores de máquina y etiquetas en español, 25 filas por página y conteo. `POST /api/v1/telemetria/ingest/` utiliza una clave Bearer revocable creada por un administrador y acepta lecturas normalizadas. `POST /api/v1/vision/ingest/` requiere habilitar expresamente el permiso de visión en la clave y acepta resultados de un motor externo con identidad de evento, versión del modelo, fecha, confianza y cajas normalizadas. La instalación no ejecuta un detector visual; muestra la procedencia de los resultados y permite revisión humana. El contrato aparece en Integraciones y API. Las claves se muestran una sola vez. La cuenta de BusCMMS/Google no se reutiliza; OAuth de Google no está configurado.

Los catálogos de buses, repuestos, neumáticos, proveedores, programas, tipos de falla, categorías y tareas pueden importarse desde las listas mediante CSV/JSON: lote de hasta 200 filas/1 MB, validación integral, referencias de la misma organización y deduplicación por archivo. La importación no reemplaza registros existentes ni introduce existencias al margen de los movimientos de almacén.

## Verificación

`validar_postgres.py` crea un cluster PostgreSQL temporal bajo `.validacion_postgres`, limitado a loopback y puerto libre, genera migraciones y ejecuta pruebas. No se conecta a CMMS. El cluster se detiene al terminar. Requiere las herramientas PostgreSQL 18 en su instalación habitual de Windows.

Con permisos para crear una base de prueba, `python manage.py test cmms` usa una base `test_CMMS` separada. No debe configurarse el nombre de la base de prueba como CMMS. Las pruebas comprueban alcance por organización/rol, cierre de OT, inspecciones críticas, reintentos, existencias insuficientes, preventivos, CSRF, exportación e indicadores sin datos.

## Alcance de esta versión

Es una implementación operativa local. La inspección firma por nombre, sin firma digital certificada. Telemetría admite archivos o API propia; falta cargar datos reales de SETRAM. El predictivo usa reglas explicables y estimaciones económicas con fuente registrada; no hay modelo estadístico entrenado ni ahorro real calculado sin evidencia. Los avisos y reportes programados son internos. Visión recibe resultados de un motor externo y conserva las observaciones manuales; no incorpora un detector entrenado. OCR, Google OAuth, mensajes externos y conectores nativos siguen pendientes. La IA documental externa requiere configuración y autorización. Las medidas de concurrencia y autorización deben ampliarse con pruebas de carga y recuperación antes de un despliegue de producción.

El lanzador utiliza `servidor_local.py`, activa depuración únicamente para ese proceso y lo limita a 127.0.0.1:8000. Esto permite servir Bootstrap y usar cookies de sesión por HTTP local, aunque `.env` o el entorno indiquen DEBUG=false. Un despliegue de red debe utilizar `setram.wsgi` con HTTPS, configuración de hosts, `DEBUG=false`, servidor WSGI, servicio de archivos estáticos, copias de seguridad y operación de PostgreSQL; no se publica automáticamente en internet.
