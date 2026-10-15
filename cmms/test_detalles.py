import io
import csv
import json
import uuid
import tempfile
from decimal import Decimal
from unittest.mock import patch
from django.test import TestCase,Client,override_settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from django.core import signing
from cmms import models as m
from cmms.registry import REGISTRY
from cmms.forms import form_class
from cmms.services import save_record,transition
from cmms.modules.inventario.services import receive,update_demands,demand_to_purchase
from cmms.modules.operacion.services import fuel_efficiency
from cmms.modules.inspecciones.services import notify,send_kpi_alerts

class DetailedWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org=m.Organization.objects.create(name='SETRAM detalle prueba',default_labor_rate=50)
        cls.other=m.Organization.objects.create(name='Otro ámbito detalle')
        cls.admin=m.User.objects.create_user('det_admin',organization=cls.org,role='administrador')
        cls.tech=m.User.objects.create_user('det_tecnico',organization=cls.org,role='tecnico')
        cls.driver=m.User.objects.create_user('det_conductor',organization=cls.org,role='conductor')
        cls.bus=m.Bus.objects.create(organization=cls.org,code='DET-01',plate='DET-01',brand='Prueba',model='Bus',year=2025,driver=cls.driver)
        cls.foreign=m.Bus.objects.create(organization=cls.other,code='AJENO',plate='AJENO',brand='Prueba',model='Bus',year=2025)
        cls.supplier=m.Supplier.objects.create(organization=cls.org,name='Proveedor detalle')
        cls.part=m.Part.objects.create(organization=cls.org,code='DET-FILTRO',name='Filtro de prueba',supplier=cls.supplier,unit_cost=10)

    def setUp(self):self.client.force_login(self.admin)

    def order(self,**extra):return m.WorkOrder.objects.create(organization=self.org,bus=self.bus,title='Trabajo detalle',description='Prueba',assigned_to=self.tech,**extra)

    def test_vin_and_gallery_limit_tenant_download(self):
        self.bus.vin='VIN-INCORRECTO'
        with self.assertRaises(ValidationError):self.bus.full_clean()
        self.bus.vin='1FUJGHDV8NLDZ2345';self.bus.full_clean()
        with tempfile.TemporaryDirectory() as root,override_settings(MEDIA_ROOT=root):
            module=REGISTRY['fotos_bus']
            for i in range(5):
                form=form_class(module)({'bus':self.bus.pk,'caption':f'Foto {i}'},{'image':SimpleUploadedFile('foto.png',b'\x89PNG\r\n\x1a\nPrueba')},user=self.admin,module=module)
                self.assertTrue(form.is_valid(),form.errors);save_record(form,self.admin)
            form=form_class(module)({'bus':self.bus.pk},{'image':SimpleUploadedFile('otra.png',b'\x89PNG\r\n\x1a\nPrueba')},user=self.admin,module=module)
            self.assertFalse(form.is_valid())
            photo=m.BusPhoto.objects.first()
            response=self.client.get(reverse('bus-photo-file',args=[photo.pk]));self.assertEqual(response.status_code,200)
            self.assertTrue(b''.join(response.streaming_content))
            stranger=m.User.objects.create_user('foto_ajeno',organization=self.other,role='administrador')
            self.client.force_login(stranger)
            self.assertEqual(self.client.get(reverse('bus-photo-file',args=[photo.pk])).status_code,404)

    def test_hourly_work_order_and_template_tasks(self):
        template=m.ServiceTask.objects.create(organization=self.org,name='Revisar puertas',instructions='Verificar cierre',estimated_hours=1)
        program=m.ServiceProgram.objects.create(organization=self.org,name='Servicio de prueba',tasks='Revisión')
        program.task_templates.add(template)
        module=REGISTRY['ordenes']
        form=form_class(module)({'bus':self.bus.pk,'title':'Orden con plantilla','description':'Diagnóstico de prueba','kind':'correctivo','priority':'media',
            'assigned_to':self.tech.pk,'program':program.pk,'labor_cost':'0','billing_mode':'por_hora','worked_hours':'2','additional_tasks':'Comprobar luces'},user=self.admin,module=module)
        self.assertTrue(form.is_valid(),form.errors);obj=save_record(form,self.admin)
        self.assertEqual(obj.labor_cost,Decimal('100'))
        self.assertEqual(obj.workordertask_set.count(),2)
        transition(self.tech,obj.pk,'en_progreso');obj.refresh_from_db();self.assertIsNotNone(obj.started_at)

    def test_multi_line_partial_purchase_replay_and_over_receipt(self):
        purchase=m.PurchaseOrder.objects.create(organization=self.org,supplier=self.supplier,part=self.part,quantity=10,unit_cost=12,reference='Detalle compra')
        another=m.Part.objects.create(organization=self.org,code='OTRA-PIEZA',name='Otra pieza')
        line=m.PurchaseLine.objects.create(organization=self.org,purchase=purchase,part=another,quantity=5,unit_cost=20)
        token=uuid.uuid4()
        receive(self.admin,purchase.pk,4,None,token);receive(self.admin,purchase.pk,4,None,token)
        purchase.refresh_from_db();self.part.refresh_from_db()
        self.assertEqual(purchase.status,'parcial');self.assertEqual(self.part.quantity,Decimal('4'))
        with self.assertRaises(ValidationError):receive(self.admin,purchase.pk,7,None,uuid.uuid4())
        receive(self.admin,purchase.pk)
        self.part.refresh_from_db();another.refresh_from_db();purchase.refresh_from_db()
        self.assertEqual(self.part.quantity,Decimal('10'));self.assertEqual(another.quantity,Decimal('5'));self.assertEqual(purchase.status,'recibido')
        self.assertEqual(purchase.total,Decimal('220'))
        self.assertEqual(self.client.get(reverse('detail',args=['compras',purchase.pk])).status_code,200)

    def test_demand_deduplication_and_manual_purchase(self):
        self.part.auto_demand=True;self.part.minimum=5;self.part.save()
        self.assertEqual(update_demands(self.org),1);self.assertEqual(update_demands(self.org),0)
        demand=m.PurchaseDemand.objects.get();purchase=demand_to_purchase(self.admin,demand.pk)
        self.assertEqual(demand_to_purchase(self.admin,demand.pk).pk,purchase.pk)
        self.assertEqual(update_demands(self.org),0)

    def test_fuel_efficiency_accounts_for_partial_tanks(self):
        def entry(km,liters,full):return m.FuelEntry.objects.create(organization=self.org,bus=self.bus,date=timezone.localdate(),odometer=km,liters=liters,cost=10*liters,reference=str(km),driver=self.driver,full_tank=full)
        rows=[entry(100,30,True),entry(200,10,False),entry(300,30,True)]
        result=fuel_efficiency(rows)
        self.assertEqual(len(result),1);self.assertEqual(result[0]['per_100'],Decimal('20'))
        self.assertEqual(fuel_efficiency(rows[:2]),[])
        response=self.client.post(reverse('action',args=['combustible',rows[2].pk]),{'estado':'observado','notes':'Comprobante no coincide'})
        self.assertEqual(response.status_code,302);rows[2].refresh_from_db();self.assertEqual(rows[2].verification,'observado')

    def test_private_driver_document_is_not_general_organization_document(self):
        with tempfile.TemporaryDirectory() as root,override_settings(MEDIA_ROOT=root):
            document=m.Document.objects.create(organization=self.org,title='Licencia privada prueba',kind='otro',user=self.driver,file=SimpleUploadedFile('licencia.pdf',b'%PDF-1.7 Prueba'))
            self.client.force_login(self.tech)
            self.assertEqual(self.client.get(reverse('document-file',args=[document.pk])).status_code,404)
            self.client.force_login(self.driver)
            response=self.client.get(reverse('document-file',args=[document.pk]));self.assertEqual(response.status_code,200)
            self.assertTrue(b''.join(response.streaming_content))

    def test_notifications_preferences_and_kpi_no_data_dedup(self):
        self.org.notification_matrix={'conductor':{'combustible':False}};self.org.save()
        self.driver=m.User.objects.get(pk=self.driver.pk)
        self.assertIsNone(notify(self.driver,'combustible','Prueba','Aviso'))
        self.org.kpi_alerts_enabled=True;self.org.save();self.bus.status='taller';self.bus.save()
        self.assertEqual(send_kpi_alerts(self.org),1);self.assertEqual(send_kpi_alerts(self.org),0)
        self.assertFalse(m.Notification.objects.filter(dedupe_key__contains='approval').exists())

    def test_filtered_table_api_csv_pdf_share_scope(self):
        self.order(priority='alta');self.order(priority='baja')
        args={'priority':'alta','vista':'registros'}
        response=self.client.get(reverse('list',args=['ordenes']),args)
        self.assertEqual(response.context['count'],1)
        self.assertEqual(self.client.get(reverse('api-list',args=['ordenes']),args).json()['total'],1)
        csvdata=self.client.get(reverse('export',args=['ordenes']),args).content.decode('utf-8-sig')
        self.assertEqual(len(list(csv.reader(io.StringIO(csvdata),delimiter=';'))),2)
        pdf=self.client.get(reverse('record-pdf',args=['ordenes']),args)
        from pypdf import PdfReader
        reader=PdfReader(io.BytesIO(pdf.content));self.assertIn('Trabajo detalle',reader.pages[0].extract_text())
        purchase=m.PurchaseOrder.objects.create(organization=self.org,supplier=self.supplier,part=self.part,quantity=2,unit_cost=10)
        other=m.PurchaseOrder.objects.create(organization=self.org,supplier=self.supplier,part=self.part,quantity=2,unit_cost=10)
        for order in (purchase,other):
            m.PurchaseLine.objects.create(organization=self.org,purchase=order,part=self.part,quantity=1,unit_cost=10)
        filtered={'purchase':purchase.pk,'vista':'registros'}
        self.assertEqual(self.client.get(reverse('list',args=['lineas_compra']),filtered).context['count'],1)
        self.assertEqual(self.client.get(reverse('api-list',args=['lineas_compra']),filtered).json()['total'],1)
        from cmms.modules.workspace import apply_filters
        program=m.ServiceProgram.objects.create(organization=self.org,name='Programa de filtro',tasks='Prueba')
        linked=self.order(program=program)
        self.assertEqual(list(apply_filters(m.WorkOrder.objects.filter(organization=self.org),REGISTRY['ordenes'],{'program':program.pk})),[linked])

    def test_module_activity_does_not_include_other_organization(self):
        from cmms.services import audit
        obj=self.order();audit(self.admin,'Prueba visible',obj)
        response=self.client.get(reverse('list',args=['ordenes']),{'vista':'actividad'})
        self.assertContains(response,'Prueba visible')
        self.client.force_login(self.driver)
        self.assertNotContains(self.client.get(reverse('list',args=['ordenes']),{'vista':'actividad'}),'Prueba visible')

    def test_import_catalog_atomic_replay_and_foreign_relationships(self):
        from cmms.modules.importing import import_catalog
        data=json.dumps([{'code':'IMP-01','plate':'IMP-01','brand':'Prueba','model':'Prueba','year':2025,'driver':self.driver.pk}]).encode()
        first,repeated=import_catalog(self.admin,'buses',SimpleUploadedFile('buses.json',data));self.assertFalse(repeated)
        _,repeated=import_catalog(self.admin,'buses',SimpleUploadedFile('buses.json',data));self.assertTrue(repeated)
        foreigndriver=m.User.objects.create_user('ajeno_importacion',organization=self.other,role='conductor')
        bad=json.dumps([{'code':'IMP-02','plate':'IMP-02','brand':'Prueba','model':'Prueba','year':2025},{'code':'IMP-03','plate':'IMP-03','brand':'Prueba','model':'Prueba','year':2025,'driver':foreigndriver.pk}]).encode()
        with self.assertRaises(ValidationError):import_catalog(self.admin,'buses',SimpleUploadedFile('otro.json',bad))
        self.assertFalse(m.Bus.objects.filter(code='IMP-02').exists())

    def test_qr_is_authenticated_and_does_not_authorize_foreign_bus(self):
        response=self.client.get(reverse('bus-qr',args=[self.bus.pk]))
        self.assertEqual(response.status_code,200);self.assertEqual(response['Content-Type'],'image/svg+xml')
        self.assertEqual(self.client.get(reverse('bus-qr',args=[self.foreign.pk])).status_code,404)
        self.assertEqual(Client().get(reverse('bus-qr',args=[self.bus.pk])).status_code,302)

    def test_team_join_requires_approval_without_password_hash_exposure(self):
        from cmms.modules.personal.joining import SALT,decide
        token=signing.dumps({'org':self.org.pk,'issuer':self.admin.pk},salt=SALT)
        response=Client().post(reverse('team-join',args=[token]),{'username':'solicitante_detalle','first_name':'Persona','last_name':'Prueba','email':'solicitud@example.com','requested_role':'conductor','password1':'Clave-registro-prueba-2026','password2':'Clave-registro-prueba-2026'})
        self.assertEqual(response.status_code,200);self.assertFalse(m.User.objects.filter(username='solicitante_detalle').exists())
        pending=m.TeamJoinRequest.objects.get()
        detail=self.client.get(reverse('detail',args=['ingresos_equipo',pending.pk]));self.assertNotContains(detail,pending.password_hash)
        decide(self.admin,'ingresos_equipo',pending.pk,'aprobada','Identidad verificada en prueba')
        account=m.User.objects.get(username='solicitante_detalle');self.assertEqual(account.role,'conductor');self.assertTrue(account.check_password('Clave-registro-prueba-2026'))

    def test_scheduled_report_creates_one_pdf_per_occurrence(self):
        from cmms.modules.administracion.reports import process_schedules
        with tempfile.TemporaryDirectory() as root,override_settings(MEDIA_ROOT=root):
            m.ScheduledReport.objects.create(organization=self.org,name='Flota semanal',kind='fleet',interval_days=7,next_run=timezone.now()-timezone.timedelta(days=1),created_by=self.admin)
            self.assertEqual(process_schedules(self.org),1);self.assertEqual(process_schedules(self.org),0)
            result=m.ReportRun.objects.get();response=self.client.get(reverse('report-run-file',args=[result.pk]));self.assertEqual(response.status_code,200)
            self.assertTrue(b''.join(response.streaming_content))

    def test_all_detailed_screens_and_reports_render(self):
        from cmms.modules.administracion.reports import CATALOG
        for kind in CATALOG:
            self.assertEqual(self.client.get(reverse('report-detail',args=[kind])).status_code,200)
            self.assertEqual(self.client.get(reverse('report-detail',args=[kind]),{'formato':'pdf'}).status_code,200)
        for mode in ('dia','semana','mes','anio','agenda'):
            self.assertEqual(self.client.get(reverse('calendar'),{'vista':mode}).status_code,200)
        for key in ('buses','ordenes','repuestos','personal','inspecciones','proveedores','compras','neumaticos','documentos','programas','cumplimiento'):
            for mode in ('registros','analitica','actividad'):
                self.assertEqual(self.client.get(reverse('list',args=[key]),{'vista':mode}).status_code,200)
        self.assertEqual(self.client.get(reverse('global-search'),{'q':'Prueba'}).status_code,200)
        self.assertEqual(self.client.get(reverse('report-zip')).status_code,200)
        self.assertEqual(self.client.get(reverse('fuel-analytics')).status_code,200)
        self.assertEqual(self.client.get(reverse('reactivation-request')).status_code,200)

    def test_vision_own_api_auth_validation_replay_and_review(self):
        from cmms.modules.telemetria.services import create_key
        camera=m.Camera.objects.create(organization=self.org,name='Cámara prueba',stream_url='http://localhost/video.webm',stream_type='video')
        _,token=create_key(self.admin,'Visión prueba',scopes=['vision'])
        payload={'camera_id':camera.pk,'event_id':'captura-1','model_version':'Fuente de prueba v1','measured_at':timezone.now().isoformat(),
            'objects':[{'object_id':'obj-1','label':'Bus prueba','bus_code':self.bus.code,'bbox':[.1,.2,.3,.4],'confidence':95,'risk':'atencion'}]}
        url=reverse('vision-ingest');header={'HTTP_AUTHORIZATION':'Bearer '+token}
        self.assertEqual(Client().post(url,json.dumps(payload),content_type='application/json').status_code,401)
        response=self.client.post(url,json.dumps(payload),content_type='application/json',**header)
        self.assertEqual(response.status_code,200)
        self.assertTrue(self.client.post(url,json.dumps(payload),content_type='application/json',**header).json()['repetida'])
        bad={**payload,'event_id':'captura-mal','objects':[{**payload['objects'][0],'bbox':[.8,.2,.3,.4]}]}
        self.assertEqual(self.client.post(url,json.dumps(bad),content_type='application/json',**header).status_code,422)
        self.assertEqual(m.VisionFrame.objects.count(),1)
        self.assertEqual(self.client.get(reverse('documents:vision')).status_code,200)
        detection=m.VisionDetection.objects.get();detection.status='confirmada'
        with self.assertRaises(ValidationError):detection.full_clean()
