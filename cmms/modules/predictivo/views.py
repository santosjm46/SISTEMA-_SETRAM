from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from cmms import models as m
from cmms.registry import MANAGERS,buses_for,scoped,REGISTRY
from cmms.views import access
from cmms.modules.ui import page
from .services import assess

@login_required
def index(request):
    access(request,'predictivo')
    buses=buses_for(request.user)
    if request.method=='POST':
        if request.user.role not in MANAGERS: raise PermissionDenied
        for bus in buses: assess(bus,request.user)
        messages.success(request,'Evaluaciones calculadas y guardadas con sus fuentes.')
        return redirect('predictive:index')
    latest=[bus.predictiveassessment_set.order_by('-created_at').first() for bus in buses]
    latest=[row for row in latest if row]
    scored=[row.score for row in latest if row.score is not None]
    tab=request.GET.get('tab','overview')
    if tab not in ('overview','analyze','predictions','roi','actions'):tab='overview'
    history=list(scoped(REGISTRY['predictivo'],request.user).select_related('bus')[:100])
    groups={}
    for row in history:
        day=row.created_at.strftime('%d/%m');groups.setdefault(day,[])
        if row.score is not None:groups[day].append(row.score)
    trend=[{'label':day,'value':round(sum(values)/len(values),1)} for day,values in reversed(list(groups.items())) if values]
    distribution=[{'label':label,'value':sum(row.level==value for row in latest)} for value,label in m.PredictiveAssessment._meta.get_field('level').choices]
    recs=scoped(REGISTRY['recomendaciones'],request.user).select_related('bus','assessment','work_order')
    economics=[]
    if request.user.role in MANAGERS:
        for rec in recs:
            estimate=round(100*(rec.potential_savings-rec.estimated_cost)/rec.estimated_cost,1) if rec.estimated_cost and rec.potential_savings is not None else None
            economics.append({'record':rec,'roi':estimate,'actual_cost':rec.work_order.total_cost if rec.work_order_id and rec.work_order.status=='cerrada' else None})
    return page(request,'predictivo','cmms/modules/predictive.html',assessments=latest,
        history=history,tab=tab,trend=trend,distribution=distribution,economics=economics,action_records=recs.filter(work_order__isnull=False),
        recommendations=scoped(REGISTRY['recomendaciones'],request.user).select_related('bus','assessment').filter(status='pendiente'),
        stats=[{'label':'Buses evaluados','value':len(latest)},{'label':'Índice medio de riesgo','value':round(sum(scored)/len(scored),1) if scored else 'Sin datos'},
               {'label':'Riesgo alto / crítico','value':sum(row.level in ('alto','critico') for row in latest)},
               {'label':'Sin datos suficientes','value':sum(row.score is None for row in latest)}])
