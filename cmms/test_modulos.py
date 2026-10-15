import hashlib
import json
import tempfile
from decimal import Decimal
from unittest.mock import patch
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase,Client,override_settings
from django.urls import reverse
from django.utils import timezone
from . import models as m
from .registry import REGISTRY,MODULES,scoped
from .forms import form_class
from .services import save_record,transition,generate_preventive
from .modules.telemetria.services import create_key,authenticate_key,ingest
from .modules.predictivo.services import assess
from .modules.actions import create_order
from .modules.inspecciones.services import dispatch_reminders


class DomainTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org=m.Organization.objects.create(name='SETRAM módulos prueba')
        cls.other=m.Organization.objects.create(name='Otra organización prueba')
        cls.admin=m.User.objects.create_user('mod_admin',organization=cls.org,role='administrador')
        cls.tech=m.User.objects.create_user('mod_tech',organization=cls.org,role='tecnico')
        cls.driver=m.User.objects.create_user('mod_driver',organization=cls.org,role='conductor')
        cls.driver2=m.User.objects.create_user('mod_driver2',organization=cls.org,role='conductor')
        cls.bus=m.Bus.objects.create(organization=cls.org,code='MOD-01',plate='MOD-01',brand='Prueba',model='Bus',year=2025,driver=cls.driver)
        cls.foreign=m.Bus.objects.create(organization=cls.other,code='EXT-01',plate='EXT-01',brand='Prueba',model='Bus',year=2025)
        cls.device=m.TelemetryDevice.objects.create(organization=cls.org,bus=cls.bus,name='Dispositivo prueba',external_id='GPS-01')

    def setUp(self):
        self.client.force_login(self.admin)

    def reading(self,**changes):
        return {'device_id':'GPS-01','event_id':'evento-prueba-1','measured_at':timezone.now().isoformat(),
                'odometer':'100.0','engine_hours':'12.0','latitude':'-16.5000000','longitude':'-68.1500000',**changes}

    def order(self,**changes):
        return m.WorkOrder.objects.create(organization=self.org,bus=self.bus,title='Orden prueba',description='Trabajo de prueba',assigned_to=self.tech,**changes)

    def test_domain_manifest_and_menu_coverage(self):
        self.assertGreaterEqual(len(MODULES),40)
        self.assertEqual(len(MODULES),len(REGISTRY))
        expected={'telemetria','predictivo','cumplimiento','retiros','jornadas','recorridos','auditor_documental','vision','recordatorios','visibilidad','ejecutivo','pulso_flota','facturacion'}
        self.assertTrue(expected<=set(REGISTRY))
        response=self.client.get('/')
        keys={item['key'] for group in response.context['navigation'].values() for item in group}
        self.assertEqual(keys,set(REGISTRY))

    def test_all_roles_only_see_authorized_enabled_menus(self):
        for user in (self.driver,self.tech):
            self.client.force_login(user)
            response=self.client.get('/')
            keys={item['key'] for group in response.context['navigation'].values() for item in group}
            self.assertEqual(keys,{item.key for item in MODULES if user.role in item.read})
            self.assertNotIn('integraciones',keys)
            self.assertNotIn('invitaciones',keys)

    def test_telemetry_key_digest_and_revocation(self):
        key,token=create_key(self.admin,'Proveedor prueba')
        self.assertNotIn(token,key.digest)
        self.assertEqual(authenticate_key(token).pk,key.pk)
        self.assertIsNone(authenticate_key(token+'alterado'))
        key.active=False; key.save()
        self.assertIsNone(authenticate_key(token))

    def test_telemetry_retries_and_historical_readings_preserve_odometer(self):
        key,_=create_key(self.admin,'Proveedor prueba')
        data=self.reading()
        first=ingest(key,[data])
        repeated=ingest(key,[data])
        self.assertEqual(first[0]['id'],repeated[0]['id'])
        self.assertTrue(repeated[0]['repetida'])
        ingest(key,[self.reading(event_id='historico',odometer='80.0',engine_hours='10.0',measured_at=(timezone.now()-timezone.timedelta(days=2)).isoformat())])
        self.bus.refresh_from_db()
        self.assertEqual(self.bus.odometer,Decimal('100'))
        self.assertEqual(self.bus.engine_hours,Decimal('12'))

    def test_conflicting_event_id_and_invalid_batch_roll_back(self):
        key,_=create_key(self.admin,'Proveedor prueba')
        data=self.reading()
        ingest(key,[data])
        with self.assertRaises(ValidationError): ingest(key,[{**data,'odometer':'101.0'}])
        with self.assertRaises(ValidationError): ingest(key,[self.reading(event_id='nuevo',odometer='200.0'),self.reading(event_id='invalido',latitude='150')])
        self.assertEqual(m.TelemetryReading.objects.count(),1)
        self.bus.refresh_from_db(); self.assertEqual(self.bus.odometer,Decimal('100'))

    def test_telemetry_numeric_future_and_tenant_validation(self):
        key,_=create_key(self.admin,'Proveedor prueba')
        m.TelemetryDevice.objects.create(organization=self.other,bus=self.foreign,name='Ajeno',external_id='GPS-AJENO')
        for changes in ({'odometer':'NaN'},{'odometer':'-1'},{'device_id':'GPS-AJENO'},{'measured_at':(timezone.now()+timezone.timedelta(days=1)).isoformat()}, {'measured_at':'2026-01-01T12:00:00'}):
            with self.subTest(changes=changes),self.assertRaises(ValidationError): ingest(key,[self.reading(**changes)])

    def test_ingest_bearer_api_and_visibility_block(self):
        key,token=create_key(self.admin,'Proveedor prueba')
        client=Client(enforce_csrf_checks=True)
        url=reverse('telemetry-ingest')
        body=json.dumps({'readings':[self.reading()]})
        self.assertEqual(client.post(url,body,content_type='application/json').status_code,401)
        self.assertEqual(client.post(url,body,content_type='application/json',HTTP_AUTHORIZATION='Bearer '+token).status_code,200)
        self.org.enabled_modules={'telemetria':False}; self.org.save()
        self.assertEqual(client.post(url,body,content_type='application/json',HTTP_AUTHORIZATION='Bearer '+token).status_code,403)
        self.assertEqual(self.client.get(reverse('telemetry:index')).status_code,403)
        self.assertEqual(self.client.get(reverse('api-list',args=['telemetria'])).status_code,403)

    def test_key_loses_access_if_creator_is_demoted(self):
        _,token=create_key(self.admin,'Proveedor prueba')
        m.User.objects.filter(pk=self.admin.pk).update(role='conductor')
        self.assertIsNone(authenticate_key(token))

    def test_predictive_missing_data_does_not_fabricate_score(self):
        result=assess(self.bus,self.admin)
        self.assertIsNone(result.score)
        self.assertEqual(result.level,'sin_datos')
        self.assertFalse(m.PredictionRecommendation.objects.exists())

    def test_predictive_ignores_stale_telemetry(self):
        key,_=create_key(self.admin,'Proveedor prueba')
        ingest(key,[self.reading(measured_at=(timezone.now()-timezone.timedelta(days=3)).isoformat(),temperature='120',fault_code='P0117')])
        result=assess(self.bus,self.admin)
        self.assertIsNone(result.score)
        self.assertFalse(result.coverage['telemetria_reciente'])

    def test_predictive_recommendation_generates_one_order_with_sources(self):
        self.bus.status='inmovilizado'; self.bus.save()
        result=assess(self.bus,self.admin)
        self.assertEqual(result.level,'critico')
        self.assertTrue(result.signals[0]['fuente'])
        rec=m.PredictionRecommendation.objects.get()
        order=create_order(self.admin,'recomendaciones',rec.pk)
        self.assertEqual(create_order(self.admin,'recomendaciones',rec.pk).pk,order.pk)
        assess(self.bus,self.admin)
        self.assertEqual(m.PredictionRecommendation.objects.count(),1)
        self.assertEqual(m.WorkOrder.objects.count(),1)

    def test_reminders_send_once_and_inbox_is_private(self):
        reminder=m.InspectionReminder.objects.create(organization=self.org,bus=self.bus,title='Inspección prueba',assigned_to=self.driver,next_due=timezone.now()-timezone.timedelta(days=10),interval_days=2)
        self.assertEqual(dispatch_reminders(self.org),1)
        self.assertEqual(dispatch_reminders(self.org),0)
        reminder.refresh_from_db(); self.assertGreater(reminder.next_due,timezone.now())
        notice=m.Notification.objects.get()
        self.assertFalse(scoped(REGISTRY['notificaciones'],self.admin).exists())
        self.client.force_login(self.tech)
        self.assertEqual(self.client.get(reverse('detail',args=['notificaciones',notice.pk])).status_code,404)
        self.client.force_login(self.driver)
        response=self.client.get(reverse('inspections:notifications'))
        self.assertContains(response,'Inspección prueba')
        self.assertEqual(self.client.post(reverse('inspections:notifications'),{'leida':notice.pk}).status_code,302)
        notice.refresh_from_db(); self.assertIsNotNone(notice.read_at)

    def test_shift_breaks_overlap_and_driver_identity(self):
        start=timezone.now()-timezone.timedelta(hours=10)
        shift=m.ShiftLog(organization=self.org,bus=self.bus,driver=self.driver,started_at=start,ended_at=start+timezone.timedelta(hours=8),break_minutes=60)
        shift.full_clean(); shift.save()
        self.assertEqual(shift.driving_hours,7)
        overlap=m.ShiftLog(organization=self.org,bus=self.bus,driver=self.driver,started_at=start+timezone.timedelta(hours=1),ended_at=start+timezone.timedelta(hours=2),break_minutes=0)
        with self.assertRaises(ValidationError): overlap.full_clean()
        form=form_class(REGISTRY['jornadas'])({'bus':self.bus.pk,'driver':self.driver2.pk,'started_at':'2026-01-01T10:00','ended_at':'2026-01-01T11:00','break_minutes':'0'},user=self.driver,module=REGISTRY['jornadas'])
        self.assertFalse(form.is_valid())
        shift.pk=None; shift.driver=self.driver2; shift.break_minutes=481
        with self.assertRaises(ValidationError): shift.full_clean()

    def test_hos_without_policy_does_not_claim_compliance(self):
        response=self.client.get(reverse('operation:hos'))
        self.assertIsNone(response.context['policy'])
        self.assertContains(response,'Umbral pendiente de configuración')

    def test_preventive_hours_and_task_gate_on_approved_close(self):
        self.bus.engine_hours=Decimal('100'); self.bus.save()
        plan=m.PreventivePlan.objects.create(organization=self.org,bus=self.bus,title='Servicio por horas',tasks='Revisar',next_hours=90,interval_hours=50)
        self.assertTrue(plan.overdue)
        order=generate_preventive(self.admin,plan.pk)
        order.assigned_to=self.tech; order.resolution='Servicio verificado'; order.save()
        task=m.WorkOrderTask.objects.create(organization=self.org,work_order=order,title='Revisión de prueba')
        transition(self.tech,order.pk,'en_progreso')
        with self.assertRaises(ValidationError): transition(self.tech,order.pk,'revision')
        module=REGISTRY['tareas_ot']
        form=form_class(module)({'work_order':order.pk,'title':task.title,'status':'hecha','spent_hours':'1','completion_notes':'Verificado'},instance=task,user=self.tech,module=module)
        self.assertTrue(form.is_valid(),form.errors); saved=save_record(form,self.tech)
        self.assertEqual(saved.completed_by_id,self.tech.pk)
        transition(self.tech,order.pk,'revision'); transition(self.admin,order.pk,'cerrada')
        plan.refresh_from_db(); self.assertEqual(plan.next_hours,Decimal('150'))
        self.assertEqual(self.client.get(reverse('detail',args=['ordenes',order.pk])).status_code,200)

    def test_trip_completed_updates_odometer_and_immobilized_bus_cannot_depart(self):
        route=m.ServiceRoute.objects.create(organization=self.org,code='R1',name='Prueba',origin='A',destination='B')
        start=timezone.localtime()-timezone.timedelta(hours=2)
        module=REGISTRY['recorridos']
        payload={'bus':self.bus.pk,'driver':self.driver.pk,'route':route.pk,'started_at':start.strftime('%Y-%m-%dT%H:%M'),
                 'ended_at':(start+timezone.timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M'),'start_km':'10','end_km':'50','passengers':'15','status':'completado'}
        form=form_class(module)(payload,user=self.driver,module=module)
        self.assertTrue(form.is_valid(),form.errors); save_record(form,self.driver)
        self.bus.refresh_from_db(); self.assertEqual(self.bus.odometer,Decimal('50'))
        self.bus.status='inmovilizado'; self.bus.save()
        form=form_class(module)({**payload,'status':'en_ruta'},user=self.driver,module=module)
        self.assertFalse(form.is_valid())

    def test_critical_incident_blocks_bus_until_approved_resolution(self):
        module=REGISTRY['incidentes']
        form=form_class(module)({'bus':self.bus.pk,'title':'Falla crítica prueba','description':'Puerta sin cierre','severity':'critica','occurred_at':timezone.localtime().strftime('%Y-%m-%dT%H:%M')},user=self.driver,module=module)
        self.assertTrue(form.is_valid(),form.errors); incident=save_record(form,self.driver)
        self.bus.refresh_from_db(); self.assertEqual(self.bus.status,'inmovilizado')
        self.bus.status='operativo'
        with self.assertRaises(ValidationError): self.bus.full_clean()
        order=incident.work_order; order.assigned_to=self.tech; order.resolution='Puerta reparada y probada'; order.save()
        transition(self.tech,order.pk,'en_progreso'); transition(self.tech,order.pk,'revision'); transition(self.admin,order.pk,'cerrada')
        incident.refresh_from_db(); self.bus.refresh_from_db()
        self.assertEqual(incident.status,'resuelto'); self.assertEqual(self.bus.status,'operativo')

    def test_compliance_and_paid_invoices_require_evidence(self):
        req=m.ComplianceRequirement(organization=self.org,title='Prueba',responsible=self.admin,due_date=timezone.localdate(),status='completado')
        with self.assertRaises(ValidationError): req.full_clean()
        supplier=m.Supplier.objects.create(organization=self.org,name='Proveedor prueba')
        invoice=m.Invoice(organization=self.org,supplier=supplier,reference='F-01',date=timezone.localdate(),amount=100,status='pagada')
        with self.assertRaises(ValidationError): invoice.full_clean()

    def test_foreign_relations_rejected_across_domains(self):
        reminder=m.InspectionReminder(organization=self.org,bus=self.foreign,assigned_to=self.driver,title='Ajeno',next_due=timezone.now())
        with self.assertRaises(ValidationError): reminder.full_clean()

    def test_invitation_role_is_server_assigned_and_link_consumed_once(self):
        secret='secreto-exclusivo-de-prueba'
        invitation=m.TeamInvitation.objects.create(organization=self.org,email='persona@example.com',role='conductor',created_by=self.admin,
            digest=hashlib.sha256(secret.encode()).hexdigest(),expires_at=timezone.now()+timezone.timedelta(days=1))
        url=reverse('team:accept',args=[invitation.public_id])
        client=Client()
        self.assertEqual(client.post(url,{'invite_secret':'incorrecto'}).status_code,410)
        result=client.post(url,{'invite_secret':secret,'username':'invitado_prueba','first_name':'Persona','last_name':'Prueba','password1':'Clave-de-prueba-efectiva-2026','password2':'Clave-de-prueba-efectiva-2026','role':'administrador'})
        self.assertEqual(result.status_code,302)
        user=m.User.objects.get(username='invitado_prueba')
        self.assertEqual(user.role,'conductor'); self.assertEqual(user.organization_id,self.org.pk)
        self.assertTrue(user.check_password('Clave-de-prueba-efectiva-2026'))
        self.assertEqual(client.get(url).status_code,410)

    def test_invitation_expires_without_disclosing_email(self):
        obj=m.TeamInvitation.objects.create(organization=self.org,email='privado@example.com',role='tecnico',created_by=self.admin,digest='a'*64,expires_at=timezone.now()+timezone.timedelta(days=1))
        client=Client(); url=reverse('team:accept',args=[obj.public_id])
        response=client.get(url); self.assertNotContains(response,obj.email)
        obj.expires_at=timezone.now()-timezone.timedelta(seconds=1); obj.save()
        self.assertEqual(client.get(url).status_code,410)

    def test_visibility_also_blocks_direct_urls_and_exports(self):
        self.org.enabled_modules={'predictivo':False,'cumplimiento':False}; self.org.save()
        for url in (reverse('predictive:index'),reverse('list',args=['cumplimiento']),reverse('export',args=['cumplimiento'])):
            self.assertEqual(self.client.get(url).status_code,403)
        self.assertEqual(self.client.get(reverse('administration:visibility')).status_code,200)
        keys={item['key'] for group in self.client.get('/').context['navigation'].values() for item in group}
        self.assertNotIn('predictivo',keys)

    def test_document_local_analysis_duplicate_and_expiry(self):
        from .modules.documentos.services import analyze_document
        with tempfile.TemporaryDirectory(dir=str(__import__('pathlib').Path(__file__).resolve().parent.parent)) as root,override_settings(MEDIA_ROOT=root):
            data=b'\xff\xd8\xff\xe0Imagen de prueba para cabecera'
            first=m.Document.objects.create(organization=self.org,title='Vencido',kind='seguro',expiry=timezone.localdate()-timezone.timedelta(days=1),file=SimpleUploadedFile('foto.jpg',data))
            result=analyze_document(first,self.admin)
            self.assertEqual(result.state,'revisar'); self.assertTrue(any('vencido' in f for f in result.findings))
            second=m.Document.objects.create(organization=self.org,title='Duplicado',kind='manual',file=SimpleUploadedFile('otra.jpg',data))
            duplicate=analyze_document(second,self.admin)
            self.assertTrue(any('mismo contenido' in f for f in duplicate.findings))
            self.assertEqual(self.client.get(reverse('detail',args=['auditor_documental',result.pk])).status_code,200)

    def test_document_ai_only_runs_with_explicit_checkbox(self):
        with tempfile.TemporaryDirectory() as root,override_settings(MEDIA_ROOT=root):
            doc=m.Document.objects.create(organization=self.org,title='Revisión prueba',kind='manual',file=SimpleUploadedFile('foto.jpg',b'\xff\xd8\xff\xe0Prueba'))
            with patch('cmms.modules.documentos.views.analyze_text',return_value={'resumen':'Prueba','observaciones':['Verificar'], 'requiere_revision':True}) as provider:
                url=reverse('documents:auditor')
                self.assertEqual(self.client.post(url,{'document':doc.pk}).status_code,302); provider.assert_not_called()
                self.assertEqual(self.client.post(url,{'document':doc.pk,'authorize_ai':'on'}).status_code,302); provider.assert_called_once()

    def test_vision_does_not_fabricate_detections(self):
        response=self.client.get(reverse('documents:vision'))
        self.assertIsNone(response.context['selected'])
        self.assertContains(response,'Sin cámaras configuradas')
        self.assertContains(response,'Las observaciones son manuales')

    def test_pdf_worker_extracts_actual_text(self):
        import io
        from pypdf import PdfWriter
        from pypdf.generic import DictionaryObject,NameObject,DecodedStreamObject
        from .modules.documentos.services import analyze_document
        writer=PdfWriter(); pdfpage=writer.add_blank_page(width=300,height=200)
        font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
        pdfpage[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
        stream=DecodedStreamObject(); stream.set_data(b'BT /F1 12 Tf 20 150 Td (Manual de prueba SETRAM) Tj ET')
        pdfpage[NameObject('/Contents')]=writer._add_object(stream)
        output=io.BytesIO(); writer.write(output)
        with tempfile.TemporaryDirectory() as root,override_settings(MEDIA_ROOT=root):
            doc=m.Document.objects.create(organization=self.org,title='PDF prueba',kind='manual',file=SimpleUploadedFile('manual.pdf',output.getvalue()))
            result=analyze_document(doc,self.admin)
            self.assertIn('Manual de prueba SETRAM',result.extracted_text)
            self.assertEqual(result.metadata['pages'],1)

    def test_closed_work_order_task_cannot_be_moved_to_another_order(self):
        closed=self.order(status='cerrada',resolution='Trabajo cerrado')
        open_order=self.order()
        task=m.WorkOrderTask.objects.create(organization=self.org,work_order=closed,title='Histórica',status='hecha',completion_notes='Terminada')
        module=REGISTRY['tareas_ot']
        form=form_class(module)({'work_order':open_order.pk,'title':'Histórica','status':'hecha','spent_hours':'1','completion_notes':'Terminada'},instance=task,user=self.admin,module=module)
        self.assertTrue(form.is_valid(),form.errors)
        with self.assertRaises(ValidationError): save_record(form,self.admin)
        task.refresh_from_db(); self.assertEqual(task.work_order_id,closed.pk)

    def test_csv_import_works_without_integration_key_and_retries_are_safe(self):
        from .modules.telemetria.files import FIELDS
        from io import StringIO
        import csv
        stream=StringIO(); writer=csv.DictWriter(stream,fieldnames=FIELDS,delimiter=';')
        writer.writeheader(); writer.writerow(self.reading())
        data=stream.getvalue().encode('utf-8-sig')
        url=reverse('telemetry:import')
        for _ in range(2):
            response=self.client.post(url,{'archivo':SimpleUploadedFile('lecturas.csv',data,content_type='text/csv')})
            self.assertEqual(response.status_code,302)
        self.assertEqual(m.TelemetryReading.objects.count(),1)
        self.assertEqual(m.IntegrationKey.objects.count(),0)
        self.assertEqual(self.client.get(reverse('telemetry:template')).status_code,200)

    def test_json_import_bad_row_rolls_back_and_reports_error(self):
        data=json.dumps({'readings':[self.reading(),self.reading(event_id='mal',device_id='NO-EXISTE')]}).encode()
        response=self.client.post(reverse('telemetry:import'),{'archivo':SimpleUploadedFile('lecturas.json',data)})
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'Dispositivo no registrado')
        self.assertFalse(m.TelemetryReading.objects.exists())
        self.bus.refresh_from_db(); self.assertEqual(self.bus.odometer,0)

    def test_import_role_csrf_and_size_limits(self):
        from .modules.telemetria.files import parse_file
        self.client.force_login(self.driver)
        self.assertEqual(self.client.get(reverse('telemetry:import')).status_code,403)
        self.assertEqual(self.client.get(reverse('telemetry:template')).status_code,403)
        client=Client(enforce_csrf_checks=True); client.force_login(self.admin)
        self.assertEqual(client.post(reverse('telemetry:import'),{'archivo':SimpleUploadedFile('a.json',b'[]')}).status_code,403)
        with self.assertRaises(ValidationError): parse_file(SimpleUploadedFile('grande.csv',b'a'*(1024*1024+1)))

    def test_telemetry_read_api_includes_position_and_only_assigned_buses(self):
        key,_=create_key(self.admin,'Prueba de lectura')
        ingest(key,[self.reading()])
        m.TelemetryReading.objects.create(organization=self.other,bus=self.foreign,measured_at=timezone.now(),odometer=50)
        self.client.force_login(self.driver)
        response=self.client.get(reverse('api-list',args=['telemetria']))
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['total'],1)
        row=response.json()['resultados'][0]
        self.assertEqual(row['latitude'],'-16.5000000')
        self.assertEqual(row['engine_hours'],'12.0')
        self.assertEqual(row['external_event'],'evento-prueba-1')
