"""Filtros, indicadores y agrupación de formularios compartidos por dominio."""
from decimal import Decimal
from django.db import models
from django.db.models import Sum,Avg,F,Count,CharField
from django.db.models.functions import Cast,TruncDate
from django.utils import timezone
from django.utils.dateparse import parse_date
from cmms import models as m

DATE_FIELDS=('date','measured_at','occurred_at','started_at','created_at','date_joined')
RELATION_FILTERS=('department','driver','assigned_to','supplier','responsible','purchase','program','user')

def date_field(module):
    names={f.name for f in module.model._meta.fields}
    return next((name for name in DATE_FIELDS if name in names),None)

def apply_filters(qs,module,params):
    fields={f.name:f for f in module.model._meta.fields}
    for name in ('priority','result','kind','role','level','risk','verification','category','impact','system'):
        if name in fields and fields[name].choices and params.get(name): qs=qs.filter(**{name:params[name]})
    for name in RELATION_FILTERS:
        if name in fields and isinstance(fields[name],models.ForeignKey) and str(params.get(name,'')).isdigit(): qs=qs.filter(**{name+'_id':int(params[name])})
    if 'active' in fields and params.get('activo') in ('1','0'): qs=qs.filter(active=params['activo']=='1')
    field=date_field(module)
    if field:
        suffix='__date' if isinstance(fields[field],models.DateTimeField) else ''
        for key,op in (('desde','gte'),('hasta','lte')):
            try: value=parse_date(params.get(key,'') or '')
            except (ValueError,TypeError): value=None
            if value: qs=qs.filter(**{field+suffix+'__'+op:value})
    return qs

def filters(module,params,qs=None):
    fields={f.name:f for f in module.model._meta.fields}
    labels={'priority':'Prioridad','result':'Resultado','kind':'Tipo','role':'Rol','level':'Nivel','risk':'Riesgo','verification':'Conciliación','category':'Categoría','impact':'Impacto','system':'Sistema'}
    result=[{'name':name,'label':label,'choices':fields[name].choices,'value':params.get(name,'')} for name,label in labels.items() if name in fields and fields[name].choices]
    if 'active' in fields: result.append({'name':'activo','label':'Vigencia','choices':[('1','Activos'),('0','Inactivos')],'value':params.get('activo','')})
    if qs is not None:
        for name in RELATION_FILTERS:
            if name in fields and isinstance(fields[name],models.ForeignKey):
                ids=qs.order_by().values_list(name+'_id',flat=True)
                objects=fields[name].remote_field.model.objects.filter(pk__in=ids)
                result.append({'name':name,'label':fields[name].verbose_name,'choices':[(str(obj.pk),str(obj)) for obj in objects],'value':params.get(name,'')})
    return result

def statistics(module,qs,user):
    rows=[{'label':'Registros de la consulta','value':qs.count()}]
    def add(label,value): rows.append({'label':label,'value':value})
    fields={f.name:f for f in module.model._meta.fields}
    if 'status' in fields:
        for value,label in fields['status'].choices[:5]: add(label,qs.filter(status=value).count())
    elif 'active' in fields:
        add('Activos',qs.filter(active=True).count()); add('Inactivos',qs.filter(active=False).count())
    if module.model is m.Bus:
        add('Km acumulados',qs.aggregate(v=Sum('odometer'))['v'] or 0)
        add('Seguro vencido',qs.filter(insurance_expiry__lt=timezone.localdate()).count())
    elif module.model is m.WorkOrder and user.role in ('administrador','supervisor'):
        closed=qs.filter(status='cerrada')
        add('Costo cerrado · Bs',sum((row.total_cost for row in closed),Decimal(0)))
    elif module.model is m.Part:
        add('Bajo mínimo',qs.filter(minimum__gt=0,quantity__lte=F('minimum')).count())
        add('Valor referencial · Bs',sum((row.quantity*row.unit_cost for row in qs),Decimal(0)))
    elif module.model is m.Supplier:
        avg=qs.aggregate(v=Avg('lead_time_days'))['v']; add('Entrega media · días',round(avg,1) if avg is not None else 'Sin datos')
    elif module.model is m.FuelEntry:
        liters=qs.aggregate(v=Sum('liters'))['v'] or 0; cost=qs.aggregate(v=Sum('cost'))['v'] or 0
        add('Litros',liters); add('Importe · Bs',cost); add('Costo medio · Bs/L',round(cost/liters,2) if liters else 'Sin datos')
        add('Pendientes de conciliar',qs.filter(verification='pendiente').count())
    elif module.model is m.Inspection:
        add('Aprobadas',qs.filter(result='aprobado').count()); add('Críticas abiertas',qs.filter(result='critico',resolved=False).count())
    elif module.model is m.PreventivePlan:
        add('Vencidos',sum(row.overdue for row in qs.select_related('bus')))
    elif module.model is m.Document:
        add('Vencidos',qs.filter(expiry__lt=timezone.localdate()).count())
        add('Vencen en 30 días',qs.filter(expiry__range=(timezone.localdate(),timezone.localdate()+timezone.timedelta(days=30))).count())
    elif module.model is m.Tire:
        add('Bajo umbral interno',qs.filter(status='montado',tread_mm__lt=user.organization.minimum_tread_mm).count())
        add('Inversión · Bs',qs.aggregate(v=Sum('cost'))['v'] or 0)
        avg=qs.aggregate(v=Avg('tread_mm'))['v']; add('Profundidad media · mm',round(avg,2) if avg is not None else 'Sin datos')
    elif module.model is m.User: add('Licencias vencidas',qs.filter(license_expiry__lt=timezone.localdate()).count())
    return rows

def analytics(module,qs):
    fields={f.name:f for f in module.model._meta.fields}
    groups=[]
    for name in ('status','result','priority','kind','role','level','risk','verification'):
        if name in fields and fields[name].choices:
            groups.append({'title':fields[name].verbose_name,'rows':[{'label':label,'value':qs.filter(**{name:value}).count()} for value,label in fields[name].choices]})
    field=date_field(module)
    trend=[]
    if field:
        values=qs.order_by().annotate(day=TruncDate(field) if isinstance(fields[field],models.DateTimeField) else F(field)).values('day').annotate(count=Count('pk')).order_by('-day')[:30]
        trend=[{'label':row['day'].strftime('%d/%m') if row['day'] else 'Sin fecha','value':row['count']} for row in reversed(list(values))]
    return groups,trend

def activity(module,qs,user):
    ids=qs.order_by().annotate(text_id=Cast('pk',CharField())).values('text_id')
    return m.AuditEvent.objects.filter(organization=user.organization,entity=module.model._meta.label,object_id__in=ids).select_related('actor')[:50]

LAYOUTS={
 'buses':[('Identificación y características',('code','vin','brand','model','year','capacity','fuel_type')),('Registro y vida útil',('plate','registration_expiry','insurance_expiry','odometer','engine_hours','service_date','design_life_years')),('Asignación y operación',('department','driver','route','status','notes'))],
 'personal':[('Datos del funcionario',('username','employee_code','first_name','last_name','email','phone')),('Rol y asignación',('role','department','is_active','password')),('Licencia de conducción',('license_number','license_category','license_expiry'))],
 'ordenes':[('Información básica',('bus','failure_type','title','kind','priority','reported_by','assigned_to','program')),('Tareas y duración',('task_templates','additional_tasks','estimated_hours')),('Información adicional',('failure_category','location','due_date')),('Costo y presupuesto',('budget','billing_mode','worked_hours','labor_rate','labor_cost','external_cost')),('Notas y evidencia',('description','remarks','resolution'))],
 'solicitudes':[('Bus y clasificación',('bus','failure_type','title','priority')),('Descripción del reporte',('description',))],
 'proveedores':[('Identidad y contacto',('name','tax_id','contact','phone','email','address')),('Condiciones de suministro',('active','lead_time_days','payment_terms'))],
 'repuestos':[('Identificación',('code','name','category','manufacturer','unit','storage_location')),('Reposición y costo',('minimum','unit_cost','supplier'))],
 'neumaticos':[('Identificación del neumático',('serial','brand','size','cost')),('Montaje y seguimiento',('bus','position','status','installed_at','installed_km')),('Desgaste y reencauche',('tread_mm','original_tread_mm','retread_count'))],
 'documentos':[('Clasificación y vínculos',('title','kind','bus','user','work_order')),('Archivo y vigencia',('file','expiry','notes'))],
 'programas':[('Programa y tareas',('name','tasks','task_templates')),('Frecuencia sugerida',('interval_days','interval_km','interval_hours','active'))],
 'preventivos':[('Bus y procedimiento',('bus','title','program','tasks')),('Vencimientos e intervalos',('next_date','next_km','next_hours','interval_days','interval_km','interval_hours','active'))],
 'combustible':[('Carga de combustible',('bus','date','odometer','liters','cost','full_tank')),('Respaldo y origen',('station','reference'))],
}

def form_groups(form,module):
    layout=LAYOUTS.get(module.key,[])
    if module.model is m.Inspection:
        layout=[('Datos de la inspección',('bus','kind','date','location','odometer','checklist')),('Puntos de verificación',tuple(n for n in form.fields if n.startswith('item_'))),('Hallazgos y firma',('findings','signature','confirm'))]
    if not layout: layout=[('Datos del registro',tuple(form.fields))]
    used=set(); result=[]
    for title,names in layout:
        current=[form[name] for name in names if name in form.fields]; used.update(names)
        if current: result.append({'title':title,'fields':current})
    remaining=[form[name] for name in form.fields if name not in used]
    if remaining: result.append({'title':'Información complementaria','fields':remaining})
    return result

def related_sections(obj,user):
    from cmms.registry import REGISTRY,scoped
    from cmms.module import enabled
    mappings=[]
    if isinstance(obj,m.Bus): mappings=[(key,'bus') for key in ('ordenes','preventivos','inspecciones','combustible','neumaticos','documentos','telemetria','incidentes')]
    if isinstance(obj,m.WorkOrder): mappings=[(key,'work_order') for key in ('tareas_ot','comentarios_ot','movimientos','documentos')]
    if isinstance(obj,m.Supplier): mappings=[('repuestos','supplier'),('compras','supplier'),('contratos','supplier'),('facturacion','supplier')]
    if isinstance(obj,m.ServiceProgram): mappings=[('preventivos','program'),('ordenes','program')]
    if isinstance(obj,m.Department): mappings=[('buses','department'),('personal','department'),('turnos_patio','department')]
    if isinstance(obj,m.User): mappings=[('buses','driver'),('jornadas','driver'),('recorridos','driver'),('documentos','user')]
    if isinstance(obj,m.PurchaseOrder): mappings=[('lineas_compra','purchase'),('recepciones','purchase')]
    result=[]
    for key,relation in mappings:
        mod=REGISTRY[key]
        if user.role not in mod.read or not enabled(user,key): continue
        qs=scoped(mod,user).filter(**{relation:obj})
        result.append({'key':key,'title':mod.label,'count':qs.count(),'objects':list(qs[:10]),'parameter':{'bus':'bus','work_order':'ot'}.get(relation,relation)})
    return result
