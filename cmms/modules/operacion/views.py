from django.contrib.auth.decorators import login_required
from cmms import models as m
from cmms.registry import REGISTRY,scoped
from cmms.views import access
from cmms.modules.ui import page

@login_required
def hos(request):
    access(request,'jornadas')
    logs=scoped(REGISTRY['jornadas'],request.user).select_related('bus','driver')
    policy=m.OperatingPolicy.objects.filter(organization=request.user.organization,active=True).first()
    rows=[{'obj':row,'warning':bool(policy and row.driving_hours>policy.daily_driving_hours)} for row in logs[:50]]
    return page(request,'jornadas','cmms/modules/hos.html',rows=rows,policy=policy,can_create=request.user.role in REGISTRY['jornadas'].create,
        stats=[{'label':'Jornadas registradas','value':logs.count()},{'label':'Horas netas · historial','value':round(sum(row.driving_hours for row in logs),2)},
               {'label':'Umbral por jornada','value':str(policy.daily_driving_hours)+' h' if policy else 'Sin configurar'},
               {'label':'Alertas · últimas 50','value':sum(item['warning'] for item in rows) if policy else 'Sin configurar'}])
