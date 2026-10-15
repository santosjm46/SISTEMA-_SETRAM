import calendar
import csv
import io
import json
import uuid
from datetime import date, timedelta
from decimal import Decimal
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Q, Sum, F
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.formats import date_format
from django.views.decorators.http import require_POST, require_GET
from . import models as m
from .forms import form_class
from .registry import REGISTRY, MANAGERS, buses_for, scoped
from .services import audit, save_record, transition, convert_request, generate_preventive, receive_purchase
from .module import enabled


def access(request, key):
    module = REGISTRY.get(key)
    if not module: raise Http404
    if not request.user.organization_id or request.user.role not in module.read or not enabled(request.user,key):
        raise PermissionDenied
    return module


def display(obj, name):
    method = getattr(obj,f'get_{name}_display',None)
    value = method() if method else getattr(obj,name,None)
    if isinstance(value,bool): return 'Sí' if value else 'No'
    if value is None or value == '': return '—'
    if hasattr(value,'tzinfo'):
        if timezone.is_aware(value): value = timezone.localtime(value)
        return date_format(value,'d/m/Y H:i')
    if isinstance(value,date): return date_format(value,'d/m/Y')
    if isinstance(value,Decimal): return f'{value:,.2f}'.replace(',',' ').replace('.',',')
    return str(value)


def queryset(request, module):
    qs = scoped(module,request.user)
    search = request.GET.get('q','').strip()[:120]
    if search:
        query = Q()
        for field in module.search: query |= Q(**{field+'__icontains':search})
        qs = qs.filter(query)
    if request.GET.get('estado') and any(f.name == 'status' for f in module.model._meta.fields):
        qs = qs.filter(status=request.GET['estado'])
    if request.GET.get('ot','').isdigit() and any(f.name == 'work_order' for f in module.model._meta.fields):
        qs=qs.filter(work_order_id=int(request.GET['ot']))
    if request.GET.get('bus','').isdigit() and any(f.name == 'bus' for f in module.model._meta.fields):
        qs = qs.filter(bus_id=int(request.GET['bus']))
    from .modules.workspace import apply_filters
    return apply_filters(qs,module,request.GET).order_by('-pk')


@login_required
def dashboard(request):
    if not request.user.organization_id: raise PermissionDenied
    from .modules.portal.dashboard import context
    return render(request,'cmms/dashboard.html',context(request))



@login_required
def list_records(request, key):
    module = access(request,key)
    if module.route and request.GET.get('vista') not in ('registros','actividad','analitica'): return redirect(module.route)
    qs = queryset(request,module)
    page = Paginator(qs,20).get_page(request.GET.get('pagina'))
    rows = [{'obj':obj,'values':[display(obj,name) for name,_ in module.columns]} for obj in page]
    statuses = module.model._meta.get_field('status').choices if any(f.name == 'status' for f in module.model._meta.fields) else []
    from .modules.workspace import statistics,filters,analytics,activity,date_field
    groups,trend=analytics(module,qs)
    params=request.GET.copy(); params.pop('pagina',None)
    pagination=params.urlencode()
    return render(request,'cmms/list.html',{'module':module,'page_title':module.label,'page':page,
        'rows':rows,'count':qs.count(),'can_create':request.user.role in module.create,
        'statuses':statuses,'buses':buses_for(request.user),'has_bus':any(f.name == 'bus' for f in module.model._meta.fields),
        'extended_workspace':True,'stats':statistics(module,qs,request.user),'extra_filters':filters(module,request.GET,qs),'has_date':bool(date_field(module)),
        'analytics_groups':groups,'trend':trend,'activity':activity(module,qs,request.user) if request.GET.get('vista')=='actividad' else [],'pagination_query':pagination})


@login_required
def detail(request, key, pk):
    module = access(request,key)
    obj = get_object_or_404(scoped(module,request.user),pk=pk)
    excluded = {'organization','updated_at','password','password_hash','digest','last_login','is_superuser','is_staff'}
    excluded.add('dashboard_widgets')
    if request.user.role not in MANAGERS and isinstance(obj,m.WorkOrder): excluded.update(('labor_cost','labor_rate','external_cost','budget','billing_mode'))
    if isinstance(obj,m.DocumentAnalysis): excluded.update(('extracted_text','findings','metadata'))
    detail_labels={'received_at':'Recepción completa','receipt':'Movimiento de la primera recepción',
                   'created_by':'Registrado por','reviewed_by':'Revisado por','reviewed_at':'Fecha de revisión',
                   'schedule':'Programación','actor':'Responsable','module':'Módulo',
                   'filename':'Nombre del archivo','records':'Registros incluidos'}
    details = [(detail_labels.get(f.name,f.verbose_name),display(obj,f.name)) for f in module.model._meta.fields if f.name not in excluded and f.name not in ('file','snapshot')]
    actions = []
    if isinstance(obj,m.WorkOrder):
        if obj.status == 'abierta': actions = [('en_progreso','Iniciar trabajo')]
        elif obj.status == 'en_progreso': actions = [('revision','Enviar a revisión')]
        elif obj.status == 'revision' and request.user.role in MANAGERS: actions = [('cerrada','Aprobar y cerrar'),('en_progreso','Devolver a ejecución')]
    if isinstance(obj,m.MaintenanceRequest) and obj.status in ('pendiente','en_revision') and request.user.role in MANAGERS:
        actions=[('en_revision','Revisar solicitud'),('rechazada','Rechazar con motivo')]
    if isinstance(obj,m.FuelEntry) and request.user.role in MANAGERS:
        actions=[('verificado','Verificar comprobante'),('observado','Registrar diferencia')]
    if isinstance(obj,(m.TeamJoinRequest,m.ReactivationRequest)) and request.user.role=='administrador' and obj.status=='pendiente':
        actions=[('aprobada','Aprobar tras verificar identidad'),('rechazada','Rechazar solicitud')]
    if isinstance(obj,m.PurchaseDemand) and obj.status=='pendiente' and request.user.role in MANAGERS:actions=[('generar_compra','Crear orden de compra')]
    if isinstance(obj,m.PurchaseOrder) and obj.status in ('pedido','parcial') and request.user.role in MANAGERS:
        actions = [('recibido','Confirmar recepción completa')]
    if key in ('recomendaciones','retiros','incidentes') and request.user.role in MANAGERS and not obj.work_order_id and obj.status not in ('descartada','resuelto','atendido'):
        actions=[('generar_ot','Generar orden de trabajo')]
    events = m.AuditEvent.objects.filter(organization_id=request.user.organization_id,entity=obj._meta.label,object_id=str(obj.pk)).select_related('actor')[:20]
    from .modules.workspace import related_sections
    purchase_lines=[]
    if isinstance(obj,m.PurchaseOrder):
        purchase_lines=[{'id':0,'part':obj.part,'ordered':obj.quantity,'received':obj.received_quantity,'pending':obj.quantity-obj.received_quantity,'token':uuid.uuid4()}]+[
            {'id':line.pk,'part':line.part,'ordered':line.quantity,'received':line.received_quantity,'pending':line.quantity-line.received_quantity,'token':uuid.uuid4()} for line in obj.purchaseline_set.all()]
    return render(request,'cmms/detail.html',{'module':module,'obj':obj,'page_title':module.singular,
        'details':details,'can_edit':request.user.role in module.edit and not (isinstance(obj,m.WorkOrder) and obj.status == 'cerrada'),
        'actions':actions,'events':events,'snapshot':getattr(obj,'snapshot',None),
        'is_request':isinstance(obj,m.MaintenanceRequest),'is_plan':isinstance(obj,m.PreventivePlan),
        'is_purchase':isinstance(obj,m.PurchaseOrder),
        'is_order':isinstance(obj,m.WorkOrder),'is_document':isinstance(obj,m.Document),
        'analysis':obj if isinstance(obj,m.DocumentAnalysis) else None,
        'order_tasks':obj.workordertask_set.all() if isinstance(obj,m.WorkOrder) else None,
        'extended_workspace':True,'related_sections':related_sections(obj,request.user),'purchase_lines':purchase_lines,
        'photos':m.BusPhoto.objects.filter(bus=obj) if isinstance(obj,m.Bus) and enabled(request.user,'fotos_bus') else [],
        'is_photo':isinstance(obj,m.BusPhoto),'is_report_run':isinstance(obj,m.ReportRun),
        'can_manage_tasks':isinstance(obj,m.WorkOrder) and request.user.role in REGISTRY['tareas_ot'].create and enabled(request.user,'tareas_ot')})


@login_required
def edit_record(request,key,pk=None):
    module = access(request,key)
    if request.user.role not in (module.edit if pk else module.create): raise PermissionDenied
    obj = get_object_or_404(scoped(module,request.user),pk=pk) if pk else None
    if isinstance(obj,m.WorkOrder) and obj.status == 'cerrada': raise PermissionDenied
    initial = {'checklist':request.GET.get('plantilla')} if module.model is m.Inspection else {}
    if module.model is m.WorkOrderTask and request.GET.get('ot','').isdigit(): initial['work_order']=request.GET['ot']
    if module.model is m.PurchaseLine and request.GET.get('purchase','').isdigit(): initial['purchase']=request.GET['purchase']
    if any(f.name=='bus' for f in module.model._meta.fields) and request.GET.get('bus','').isdigit(): initial['bus']=request.GET['bus']
    form = form_class(module)(request.POST or None,request.FILES or None,instance=obj,user=request.user,module=module,initial=initial)
    token = request.POST.get('_token') if request.method == 'POST' else str(uuid.uuid4())
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                if pk:
                    result = save_record(form,request.user)
                else:
                    try: token_uuid = uuid.UUID(token or '')
                    except ValueError: raise ValidationError('El formulario expiró. Recarga la página.')
                    # Una restricción única serializa envíos concurrentes del mismo formulario.
                    existing = m.Submission.objects.filter(token=token_uuid,actor=request.user,module=key).first()
                    if existing:
                        return redirect('detail',key=key,pk=existing.object_id)
                    submission = m.Submission.objects.create(token=token_uuid,actor=request.user,module=key,object_id=0)
                    result = save_record(form,request.user)
                    submission.object_id = result.pk
                    submission.save(update_fields=['object_id'])
            messages.success(request,'Registro guardado correctamente.')
            return redirect('detail',key=key,pk=result.pk)
        except ValidationError as exc:
            form.add_error(None,' '.join(exc.messages))
        except IntegrityError:
            existing = m.Submission.objects.filter(token=token,actor=request.user,module=key).first()
            if existing: return redirect('detail',key=key,pk=existing.object_id)
            form.add_error(None,'No se guardó el registro: código duplicado o datos inconsistentes.')
    from .modules.workspace import form_groups
    return render(request,'cmms/form.html',{'module':module,'form':form,'token':token,'form_groups':form_groups(form,module),
        'extended_workspace':True,'wizard':module.model is m.WorkOrder and not pk,
        'page_title':('Editar ' if pk else 'Registrar ')+module.singular.lower(),'editing':bool(pk)})


@login_required
@require_POST
def action(request,key,pk):
    module = access(request,key)
    get_object_or_404(scoped(module,request.user),pk=pk)
    try:
        if key == 'ordenes': result = transition(request.user,pk,request.POST.get('estado'))
        elif key in ('ingresos_equipo','reactivaciones'):
            from .modules.personal.joining import decide
            result=decide(request.user,key,pk,request.POST.get('estado'),request.POST.get('notes',''))
            return redirect('detail',key=key,pk=pk)
        elif key=='demandas_compra':
            from .modules.inventario.services import demand_to_purchase
            result=demand_to_purchase(request.user,pk)
            return redirect('detail',key='compras',pk=result.pk)
        elif key in ('solicitudes','combustible') and request.POST.get('estado'):
            from .modules.extended_views import review_record
            result=review_record(request.user,key,pk,request.POST.get('estado'),request.POST.get('notes',''))
            messages.success(request,'Revisión registrada.')
            return redirect('detail',key=key,pk=pk)
        elif key == 'solicitudes': result = convert_request(request.user,pk)
        elif key == 'preventivos': result = generate_preventive(request.user,pk)
        elif key == 'compras': result = receive_purchase(request.user,pk)
        elif key in ('recomendaciones','retiros','incidentes'):
            from .modules.actions import create_order
            result=create_order(request.user,key,pk)
        else: raise Http404
        messages.success(request,'Operación completada.')
        return redirect('detail',key='compras' if key == 'compras' else 'ordenes',pk=result.pk)
    except ValidationError as exc:
        messages.error(request,' '.join(exc.messages))
        return redirect('detail',key=key,pk=pk)


def csv_safe(value):
    text = str(value)
    return "'"+text if text.lstrip().startswith(('=','+','-','@','\t','\r')) else text


@login_required
@require_GET
def export_csv(request,key):
    module = access(request,key)
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="setram_{key}.csv"'
    response.write('\ufeff')
    writer = csv.writer(response,delimiter=';')
    writer.writerow([label for _,label in module.columns])
    for obj in queryset(request,module).iterator():
        writer.writerow([csv_safe(display(obj,name)) for name,_ in module.columns])
    audit(request.user,'Exportación CSV',request.user,{'modulo':key})
    return response


@login_required
def document_file(request,pk):
    access(request,'documentos')
    doc = get_object_or_404(scoped(REGISTRY['documentos'],request.user),pk=pk)
    return FileResponse(doc.file.open('rb'),as_attachment=True,filename=doc.file.name.rsplit('/',1)[-1])


@login_required
def calendar_view(request):
    from .modules.flota.calendar import view
    return view(request)



@login_required
def reports(request):
    if request.user.role not in MANAGERS or not request.user.organization_id: raise PermissionDenied
    orders = scoped(REGISTRY['ordenes'],request.user)
    fuel = scoped(REGISTRY['combustible'],request.user)
    from .modules.administracion.reports import CATALOG
    return render(request,'cmms/reports.html',{'page_title':'Informes y costos','catalog':[{'key':key,'title':title} for key,(title,_) in CATALOG.items()],
        'modules':[v for v in REGISTRY.values() if request.user.role in v.read and v.key != 'auditoria' and enabled(request.user,v.key)],
        'labor':orders.filter(status='cerrada').aggregate(total=Sum('labor_cost'))['total'] or Decimal('0'),
        'parts_cost':sum((v.quantity*v.unit_cost for v in m.StockMovement.objects.filter(organization_id=request.user.organization_id,kind='salida',work_order__status='cerrada')),Decimal('0')),
        'fuel_cost':fuel.aggregate(total=Sum('cost'))['total'] or Decimal('0'),
        'liters':fuel.aggregate(total=Sum('liters'))['total'] or Decimal('0')})


@login_required
def settings_view(request):
    if request.user.role != 'administrador' or not request.user.organization_id: raise PermissionDenied
    from .modules.administracion.forms import OrganizationSettingsForm
    cls = OrganizationSettingsForm
    form = cls(request.POST or None,instance=request.user.organization)
    form.fields['name'].widget.attrs['class'] = 'form-control'
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            obj = form.save()
            audit(request.user,'Configuración actualizada',obj,{'nombre':obj.name})
        messages.success(request,'Configuración guardada.')
        return redirect('settings')
    return render(request,'cmms/settings.html',{'page_title':'Configuración SETRAM','form':form,'role_groups':form.role_groups,'extended_workspace':True})


def api_auth(view):
    @wraps(view)
    def wrapped(request,*args,**kwargs):
        if not request.user.is_authenticated: return JsonResponse({'error':'Autenticación requerida'},status=401)
        try: return view(request,*args,**kwargs)
        except PermissionDenied: return JsonResponse({'error':'Operación no permitida'},status=403)
        except Http404: return JsonResponse({'error':'Registro no encontrado'},status=404)
    return wrapped


@api_auth
@require_GET
def api_records(request,key,pk=None):
    module = access(request,key)
    qs = queryset(request,module)
    if pk:
        objects = [get_object_or_404(qs,pk=pk)]
        count, pages, number = 1,1,1
    else:
        page = Paginator(qs,25).get_page(request.GET.get('pagina'))
        objects, count, pages, number = page.object_list,page.paginator.count,page.paginator.num_pages,page.number
    def raw_value(obj,name):
        value=getattr(obj,name,None)
        if isinstance(value,m.models.Model): return value.pk
        if isinstance(value,(date,)): return value.isoformat()
        if isinstance(value,Decimal): return str(value)
        return value
    results = [{'id':obj.pk,**{name:raw_value(obj,name) for name,_ in module.columns},
                'etiquetas':{name:display(obj,name) for name,_ in module.columns}} for obj in objects]
    return JsonResponse({'modulo':key,'total':count,'pagina':number,'paginas':pages,'resultados':results})


@api_auth
@require_POST
def api_order_state(request,pk):
    access(request,'ordenes')
    get_object_or_404(scoped(REGISTRY['ordenes'],request.user),pk=pk)
    try:
        data = json.loads(request.body)
        if not isinstance(data,dict): raise ValueError
        order = transition(request.user,pk,data.get('estado'))
        return JsonResponse({'id':order.pk,'estado':order.status})
    except (ValueError,TypeError): return JsonResponse({'error':'JSON inválido'},status=400)
    except ValidationError as exc: return JsonResponse({'error':exc.messages},status=422)


def health(request):
    from django.db import connection
    try:
        with connection.cursor() as cursor: cursor.execute('SELECT 1')
        return JsonResponse({'sistema':'SETRAM CMMS','estado':'disponible'})
    except Exception:
        return JsonResponse({'estado':'base de datos no disponible'},status=503)
