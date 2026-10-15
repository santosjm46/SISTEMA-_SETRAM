"""Capturas de QA con datos exclusivamente en una base temporal."""
import json
import mimetypes
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlsplit

if os.getenv('SETRAM_QA') != '1' or os.getenv('DB_NAME') != 'setram_qa':
    raise RuntimeError('Este script solo funciona con la base temporal setram_qa del ejecutor de pruebas.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE','setram.settings')
import django
django.setup()

from django.test import Client
from django.utils import timezone
from playwright.sync_api import sync_playwright
from cmms import models as m

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'pruebas_visuales'
OUT.mkdir(exist_ok=True)
org=m.Organization.objects.create(name='SETRAM · Datos de validación')
admin=m.User.objects.create_user('qa_admin',organization=org,role='administrador',first_name='Administrador de prueba')
tech=m.User.objects.create_user('qa_tecnico',organization=org,role='tecnico',first_name='Técnico de prueba')
driver=m.User.objects.create_user('qa_conductor',organization=org,role='conductor',first_name='Conductor de prueba')
template=m.Checklist.objects.create(organization=org,name='Plantilla de validación',items='Frenos\nPuertas\nLuces')
for i in range(1,7):
    bus=m.Bus.objects.create(organization=org,code=f'QA-{i:03}',plate=f'PRUEBA-{i:03}',brand='Bus de prueba',model='Validación',year=2025,capacity=60,odometer=12000*i,status='taller' if i==6 else 'operativo',driver=driver if i==1 else None)
    if i<=3:
        m.WorkOrder.objects.create(organization=org,bus=bus,title=['Revisión del sistema de frenos','Servicio periódico de motor','Inspección de puertas'][i-1],description='Datos creados solo para validar la interfaz',assigned_to=tech,priority='alta' if i==1 else 'media',status='en_progreso' if i==1 else 'abierta')
    if i<=2:
        m.PreventivePlan.objects.create(organization=org,bus=bus,title='Servicio periódico de prueba',tasks='Revisar y registrar',next_date=timezone.localdate(),interval_days=30)
    m.Inspection.objects.create(organization=org,bus=bus,inspector=driver,odometer=bus.odometer,checklist=template,result='aprobado',signature='Inspector de prueba')
m.Part.objects.create(organization=org,code='QA-REP-01',name='Filtro de prueba',minimum=3,quantity=1,unit_cost=45)
bus=m.Bus.objects.get(organization=org,code='QA-001')
device=m.TelemetryDevice.objects.create(organization=org,bus=bus,name='Dispositivo de validación',external_id='QA-GPS-001')
m.TelemetryReading.objects.create(organization=org,bus=bus,device=device,measured_at=timezone.now(),odometer=bus.odometer,engine_hours=500,speed=0,temperature=106,fault_code='P0117',latitude='-16.5000000',longitude='-68.1500000')
from cmms.modules.predictivo.services import assess
for obj in m.Bus.objects.filter(organization=org): assess(obj,admin)
m.ComplianceRequirement.objects.create(organization=org,bus=bus,title='Verificación técnica de prueba',responsible=admin,due_date=timezone.localdate())
m.ShiftLog.objects.create(organization=org,bus=bus,driver=driver,started_at=timezone.now()-timezone.timedelta(hours=10),ended_at=timezone.now()-timezone.timedelta(hours=2),break_minutes=60)
m.OperatingPolicy.objects.create(organization=org,name='Política de prueba',daily_driving_hours=6,notes='Umbral exclusivo de QA visual, no configuración operativa de SETRAM.')
m.Camera.objects.create(organization=org,name='Cámara de prueba',bus=bus,stream_url='http://localhost/qa-video-no-disponible.webm',stream_type='video',notes='Fuente de prueba; no se transmite video real.')
m.ServiceTask.objects.create(organization=org,name='Verificación de puertas',instructions='Comprobar el cierre y registrar la evidencia',estimated_hours=1)
supplier=m.Supplier.objects.create(organization=org,name='Proveedor de validación',lead_time_days=3)
part=m.Part.objects.get(organization=org,code='QA-REP-01')
purchase=m.PurchaseOrder.objects.create(organization=org,supplier=supplier,part=part,quantity=5,unit_cost=45,reference='Orden exclusiva de validación')
bus.vin='1FUJGHDV8NLDZ2345';bus.design_life_years=12;bus.insurance_expiry=timezone.localdate()+timezone.timedelta(days=15);bus.save()
from cmms.modules.catalog_seeds import apply as apply_catalogs,SPECS
apply_catalogs(admin,list(SPECS))
catalog_fault=m.FailureType.objects.get(organization=org,code='F-FRE-01')
client=Client(HTTP_HOST='localhost')
client.force_login(admin)
errors=[]
executor=ThreadPoolExecutor(max_workers=1)


def handler(route):
    url=urlsplit(route.request.url)
    if url.path.startswith('/static/'):
        target=(ROOT/'static'/url.path.removeprefix('/static/')).resolve()
        if not target.is_relative_to((ROOT/'static').resolve()) or not target.is_file():
            route.fulfill(status=404,body='No encontrado'); return
        route.fulfill(status=200,content_type=mimetypes.guess_type(str(target))[0] or 'application/octet-stream',body=target.read_bytes())
    else:
        response=executor.submit(client.get,url.path+('?' + url.query if url.query else '')).result()
        route.fulfill(status=response.status_code,headers={k:v for k,v in response.items() if k.lower() != 'content-length'},body=response.content)


with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(viewport={'width':1440,'height':1050},device_scale_factor=1)
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.route('http://localhost/**',handler)
    screens=[('/','administrador'),('/modulos/buses/','flota'),('/modulos/inspecciones/nuevo/','inspeccion'),('/login/','acceso'),
             ('/telemetria/','telemetria'),('/telemetria/importar/','importacion_telemetria'),('/predictivo/','predictivo'),('/cumplimiento/','cumplimiento'),
             ('/operacion/jornadas/','jornadas'),('/documentos/auditor/','auditor_documental'),
             ('/documentos/vision/','vision'),('/organizacion/modulos/','visibilidad'),('/organizacion/facturacion/','finanzas')]
    screens.extend([('/modulos/buses/nuevo/','alta_bus'),('/modulos/ordenes/nuevo/','asistente_ot'),
                    (f'/modulos/buses/{bus.pk}/','ficha_bus'),(f'/modulos/compras/{purchase.pk}/','compra_detalle'),
                    ('/modulos/repuestos/?vista=analitica','inventario_analitica'),('/modulos/personal/','equipo'),
                    ('/calendario/?vista=anio','calendario_anual'),('/informes/','catalogo_informes'),('/configuracion/','configuracion'),
                    ('/catalogos/iniciales/','catalogos_iniciales'),('/modulos/tipos_falla/','tipos_falla'),('/modulos/repuestos/nuevo/','alta_repuesto')])
    for path,name in screens:
        response=page.goto('http://localhost'+path,wait_until='networkidle')
        if not response or response.status != 200: raise RuntimeError(f'Pantalla no disponible: {path}')
        page.screenshot(path=str(OUT/(name+'.png')),full_page=True)
    page.set_viewport_size({'width':390,'height':844})
    mobile_paths=('/telemetria/','/predictivo/','/documentos/auditor/','/organizacion/modulos/','/modulos/ordenes/nuevo/','/modulos/buses/nuevo/','/configuracion/','/informes/','/catalogos/iniciales/','/modulos/repuestos/nuevo/')
    for path in mobile_paths:
        response=page.goto('http://localhost'+path,wait_until='networkidle')
        if response.status!=200: raise RuntimeError('Módulo no disponible en móvil: '+path)
        if page.evaluate('document.documentElement.scrollWidth > innerWidth + 1'):
            raise RuntimeError('Desbordamiento horizontal en móvil: '+path)
    page.goto('http://localhost/',wait_until='networkidle')
    if page.evaluate('document.documentElement.scrollWidth > innerWidth + 1'):
        raise RuntimeError('Desbordamiento horizontal en móvil.')
    page.get_by_role('button',name='Abrir menú').click()
    if not page.locator('#sidebar').evaluate("e=>e.classList.contains('open')"):
        raise RuntimeError('El menú móvil no se abrió.')
    page.locator('#sidebarShade').click(position={'x':350,'y':200})
    page.wait_for_function("document.getElementById('sidebar').getBoundingClientRect().right <= 0.5")
    page.screenshot(path=str(OUT/'movil.png'),full_page=True)
    page.set_viewport_size({'width':1440,'height':1050})
    page.goto('http://localhost/modulos/ordenes/nuevo/',wait_until='networkidle')
    page.locator('#id_bus').select_option(str(bus.pk))
    fault=catalog_fault
    page.locator('#id_failure_type').select_option(str(fault.pk))
    if page.locator('#id_title').input_value()!=fault.name:raise RuntimeError('El catálogo no prellenó el título de la OT.')
    if page.locator('#id_failure_category').input_value()!='frenos':raise RuntimeError('El catálogo no prellenó el sistema de la OT.')
    if not page.locator('#id_description').input_value():raise RuntimeError('El catálogo no prellenó la descripción.')
    page.screenshot(path=str(OUT/'asistente_ot_falla.png'),full_page=True)
    page.locator('#wizardNext').click()
    if not page.locator('.wizard-section[data-step="1"]').is_visible():raise RuntimeError('El asistente de OT no avanzó a las tareas.')
    page.screenshot(path=str(OUT/'asistente_ot_tareas.png'),full_page=True)
    executor.submit(client.force_login,driver).result()
    page.goto('http://localhost/',wait_until='networkidle')
    if page.get_by_role('link',name='Personal y roles',exact=True).count():
        raise RuntimeError('El conductor ve el menú de personal.')
    page.screenshot(path=str(OUT/'conductor.png'),full_page=True)
    executor.submit(client.force_login,tech).result()
    page.goto('http://localhost/',wait_until='networkidle')
    page.screenshot(path=str(OUT/'tecnico.png'),full_page=True)
    browser.close()
if errors: raise RuntimeError('Errores JavaScript: '+json.dumps(errors))
executor.shutdown()
(OUT/'resultado.json').write_text(json.dumps({'estado':'correcto','datos':'Solo pruebas, no CMMS','pantallas':len(screens)+5,'movil':f'390 px sin desbordamiento en panel y {len(mobile_paths)} módulos','asistente':'Tipo de falla prellena título, descripción y sistema; navegación a tareas sin guardar OT','roles':['administrador','conductor','tecnico']},ensure_ascii=False,indent=2),encoding='utf-8')
print('Verificación visual completada. Evidencias en pruebas_visuales; datos exclusivamente temporales.')
