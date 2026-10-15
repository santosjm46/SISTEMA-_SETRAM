import calendar
from datetime import date,timedelta
from django.shortcuts import render
from django.utils import timezone
from django.utils.dateparse import parse_date
from cmms.registry import REGISTRY,scoped,buses_for
from cmms.module import enabled
from django.core.exceptions import PermissionDenied
from django.db import models

def view(request):
    user=request.user
    if not user.organization_id:raise PermissionDenied
    today=timezone.localdate()
    try:
        anchor=parse_date(request.GET.get('fecha','')) or date(int(request.GET.get('anio',today.year)),int(request.GET.get('mes',today.month)),1)
        if not 2020<=anchor.year<=2100:raise ValueError()
    except (ValueError,TypeError):anchor=today
    mode=request.GET.get('vista','mes')
    if mode not in ('dia','semana','mes','anio','agenda'):mode='mes'
    if mode=='dia':first=last=anchor
    elif mode=='semana':first=anchor-timedelta(days=anchor.weekday());last=first+timedelta(days=6)
    elif mode=='anio':first=date(anchor.year,1,1);last=date(anchor.year,12,31)
    elif mode=='agenda':first=today;last=today+timedelta(days=90)
    else:first=anchor.replace(day=1);last=date(anchor.year,anchor.month,calendar.monthrange(anchor.year,anchor.month)[1])
    sources=[('preventivos','next_date','Preventivo','teal'),('ordenes','due_date','OT','amber'),('documentos','expiry','Documento','rose'),('cumplimiento','due_date','Requisito','rose'),('retiros','due_date','Campaña','amber'),('recordatorios','next_due','Recordatorio','teal'),('inspecciones','date','Inspección','blue'),('recorridos','started_at','Recorrido','blue'),('buses','registration_expiry','Registro de bus','rose'),('buses','insurance_expiry','Seguro de bus','rose')]
    events={};agenda=[];selected=request.GET.get('tipo','')
    for key,field,title,color in sources:
        module=REGISTRY[key]
        if user.role not in module.read or not enabled(user,key) or selected and key!=selected:continue
        qs=scoped(module,user)
        fields={f.name:f for f in module.model._meta.fields}
        if request.GET.get('bus','').isdigit():
            if key=='buses':qs=qs.filter(pk=request.GET['bus'])
            elif 'bus' in fields:qs=qs.filter(bus_id=request.GET['bus'])
        suffix='__date' if isinstance(fields[field],models.DateTimeField) else ''
        qs=qs.filter(**{field+suffix+'__gte':first,field+suffix+'__lte':last})
        if 'bus' in fields:qs=qs.select_related('bus')
        for obj in qs:
            value=getattr(obj,field)
            day=timezone.localtime(value).date() if isinstance(fields[field],models.DateTimeField) else value
            item={'date':day,'label':title+' · '+str(obj),'key':key,'pk':obj.pk,'color':color}
            events.setdefault(day,[]).append(item);agenda.append(item)
    agenda.sort(key=lambda row:(row['date'],row['label']))
    weeks=[]
    if mode=='mes':weeks=[[{'date':day,'in_month':day.month==anchor.month,'events':events.get(day,[])} for day in week] for week in calendar.Calendar(firstweekday=0).monthdatescalendar(anchor.year,anchor.month)]
    if mode=='semana':weeks=[[{'date':first+timedelta(days=i),'in_month':True,'events':events.get(first+timedelta(days=i),[])} for i in range(7)]]
    months=[{'number':month,'name':date(anchor.year,month,1).strftime('%m'),'count':sum(row['date'].month==month for row in agenda)} for month in range(1,13)]
    return render(request,'cmms/calendar.html',{'page_title':'Calendario de flota','extended_workspace':True,'weeks':weeks,'first':first,'last':last,'anchor':anchor,'mode':mode,
        'agenda':agenda,'months':months,'previous':first-timedelta(days=1),'following':last+timedelta(days=1),'today':today,
        'sources':list(dict((key,title) for key,_,title,_ in sources).items()),'buses':buses_for(user)})
