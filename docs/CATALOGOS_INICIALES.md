# Catálogos iniciales de SETRAM

Consulta autenticada del 15 de octubre de 2026. En la sesión autorizada de BusCMMS, Repuestos, Programas y Task Library mostraron cero registros. El selector de categorías sí ofreció 26 opciones. La evidencia local está en `auditoria/catalogos_20261015_155104/inventario.json`.

Se consultó la interfaz; no se accedió directamente a la base de datos del proveedor ni se enviaron formularios. Las categorías se tradujeron al español. Se conservaron sus códigos y etiquetas originales para poder verificar su procedencia.

| Catálogo | Elementos | Origen |
| --- | ---: | --- |
| Categorías de repuestos | 26 | Opciones observadas en BusCMMS |
| Tipos de falla y síntomas | 32 | Base general preparada para SETRAM |
| Familias de repuestos | 40 | Base general preparada para SETRAM |
| Biblioteca de tareas | 18 | Base general preparada para SETRAM |
| Programas de revisión | 6 | Base general preparada para SETRAM |

Los códigos `GEN-...` son internos. No son números OEM ni acreditan compatibilidad con ningún modelo de bus. Un registro genérico debe completarse con la especificación o convertirse en una referencia específica antes de utilizarse en compras y montaje. Se incluye un campo de especificación/compatibilidad pendiente.

Las existencias, costos referenciales, mínimos y duraciones comienzan en cero. Costo cero significa sin cotización en estos registros de origen, no precio de mercado. No se crean movimientos, proveedores, buses, fallas reales, OT, planes preventivos ni períodos de mantenimiento. Los programas son plantillas para adaptar; sus intervalos permanecen en cero. Un repuesto sin mínimo configurado no genera una alerta de bajo mínimo.

## Uso en la aplicación

Con una cuenta de administrador, abre **Catálogos iniciales** desde las pestañas de los módulos, o visita `/catalogos/iniciales/`. Cada grupo muestra qué se agregará y qué ya existe, con el origen de cada fila. Se pueden seleccionar los grupos deseados.

La carga solo agrega faltantes: compara código interno y nombre, conserva las filas existentes y registra altas y origen en auditoría. Usa una transacción y bloqueo por organización; un error revierte el lote completo. Repetir la acción no duplica los elementos. La visibilidad de módulos también se comprueba en servidor.

Los tipos de falla se administran en **Mantenimiento → Tipos de falla y síntomas**. Se pueden elegir en solicitudes y OT. Al seleccionar uno en un formulario vacío, se sugieren título y descripción; el sistema afectado de la OT se deriva del catálogo en el servidor. El usuario puede redactar el reporte y el técnico debe confirmar el diagnóstico. Convertir una solicitud a OT conserva la clasificación. Desactivar un tipo lo retira de nuevas selecciones y conserva su referencia histórica.

Las categorías se administran en **Inventario → Categorías de repuestos** y aparecen como sugerencias al escribir la categoría de un repuesto. Se mantienen las categorías de texto existentes. También se pueden importar CSV/JSON de tipos de falla, categorías y tareas desde sus listas, además de los catálogos previamente admitidos.

## Archivos y mantenimiento

La definición está en `catalogos/setram_base_v1.json`. Cada registro cargado conserva su origen en `catalog_source`; los creados manualmente no se atribuyen al proveedor. La carga deja constancia en `CatalogImport` y auditoría.

El comando siguiente previsualiza la carga sin escribir; los identificadores deben corresponder a un administrador activo de la organización seleccionada:

```powershell
.\.venv\Scripts\python.exe manage.py cargar_catalogos_setram --organizacion <id> --usuario <id>
```

Añadir `--aplicar` realiza la carga. `--modulos tipos_falla repuestos` limita los grupos. Las cantidades y costos reales se introducen posteriormente mediante los flujos de almacén y compras.

El respaldo, los conteos y el resultado de la carga local se guardan en `docs/estado_catalogos_cmms.json`. Las pruebas funcionales se ejecutan en PostgreSQL temporal; sus datos no se incorporan a CMMS.

Se cargaron los 122 elementos en CMMS y se comprobó que una segunda carga produjo cero altas. Los conteos operativos existentes se conservaron. La migración `0007` es aditiva. Pasaron 71 pruebas y 30 pantallas de QA, incluido el prellenado de una OT sin guardarla y vistas móviles de 390 px. El servidor reiniciado pasó las comprobaciones de `docs/verificacion_catalogos_local.json`.
