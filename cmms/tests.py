import uuid
from decimal import Decimal
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase, TransactionTestCase, Client
from django.urls import reverse
from . import models as m
from .registry import REGISTRY
from .forms import form_class
from .services import save_record, transition, convert_request, generate_preventive


class OperationalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org=m.Organization.objects.create(name='SETRAM prueba')
        cls.other=m.Organization.objects.create(name='Organización distinta')
        cls.admin=m.User.objects.create_user('admin_prueba',organization=cls.org,role='administrador',password='Clave-Pruebas-2026')
        cls.tech=m.User.objects.create_user('tecnico_prueba',organization=cls.org,role='tecnico',password='Clave-Pruebas-2026')
        cls.driver=m.User.objects.create_user('conductor_prueba',organization=cls.org,role='conductor',password='Clave-Pruebas-2026')
        cls.bus=m.Bus.objects.create(organization=cls.org,code='TEST-001',plate='TEST-001',brand='Prueba',model='Bus',year=2025,driver=cls.driver)
        cls.foreign=m.Bus.objects.create(organization=cls.other,code='TEST-002',plate='TEST-002',brand='Prueba',model='Bus',year=2025)
        cls.checklist=m.Checklist.objects.create(organization=cls.org,name='Prueba',items='Frenos\nLuces')

    def order(self,**kwargs):
        return m.WorkOrder.objects.create(organization=self.org,bus=self.bus,title='Prueba',description='Trabajo',**kwargs)

    def test_tenant_and_role_restrictions(self):
        self.client.force_login(self.driver)
        self.assertEqual(self.client.get(reverse('detail',args=['buses',self.foreign.pk])).status_code,404)
        self.assertEqual(self.client.get(reverse('list',args=['personal'])).status_code,403)
        self.assertEqual(self.client.get(reverse('create',args=['ordenes'])).status_code,403)
        self.assertEqual(self.client.get(reverse('reports')).status_code,403)

    def test_technician_only_assigned_order_and_cannot_close(self):
        mine=self.order(assigned_to=self.tech,status='revision',resolution='Reparado')
        other=self.order()
        self.client.force_login(self.tech)
        self.assertEqual(self.client.get(reverse('detail',args=['ordenes',other.pk])).status_code,404)
        with self.assertRaises(PermissionDenied): transition(self.tech,mine.pk,'cerrada')

    def test_stock_insufficient_rolls_back(self):
        part=m.Part.objects.create(organization=self.org,code='REP-1',name='Filtro',quantity=1)
        order=self.order()
        module=REGISTRY['movimientos']
        form=form_class(module)({'part':part.pk,'kind':'salida','quantity':'2','unit_cost':'12','work_order':order.pk,'reference':'Prueba'},user=self.admin,module=module)
        self.assertTrue(form.is_valid(),form.errors)
        with self.assertRaises(ValidationError): save_record(form,self.admin)
        part.refresh_from_db()
        self.assertEqual(part.quantity,Decimal('1'))
        self.assertEqual(m.StockMovement.objects.count(),0)

    def test_critical_inspection_blocks_and_closing_resolves(self):
        module=REGISTRY['inspecciones']
        from django.utils import timezone
        form=form_class(module)({'bus':self.bus.pk,'kind':'preoperacional','date':timezone.localtime().strftime('%Y-%m-%dT%H:%M'),
            'odometer':'10','checklist':self.checklist.pk,'findings':'Falla de frenos','signature':'Inspector prueba',
            'item_0':'critico','item_1':'aprobado','confirm':'on'},user=self.driver,module=module)
        self.assertTrue(form.is_valid(),form.errors)
        inspection=save_record(form,self.driver)
        self.bus.refresh_from_db()
        self.assertEqual(self.bus.status,'inmovilizado')
        self.assertEqual(inspection.snapshot['version'],1)
        order=inspection.work_order
        order.assigned_to=self.tech
        order.resolution='Frenos reparados y verificados'
        order.save()
        transition(self.tech,order.pk,'en_progreso')
        transition(self.tech,order.pk,'revision')
        transition(self.admin,order.pk,'cerrada')
        inspection.refresh_from_db(); self.bus.refresh_from_db()
        self.assertTrue(inspection.resolved)
        self.assertEqual(self.bus.status,'operativo')

    def test_request_conversion_is_idempotent(self):
        req=m.MaintenanceRequest.objects.create(organization=self.org,bus=self.bus,title='Luz',description='Prueba',reported_by=self.driver)
        first=convert_request(self.admin,req.pk)
        second=convert_request(self.admin,req.pk)
        self.assertEqual(first.pk,second.pk)

    def test_preventive_advances_only_on_approved_close(self):
        from django.utils import timezone
        plan=m.PreventivePlan.objects.create(organization=self.org,bus=self.bus,title='Servicio',tasks='Revisar',next_date=timezone.localdate(),interval_days=30,next_km=100,interval_km=100)
        order=generate_preventive(self.admin,plan.pk)
        self.assertEqual(generate_preventive(self.admin,plan.pk).pk,order.pk)
        order.assigned_to=self.tech; order.resolution='Servicio efectuado'; order.save()
        transition(self.tech,order.pk,'en_progreso'); transition(self.tech,order.pk,'revision')
        plan.refresh_from_db(); self.assertEqual(plan.next_date,timezone.localdate())
        transition(self.admin,order.pk,'cerrada')
        plan.refresh_from_db(); self.assertEqual(plan.next_date,timezone.localdate()+timezone.timedelta(days=30))

    def test_all_admin_pages_render(self):
        self.client.force_login(self.admin)
        for module in REGISTRY.values():
            with self.subTest(module=module.key):
                self.assertEqual(self.client.get(reverse('list',args=[module.key]),follow=True).status_code,200)
                if module.create:
                    self.assertEqual(self.client.get(reverse('create',args=[module.key])).status_code,200)
        for name in ('dashboard','calendar','reports','settings'):
            self.assertEqual(self.client.get(reverse(name)).status_code,200)

    def test_empty_dashboard_no_invented_percentages(self):
        empty=m.User.objects.create_user('vacio',organization=self.other,role='conductor')
        self.client.force_login(empty)
        response=self.client.get(reverse('dashboard'))
        self.assertIsNone(response.context['availability'])
        self.assertIsNone(response.context['approval'])

    def test_csrf_and_api_authorization(self):
        client=Client(enforce_csrf_checks=True)
        self.assertEqual(client.get('/api/v1/buses/').status_code,401)
        client.force_login(self.driver)
        self.assertEqual(client.get('/api/v1/personal/').status_code,403)
        order=self.order(assigned_to=self.tech)
        self.assertEqual(client.post(reverse('action',args=['ordenes',order.pk]),{'estado':'en_progreso'}).status_code,403)

    def test_csv_formula_is_escaped(self):
        from .views import csv_safe
        self.assertEqual(csv_safe('=HYPERLINK(1)'),"'=HYPERLINK(1)")

    def test_form_replay_does_not_duplicate_requests(self):
        self.client.force_login(self.driver)
        payload={'bus':self.bus.pk,'title':'Prueba doble','description':'Descripción','priority':'media','_token':str(uuid.uuid4())}
        for _ in range(2):
            self.assertEqual(self.client.post(reverse('create',args=['solicitudes']),payload).status_code,302)
        self.assertEqual(m.MaintenanceRequest.objects.filter(title='Prueba doble').count(),1)

    def test_purchase_receipt_does_not_duplicate_stock(self):
        from .services import receive_purchase
        part=m.Part.objects.create(organization=self.org,code='COMPRA-1',name='Filtro')
        supplier=m.Supplier.objects.create(organization=self.org,name='Proveedor prueba')
        purchase=m.PurchaseOrder.objects.create(organization=self.org,supplier=supplier,part=part,quantity=5,unit_cost=12,reference='Compra prueba')
        receive_purchase(self.admin,purchase.pk)
        receive_purchase(self.admin,purchase.pk)
        part.refresh_from_db()
        self.assertEqual(part.quantity,Decimal('5'))
        self.assertEqual(m.StockMovement.objects.filter(part=part).count(),1)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse('detail',args=['compras',purchase.pk])).status_code,200)

    def test_stale_part_edit_preserves_current_stock(self):
        part=m.Part.objects.create(organization=self.org,code='STALE-1',name='Filtro',quantity=1)
        module=REGISTRY['repuestos']
        form=form_class(module)({'code':part.code,'name':'Filtro actualizado','unit':'unidad','minimum':'1','unit_cost':'10'},instance=part,user=self.admin,module=module)
        self.assertTrue(form.is_valid(),form.errors)
        m.Part.objects.filter(pk=part.pk).update(quantity=7)
        save_record(form,self.admin)
        part.refresh_from_db()
        self.assertEqual(part.quantity,Decimal('7'))

    def test_api_serializes_values_and_denies_other_organization(self):
        self.client.force_login(self.admin)
        response=self.client.get(reverse('api-list',args=['buses']))
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['resultados'][0]['odometer'],'0.0')
        self.assertEqual(self.client.get(reverse('api-detail',args=['buses',self.foreign.pk])).status_code,404)

    def test_program_copies_tasks_into_plan(self):
        from django.utils import timezone
        program=m.ServiceProgram.objects.create(organization=self.org,name='Programa prueba',tasks='Revisar filtros',interval_days=30)
        module=REGISTRY['preventivos']
        form=form_class(module)({'bus':self.bus.pk,'title':'Servicio','program':program.pk,'tasks':'',
             'next_date':timezone.localdate().isoformat(),'interval_days':'0','interval_km':'0','interval_hours':'0','active':'on'},user=self.admin,module=module)
        self.assertTrue(form.is_valid(),form.errors)
        plan=save_record(form,self.admin)
        self.assertEqual(plan.tasks,'Revisar filtros')
        self.assertEqual(plan.interval_days,30)

    def test_new_password_is_checked_against_new_username(self):
        module=REGISTRY['personal']
        form=form_class(module)({'username':'operador_setram_verificacion','role':'tecnico','is_active':'on',
              'password':'operador_setram_verificacion'},user=self.admin,module=module)
        self.assertFalse(form.is_valid())
        self.assertIn('password',form.errors)

    def test_document_rejects_disguised_html(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        module=REGISTRY['documentos']
        form=form_class(module)({'title':'Archivo de prueba','kind':'manual'},
            {'file':SimpleUploadedFile('manual.pdf',b'<html>contenido</html>',content_type='application/pdf')},user=self.admin,module=module)
        self.assertFalse(form.is_valid())
        self.assertIn('file',form.errors)


class ConcurrencyTests(TransactionTestCase):
    def test_two_simultaneous_outputs_cannot_consume_same_last_part(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import close_old_connections, connections
        org=m.Organization.objects.create(name='Concurrencia prueba')
        admin=m.User.objects.create_user('concurrencia',organization=org,role='administrador')
        bus=m.Bus.objects.create(organization=org,code='CON-01',plate='CON-01',brand='Prueba',model='Prueba',year=2025)
        order=m.WorkOrder.objects.create(organization=org,bus=bus,title='Prueba concurrente',description='Prueba')
        part=m.Part.objects.create(organization=org,code='ULTIMO-1',name='Último repuesto',quantity=1)
        gate=Barrier(2)
        def consume():
            close_old_connections()
            try:
                actor=m.User.objects.get(pk=admin.pk)
                module=REGISTRY['movimientos']
                form=form_class(module)({'part':part.pk,'kind':'salida','quantity':'1','unit_cost':'1',
                     'work_order':order.pk,'reference':'Concurrente'},user=actor,module=module)
                if not form.is_valid(): raise AssertionError(form.errors)
                gate.wait(timeout=20)
                try: save_record(form,actor); return 'ok'
                except ValidationError: return 'insuficiente'
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(consume),pool.submit(consume)]
            results=[future.result(timeout=40) for future in futures]
        self.assertEqual(sorted(results),['insuficiente','ok'])
        part.refresh_from_db()
        self.assertEqual(part.quantity,Decimal('0'))
        self.assertEqual(m.StockMovement.objects.filter(part=part).count(),1)
