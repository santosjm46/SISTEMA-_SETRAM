from django.db import transaction
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from cmms import models as m


@transaction.atomic
def assess(bus,user):
    if user.role not in ('administrador','supervisor'): raise PermissionDenied
    bus=m.Bus.objects.select_for_update().get(pk=bus.pk,organization_id=user.organization_id)
    now=timezone.now()
    reading=bus.telemetryreading_set.order_by('-measured_at').first()
    inspections=bus.inspection_set.count()
    plans=list(bus.preventiveplan_set.filter(active=True))
    orders=bus.workorder_set.exclude(status='cerrada')
    fresh=bool(reading and now-reading.measured_at<=timezone.timedelta(hours=24))
    coverage={'inspecciones':inspections,'planes_activos':len(plans),'ordenes_abiertas':orders.count(),
              'telemetria_reciente':fresh,'ultima_lectura':reading.measured_at.isoformat() if reading else None}
    signals=[]
    def add(title,points,source): signals.append({'senal':title,'puntos':points,'fuente':source})
    if bus.status=='inmovilizado': add('Bus inmovilizado',70,'Estado operativo de flota')
    if bus.inspection_set.filter(result='critico',resolved=False).exists(): add('Defecto crítico sin resolver',40,'Inspecciones')
    if orders.filter(priority='critica').exists(): add('OT crítica abierta',20,'Órdenes de trabajo')
    elif orders.exists(): add('Mantenimiento correctivo pendiente',10,'Órdenes de trabajo')
    if any(plan.overdue for plan in plans): add('Preventivo vencido por fecha, kilometraje u horas',15,'Planes preventivos')
    if bus.safetyincident_set.filter(severity='critica').exclude(status='resuelto').exists(): add('Incidente crítico activo',25,'Seguridad')
    if bus.recall_set.exclude(status='atendido').exists(): add('Campaña de fabricante pendiente',10,'Retiros')
    if fresh and reading.fault_code: add('Código de falla reportado por dispositivo',15,'Telemetría: '+reading.fault_code)
    if fresh and reading.temperature is not None and reading.temperature>=105: add('Refrigerante ≥105 °C: revisar según especificación del bus',20,'Telemetría')
    enough=bool(inspections or plans or orders.exists() or fresh or signals)
    score=min(100,sum(item['puntos'] for item in signals)) if enough else None
    level='sin_datos' if score is None else 'critico' if score>=70 else 'alto' if score>=40 else 'medio' if score>=20 else 'bajo'
    result=m.PredictiveAssessment.objects.create(organization=bus.organization,bus=bus,score=score,level=level,signals=signals,coverage=coverage)
    if level in ('alto','critico') and not m.PredictionRecommendation.objects.filter(bus=bus,status__in=('pendiente','ot_creada')).exclude(work_order__status='cerrada').exists():
        m.PredictionRecommendation.objects.create(organization=bus.organization,bus=bus,assessment=result,
            title='Revisar señales técnicas de '+bus.code,explanation='\n'.join(s['senal']+' · '+s['fuente'] for s in signals))
    from cmms.services import audit
    audit(user,'Evaluación predictiva',result,{'indice':score,'nivel':level,'algoritmo':result.algorithm})
    return result
