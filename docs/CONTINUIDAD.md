# Punto de continuidad

Estado al 15 de octubre de 2026. El trabajo siguiente continúa sobre el CMMS local de SETRAM; el repositorio contiene sus fuentes y migraciones, no una copia de la base de datos ni de las sesiones de acceso.

## Implementado y comprobado

- Aplicación Django/Bootstrap organizada en once dominios, con permisos por organización y rol.
- Migraciones `0001` a `0007`, verificadas con PostgreSQL temporal y aplicadas a la base local CMMS.
- 71 pruebas funcionales correctas y 30 pantallas de QA, incluyendo administrador, técnico, conductor y móvil.
- Definición de 122 elementos de catálogo: 26 categorías observadas en BusCMMS y, preparados para SETRAM, 32 tipos de falla, 40 familias de repuestos, 18 tareas y 6 programas.
- Carga aditiva e idempotente en `/catalogos/iniciales/`, con origen de los registros, sin stock ni precios inventados.
- Clasificación de fallas en solicitudes/OT, prellenado de campos y conservación al convertir la solicitud en OT.

## Próximos datos y decisiones

Falta identificar marcas, modelos y variantes de los buses de SETRAM para completar referencias OEM, dimensiones, compatibilidad y procedimientos. Los programas generales no definen intervalos; deben adaptarse a los manuales de la flota.

Las existencias reales se cargarán con movimientos de almacén. Las tarifas y costos requieren datos de SETRAM. Telemetría utilizará archivos o una API propia, según la decisión tomada. El modelo predictivo entrenado, detector visual interno, OCR y autenticación Google propia siguen pendientes de integración.

Para instalar y revisar el alcance, comenzar por `SETRAM_README.md`, `ESTADO_SETRAM.md` y `docs/CATALOGOS_INICIALES.md`. La configuración `.env`, los respaldos de CMMS, evidencias del visor y archivos subidos permanecen únicamente en el equipo local.
