# SETRAM CMMS

Sistema modular para gestión de buses y mantenimiento de SETRAM, desarrollado con Python, Django, Bootstrap y PostgreSQL. Configuración regional: bolivianos (BOB), kilómetros y America/La_Paz.

Incluye flota, personal y roles, solicitudes y órdenes de trabajo, inspecciones/DVIR, preventivos, almacén y compras, combustible, neumáticos, documentación, cumplimiento, telemetría mediante archivos/API propia, mantenimiento predictivo por reglas e informes.

## Instalación del CMMS

Requiere Windows, Python 3.14 y PostgreSQL 18 para el entorno local validado.

```powershell
git clone https://github.com/santosjm46/SISTEMA-_SETRAM.git
cd SISTEMA-_SETRAM
powershell -ExecutionPolicy Bypass -File .\instalar_cmms.ps1
```

El instalador prepara el entorno, solicita la conexión a la base `CMMS`, aplica migraciones y abre la creación del administrador. Las credenciales se guardan únicamente en el archivo local `.env`. Después ejecuta `iniciar_cmms.cmd` y abre **http://127.0.0.1:8000**.

El repositorio contiene código, migraciones y definiciones de catálogos. La base PostgreSQL, sus respaldos, archivos subidos, credenciales y sesiones del visor permanecen locales. Una instalación nueva necesita su propia configuración y sus cuentas.

## Documentación y validación

- [Instalación, módulos y API](SETRAM_README.md).
- [Estado y límites de implementación](ESTADO_SETRAM.md).
- [Correspondencia de módulos](docs/MODULOS_SETRAM.md).
- [Catálogos iniciales y procedencia](docs/CATALOGOS_INICIALES.md).
- [Punto de continuidad](docs/CONTINUIDAD.md).

La última validación completó 71 pruebas funcionales en PostgreSQL temporal y 30 pantallas de QA. Para repetirla, instala también las dependencias del visor con `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` y ejecuta `.\.venv\Scripts\python.exe validar_postgres.py`. El ejecutor utiliza una base temporal separada de CMMS. Los resultados, capturas y registros de la instalación local no se publican.

El servidor incluido escucha en loopback para desarrollo local. El predictivo utiliza reglas; la visión recibe resultados de un modelo externo por API. Los conectores externos y el despliegue de producción requieren configuración adicional.

## Visor local de auditoría BusCMMS

Requiere Windows, Python y Google Chrome. No es un formulario de contraseñas: abre Chrome normal con un perfil exclusivo y conecta Playwright después del inicio de sesión manual. Google puede rechazar un acceso; en ese caso usa tu navegador habitual y comparte capturas manualmente. No se eluden restricciones de Google.

### Uso del visor

1. Ejecuta `powershell -ExecutionPolicy Bypass -File .\instalar_visor.ps1` desde esta carpeta (el cambio de política solo afecta ese proceso).
2. Abre `iniciar_visor.cmd`.
3. Pulsa **Abrir Chrome**: abre `/es/login/admin`, el portal de administrador.
4. Pulsa **Iniciar con Google**: conecta el visor y pulsa el botón de Google en BusCMMS. Selecciona tu cuenta y completa el acceso directamente en Chrome. También puedes pulsar el botón del sitio manualmente y luego **Conectar sesión**. Mantén una sola pestaña de BusCMMS para evitar ambigüedad.
5. Navega al módulo que revisarás y pulsa **Capturar página**.

Cada captura guarda imagen, texto y metadatos en `auditoria`. `auditoria/ultima_captura.json` identifica la evidencia más reciente. Los campos de entrada se ocultan en la imagen y se excluyen del texto. Otros datos visibles de la empresa sí se guardan. No se capturan cookies, tokens, tráfico de red ni contraseñas. La URL guardada omite parámetros y fragmentos.

Chrome conserva cookies de sesión dentro de `.perfil_visor`, que debe permanecer local. El puerto de depuración permite controlar ese perfil a programas locales mientras Chrome está abierto: ciérralo al terminar. El visor no usa tu perfil habitual ni tu sesión ya abierta.

### Colaboración desde la carpeta

Una vez conectado, el asistente puede solicitar una captura escribiendo `{"accion":"capturar"}` en `auditoria/solicitud_captura.json`. El visor procesa la petición y guarda evidencia de la pestaña de BusCMMS. Este canal solo permite capturas; no permite navegar, pulsar botones ni modificar registros. El inicio de sesión y la navegación los hace el usuario. Tener archivos locales no conecta automáticamente este chat con el navegador.

### Auditoría de entornos

`auditar_entorno.py --entorno administrador` o `--entorno usuario` genera un inventario de páginas enlazadas y evidencias locales. Ejecutar con el Python de `.venv` y la sesión correspondiente abierta. El nombre del entorno es una etiqueta declarada, no una verificación del rol. No envía formularios ni exporta credenciales. El recorrido guarda los campos sin valores y puede tardar varios minutos. Las cargas secundarias necesitan revisión manual; un título visible no demuestra que toda la página esté lista.

Los resultados y límites de la revisión actual están en `INFORME_AUDITORIA.md`; las prioridades propuestas para el nuevo sistema están en `REQUISITOS_SISTEMA.md`. `revisar_formularios.py` y `revisar_complementos.py` reproducen las aperturas concretas del administrador; no son pruebas de creación ni autorización.

### Interfaz programática local

`cliente_buscmms.py` consulta la sesión de Chrome mediante Playwright y devuelve JSON. No es la API oficial de BusCMMS ni un servidor HTTP. Tras actualizar el visor, cierra el Chrome exclusivo del visor y el panel, reabre el panel y pulsa **Abrir Chrome**. La sesión se conserva en el perfil local. Completa el acceso si se solicita.

```powershell
.\.venv\Scripts\python.exe cliente_buscmms.py estado
.\.venv\Scripts\python.exe cliente_buscmms.py menus
.\.venv\Scripts\python.exe cliente_buscmms.py abrir --ruta /es/dashboard
.\.venv\Scripts\python.exe cliente_buscmms.py captura
```

`abrir` acepta únicamente rutas obtenidas de enlaces de la pantalla actual; excluye acceso, salida y eliminación. No escribe datos ni envía formularios. Los grupos de menú sin enlaces no se expanden automáticamente. Esta conexión permite que el asistente consulte el navegador con comandos locales; requiere Chrome abierto y una sesión válida. Para una API oficial hacen falta documentación, acceso habilitado y credenciales propias de esa API, que deben mantenerse locales.

Este visor facilita una auditoría visual y funcional guiada. No demuestra permisos del servidor, seguridad de autenticación ni la corrección interna de los indicadores. No hay captura automática durante el acceso.
