from decimal import Decimal
from datetime import date
from django.db.models import Sum,Count,F,Avg
from django.utils import timezone
from cmms.registry import REGISTRY,scoped,buses_for
from cmms.module import enabled,MANAGERS
from cmms import models as m

TABS=[('general','Vista general'),('mantenimiento','Mantenimiento'),('flota','Buses'),('combustible','Combustible y costos'),('seguridad','Seguridad'),('inventario','Inventario'),('departamentos','Departamentos'),('documentos','Documentos')]
WIDGETS=[('flota','Estado de flota'),('ordenes','Órdenes de trabajo'),('inspecciones','Inspecciones'),('alertas','Alertas'),('accesos','Accesos rápidos')]

def period(params):
    today=timezone.localdate(); selected=params.get('periodo','mes')
    start=today-timezone.timedelta(days=today.weekday()) if selected=='semana' else date(today.year,((today.month-1)//3)*3+1,1) if selected=='trimestre' else today.replace(day=1)
    return start,today,{'semana':'Esta semana','trimestre':'Este trimestre'}.get(selected,'Este mes')

def kpis(user,start=None):
    buses=buses_for(user); inspections=scoped(REGISTRY['inspecciones'],user).filter(date__date__gte=start or timezone.localdate().replace(day=1))
    total=buses.count(); available=buses.filter(status='operativo').count(); done=inspections.count(); passed=inspections.filter(result='aprobado').count()
    return {'total_buses':total,'available_buses':available,'availability':round(100*available/total) if total else None,
        'inspection_count':done,'passed':passed,'approval':round(100*passed/done) if done else None}

def context(request):
    user=request.user; start,end,label=period(request.GET)
    tab=request.GET.get('tab','general'); tab=tab if tab in dict(TABS) else 'general'
    def allowed(key):return user.role in REGISTRY[key].read and enabled(user,key)
    def data(key):return scoped(REGISTRY[key],user) if allowed(key) else REGISTRY[key].model.objects.none()
    orders=data('ordenes'); inspections=data('inspecciones'); plans=list(data('preventivos').filter(active=True).select_related('bus'))
    overdue=[plan for plan in plans if plan.overdue]
    low=data('repuestos').filter(minimum__gt=0,quantity__lte=F('minimum')) if user.role in MANAGERS else m.Part.objects.none()
    stats=[]
    def add(name,value,key=None):
        if not key or allowed(key):stats.append({'label':name,'value':value,'key':key})
    if tab=='mantenimiento':
        add('OT abiertas',orders.exclude(status='cerrada').count(),'ordenes');add('OT cerradas del período',orders.filter(status='cerrada',completed_at__date__gte=start).count(),'ordenes');add('Preventivos vencidos',len(overdue),'preventivos');add('Solicitudes pendientes',data('solicitudes').filter(status__in=('pendiente','en_revision')).count(),'solicitudes')
    elif tab=='flota':
        buses=buses_for(user)
        for value,title in m.Bus._meta.get_field('status').choices:add(title,buses.filter(status=value).count(),'buses')
    elif tab=='combustible':
        fuel=data('combustible').filter(date__gte=start,date__lte=end);total=fuel.aggregate(v=Sum('cost'))['v'] or 0;liters=fuel.aggregate(v=Sum('liters'))['v'] or 0
        add('Combustible del período · Bs',total,'combustible');add('Volumen · litros',liters,'combustible');add('Costo medio · Bs/L',round(total/liters,2) if liters else 'Sin datos','combustible');add('Pendientes de conciliar',fuel.filter(verification='pendiente').count(),'combustible')
    elif tab=='seguridad':
        add('Inspecciones críticas abiertas',inspections.filter(result='critico',resolved=False).count(),'inspecciones');add('Incidentes abiertos',data('incidentes').exclude(status='resuelto').count(),'incidentes');add('Requisitos vencidos',data('cumplimiento').exclude(status__in=('completado','no_aplica')).filter(due_date__lt=end).count(),'cumplimiento');add('Campañas pendientes',data('retiros').exclude(status='atendido').count(),'retiros')
    elif tab=='inventario':
        parts=data('repuestos');add('Repuestos',parts.count(),'repuestos');add('Bajo mínimo',low.count(),'repuestos');add('Valor referencial · Bs',sum((r.quantity*r.unit_cost for r in parts),Decimal(0)),'repuestos');add('Compras pendientes',data('compras').exclude(status='recibido').count(),'compras')
    elif tab=='departamentos':
        add('Patios activos',data('departamentos').filter(active=True).count(),'departamentos');add('Turnos activos',data('turnos_patio').filter(active=True).count(),'turnos_patio')
    elif tab=='documentos':
        docs=data('documentos');add('Documentos visibles',docs.count(),'documentos');add('Vencidos',docs.filter(expiry__lt=end).count(),'documentos');add('Vencen en 30 días',docs.filter(expiry__range=(end,end+timezone.timedelta(days=30))).count(),'documentos');add('Análisis pendientes de revisión',data('auditor_documental').filter(state='revisar').count(),'auditor_documental')
    requirements={'mantenimiento':'ordenes','flota':'buses','combustible':'combustible','seguridad':'inspecciones','inventario':'repuestos','departamentos':'departamentos','documentos':'documentos'}
    tabs=[(key,title) for key,title in TABS if key=='general' or allowed(requirements[key])]
    result={'page_title':'Panel de control','extended_workspace':True,'dashboard_tabs':tabs,'dashboard_tab':tab,'area_stats':stats,
        'period_label':label,'period_start':start,'period_end':end,'period_value':request.GET.get('periodo','mes'),'widget_choices':[{'key':key,'title':title,'selected':key in (user.dashboard_widgets or dict(WIDGETS))} for key,title in WIDGETS],
        'widgets':user.dashboard_widgets or list(dict(WIDGETS)),
        'open_orders':orders.exclude(status='cerrada').count(),'closed_orders':orders.filter(status='cerrada').count(),
        'overdue_plans':overdue[:5],'overdue_count':len(overdue),'plan_count':len(plans),'low_stock':low[:5],'low_stock_count':low.count(),
        'recent_orders':orders.select_related('bus','assigned_to')[:5],'recent_inspections':inspections.filter(date__date__gte=start).select_related('bus')[:5],
        'today':end,'bus_statuses':[(title,buses_for(user).filter(status=value).count()) for value,title in m.Bus._meta.get_field('status').choices]}
    result.update(kpis(user,start));return result
