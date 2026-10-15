from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum
from cmms import models as m
from cmms.views import access
from cmms.registry import REGISTRY,buses_for,scoped
from cmms.modules.ui import page

@login_required
def start(request):
    access(request,'comenzar')
    org=request.user.organization
    steps=[{'title':'Registrar buses','key':'buses','count':buses_for(request.user).count()},
           {'title':'Asignar personal y roles','key':'personal','count':m.User.objects.filter(organization=org,is_active=True).count()},
           {'title':'Definir listas de verificación','key':'plantillas','count':m.Checklist.objects.filter(organization=org,active=True).count()},
           {'title':'Programar mantenimiento','key':'preventivos','count':scoped(REGISTRY['preventivos'],request.user).count()},
           {'title':'Registrar dispositivos y lecturas','key':'telemetria','count':scoped(REGISTRY['telemetria'],request.user).count()}]
    return page(request,'comenzar','cmms/modules/start.html',steps=[s for s in steps if request.user.role in REGISTRY[s['key']].read])

@login_required
def executive(request):
    access(request,'ejecutivo')
    from .dashboard import period
    start,_,period_label=period(request.GET)
    orders=scoped(REGISTRY['ordenes'],request.user)
    closed=orders.filter(status='cerrada',completed_at__date__gte=start)
    cycles=[(row.completed_at-row.created_at).total_seconds()/86400 for row in closed if row.completed_at]
    buses=buses_for(request.user)
    fuel=scoped(REGISTRY['combustible'],request.user).filter(date__gte=start)
    parts=m.StockMovement.objects.filter(organization=request.user.organization,kind='salida',work_order__in=closed)
    cost=sum((row.total_cost for row in closed),Decimal(0))
    repair_times=[(row.completed_at-row.started_at).total_seconds()/3600 for row in closed if row.started_at and row.completed_at]
    plans=list(scoped(REGISTRY['preventivos'],request.user).filter(active=True).select_related('bus'))
    pm=round(100*sum(not plan.overdue for plan in plans)/len(plans)) if plans else None
    failure_modes=[{'label':label,'value':orders.filter(created_at__date__gte=start,failure_category=value).count()} for value,label in m.WorkOrder._meta.get_field('failure_category').choices]
    return page(request,'ejecutivo','cmms/modules/executive.html',closed_orders=closed[:20],
        stats=[{'label':'OT cerradas del período','value':closed.count()},{'label':'Ciclo medio · días','value':round(sum(cycles)/len(cycles),1) if cycles else 'Sin datos'},
               {'label':'Costo de OT cerradas (Bs)','value':f'{cost:.2f}'},{'label':'Combustible del período (Bs)','value':str(fuel.aggregate(total=Sum('cost'))['total'] or 0)},
               {'label':'Reparación media · horas','value':round(sum(repair_times)/len(repair_times),1) if repair_times else 'Sin datos'},
               {'label':'Preventivos al día','value':str(pm)+'%' if pm is not None else 'Sin datos'}],
        status_counts=[{'label':label,'count':orders.filter(status=value).count()} for value,label in m.WorkOrder._meta.get_field('status').choices],
        total_buses=buses.count(),available=buses.filter(status='operativo').count(),period=start,failure_modes=failure_modes,period_label=period_label)

@login_required
def pulse(request):
    access(request,'pulso_flota')
    rows=[]
    for bus in buses_for(request.user):
        plans=list(bus.preventiveplan_set.filter(active=True))
        assessment=bus.predictiveassessment_set.first()
        rows.append({'bus':bus,'overdue':sum(plan.overdue for plan in plans),'orders':bus.workorder_set.exclude(status='cerrada').count(),
                     'critical':bus.inspection_set.filter(result='critico',resolved=False).count(),'assessment':assessment,
                     'age':max(0,timezone.localdate().year-bus.year),'remaining':max(0,bus.design_life_years-(timezone.localdate().year-bus.year)) if bus.design_life_years else None})
    level=request.GET.get('riesgo')
    if level:rows=[row for row in rows if row['assessment'] and row['assessment'].level==level]
    rows.sort(key=lambda row:(-(row['assessment'].score or 0) if row['assessment'] else 0,-row['age']))
    return page(request,'pulso_flota','cmms/modules/pulse.html',rows=rows,
        stats=[{'label':'Buses visibles','value':len(rows)},{'label':'Inmovilizados','value':sum(row['bus'].status=='inmovilizado' for row in rows)},
               {'label':'Planes vencidos','value':sum(row['overdue'] for row in rows)},{'label':'OT abiertas','value':sum(row['orders'] for row in rows)}])
