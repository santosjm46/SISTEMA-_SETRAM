import copy
import json
from decimal import Decimal
from unittest.mock import patch
from django.test import TestCase,Client
from django.core.exceptions import PermissionDenied,ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from cmms import models as m
from cmms.registry import REGISTRY
from cmms.forms import form_class
from cmms.services import save_record,convert_request
from cmms.modules.catalog_seeds import bundle,preview,apply,SPECS
from cmms.modules.importing import import_catalog


class InitialCatalogTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org=m.Organization.objects.create(name='Catálogos prueba')
        cls.other=m.Organization.objects.create(name='Otro catálogo')
        cls.admin=m.User.objects.create_user('cat_admin',organization=cls.org,role='administrador')
        cls.driver=m.User.objects.create_user('cat_conductor',organization=cls.org,role='conductor')
        cls.bus=m.Bus.objects.create(organization=cls.org,driver=cls.driver,code='CAT-01',plate='CAT-01',brand='Prueba',model='Prueba',year=2025)

    def setUp(self):self.client.force_login(self.admin)

    def test_preview_and_seed_preserve_zero_stock_and_provenance(self):
        data=preview(self.admin)
        self.assertEqual(sum(group['new'] for group in data['groups']),122)
        self.assertEqual(m.Part.objects.count(),0)
        result=apply(self.admin,list(SPECS))
        self.assertEqual(sum(row['creados'] for row in result.values()),122)
        self.assertEqual(m.PartCategory.objects.count(),26)
        self.assertEqual(m.FailureType.objects.count(),32)
        self.assertEqual(m.Part.objects.count(),40)
        self.assertEqual(m.ServiceTask.objects.count(),18)
        self.assertEqual(m.ServiceProgram.objects.count(),6)
        self.assertFalse(m.Part.objects.exclude(quantity=0,unit_cost=0,minimum=0,auto_demand=False).exists())
        self.assertFalse(m.ServiceProgram.objects.exclude(interval_days=0,interval_km=0,interval_hours=0).exists())
        self.assertFalse(m.ServiceTask.objects.exclude(estimated_hours=0).exists())
        self.assertIn('BusCMMS',m.PartCategory.objects.first().catalog_source)
        self.assertNotIn('BusCMMS',m.Part.objects.first().catalog_source)
        for program in m.ServiceProgram.objects.all():self.assertEqual(program.task_templates.count(),len(program.tasks.splitlines()))
        self.assertFalse(m.StockMovement.objects.exists());self.assertFalse(m.WorkOrder.objects.exists());self.assertFalse(m.PreventivePlan.objects.exists())
        dashboard=self.client.get(reverse('dashboard'))
        self.assertEqual(dashboard.context['low_stock_count'],0)

    def test_retries_keep_existing_manual_records_and_organization(self):
        original=m.Part.objects.create(organization=self.org,code='GEN-FIL-01',name='Filtro identificado por SETRAM',unit_cost=18,minimum=2,quantity=3,application_notes='Especificación propia')
        same_name=m.ServiceTask.objects.create(organization=self.org,name='Verificación visual de motor y fugas',instructions='Procedimiento propio',estimated_hours=2)
        m.Part.objects.create(organization=self.other,code='GEN-FIL-02',name='Fuera del ámbito',quantity=100)
        apply(self.admin,list(SPECS));audit_count=m.AuditEvent.objects.count()
        again=apply(self.admin,list(SPECS))
        self.assertEqual(sum(row['creados'] for row in again.values()),0)
        self.assertEqual(m.AuditEvent.objects.count(),audit_count)
        original.refresh_from_db();same_name.refresh_from_db()
        self.assertEqual((original.quantity,original.unit_cost,original.application_notes),(Decimal('3'),Decimal('18'),'Especificación propia'))
        self.assertEqual(same_name.instructions,'Procedimiento propio')
        self.assertEqual(m.Part.objects.filter(organization=self.org).count(),40)
        self.assertEqual(m.Part.objects.get(organization=self.other).quantity,100)

    def test_catalog_permissions_visibility_and_csrf(self):
        self.client.force_login(self.driver)
        self.assertEqual(self.client.get(reverse('catalog-presets')).status_code,403)
        self.assertEqual(self.client.post(reverse('catalog-presets'),{'catalogos':['repuestos']}).status_code,403)
        self.client.force_login(self.admin)
        self.org.enabled_modules={'repuestos':False};self.org.save()
        self.admin.organization.refresh_from_db()
        with self.assertRaises(PermissionDenied):apply(self.admin,['tipos_falla','repuestos'])
        self.assertFalse(m.FailureType.objects.exists())
        csrf=Client(enforce_csrf_checks=True);csrf.force_login(self.admin)
        self.assertEqual(csrf.post(reverse('catalog-presets'),{'catalogos':['tipos_falla']}).status_code,403)

    def test_invalid_late_entry_rolls_back_whole_catalog(self):
        invalid=copy.deepcopy(bundle());invalid['catalogs']['repuestos'][-1]['name']='x'*141
        with patch('cmms.modules.catalog_seeds.bundle',return_value=invalid):
            with self.assertRaises(ValidationError):apply(self.admin,list(SPECS))
        for _,model,_ in SPECS.values():self.assertFalse(model.objects.exists())
        self.assertFalse(m.AuditEvent.objects.exists());self.assertFalse(m.CatalogImport.objects.exists())

    def test_failure_classification_is_scoped_and_survives_conversion(self):
        apply(self.admin,['tipos_falla'])
        fault=m.FailureType.objects.get(code='F-FRE-01')
        module=REGISTRY['solicitudes']
        form=form_class(module)({'bus':self.bus.pk,'title':'Alarma reportada','description':'Evidencia de prueba','priority':'alta','failure_type':fault.pk},user=self.driver,module=module)
        self.assertTrue(form.is_valid(),form.errors)
        request=save_record(form,self.driver);order=convert_request(self.admin,request.pk)
        self.assertEqual(order.failure_type,fault);self.assertEqual(order.failure_category,'frenos')
        other=m.FailureType.objects.create(organization=self.other,code='AJENO',name='Ajeno',system='motor')
        payload={'bus':self.bus.pk,'title':'Prueba','description':'Detalle','priority':'media','kind':'correctivo','labor_cost':0,'failure_category':'otro','failure_type':fault.pk}
        module=REGISTRY['ordenes'];form=form_class(module)(payload,user=self.admin,module=module)
        self.assertTrue(form.is_valid(),form.errors)
        self.assertEqual(save_record(form,self.admin).failure_category,'frenos')
        payload['failure_type']=other.pk;form=form_class(module)(payload,user=self.admin,module=module)
        self.assertFalse(form.is_valid());self.assertIn('failure_type',form.errors)
        fault.active=False;fault.save();payload['failure_type']=fault.pk
        self.assertFalse(form_class(module)(payload,user=self.admin,module=module).is_valid())
        retained=form_class(module)(instance=order,user=self.admin,module=module)
        self.assertTrue(retained.fields['failure_type'].queryset.filter(pk=fault.pk).exists())

    def test_new_catalogs_accept_atomic_imports_with_scoped_actor(self):
        for key,record in [('tipos_falla',{'code':'IMP-F01','name':'Síntoma propio','system':'motor','active':True}),
                           ('categorias_repuesto',{'code':'setram-propia','name':'Categoría propia','active':True}),
                           ('biblioteca_tareas',{'name':'Tarea importada','instructions':'Procedimiento propio','estimated_hours':'1','active':True})]:
            result,repeated=import_catalog(self.admin,key,SimpleUploadedFile(key+'.json',json.dumps([record]).encode()))
            self.assertFalse(repeated);self.assertEqual(result.records,1)
        category=m.PartCategory.objects.get();form=form_class(REGISTRY['repuestos'])(user=self.admin,module=REGISTRY['repuestos'])
        self.assertIn(category.name,form.category_options)

    def test_catalog_page_adds_selected_sections_only(self):
        url=reverse('catalog-presets')
        self.assertContains(self.client.get(url),'Catálogos iniciales')
        response=self.client.post(url,{'catalogos':['tipos_falla']},follow=True)
        self.assertEqual(response.status_code,200)
        self.assertEqual(m.FailureType.objects.count(),32);self.assertEqual(m.Part.objects.count(),0)
        self.assertEqual(self.client.get(reverse('list',args=['tipos_falla']),{'system':'frenos'}).context['count'],4)
