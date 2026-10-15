from django.db import transaction
from django.utils import timezone
from cmms import models as m

TOPICS=[('ordenes','Órdenes de trabajo'),('solicitudes','Solicitudes'),('inspecciones','Inspecciones y seguridad'),('cumplimiento','Cumplimiento y campañas'),('combustible','Combustible'),('operacion','Jornadas y recorridos'),('sistema','Equipo e informes'),('kpi','Indicadores')]

def notify(user,kind,title,body,link='',dedupe=''):
    from cmms.module import enabled
    org=user.organization
    if not user.is_active or not org or not org.notifications_enabled or not enabled(user,'notificaciones'):return None
    matrix=org.notification_matrix or {}
    if not matrix.get(user.role,{}).get(kind,True):return None
    if link and (not link.startswith('/') or link.startswith('//')):link=''
    defaults={'kind':kind,'title':title[:180],'body':body,'link':link}
    if dedupe:
        obj,_=m.Notification.objects.get_or_create(organization=org,user=user,dedupe_key=dedupe,defaults=defaults);return obj
    return m.Notification.objects.create(organization=org,user=user,**defaults)

def send_kpi_alerts(org):
    if not org.kpi_alerts_enabled:return 0
    from cmms.modules.portal.dashboard import kpis
    members=list(m.User.objects.filter(organization=org,is_active=True,role__in=('administrador','supervisor')))
    if not members:return 0
    snapshot=kpis(members[0]);count=0;today=timezone.localdate()
    for field,threshold,label in [('availability',org.minimum_availability,'Disponibilidad de flota'),('approval',org.minimum_inspection_approval,'Aprobación de inspecciones del mes')]:
        value=snapshot[field]
        if value is None or value>=threshold:continue
        for member in members:
            key=f'kpi:{field}:{today}'; existed=m.Notification.objects.filter(user=member,dedupe_key=key).exists()
            obj=notify(member,'kpi',label,f'{value}% registrado; umbral interno {threshold}%. Datos calculados con la flota visible y las inspecciones del mes.','/',key)
            count+=int(bool(obj) and not existed)
    return count


@transaction.atomic
def dispatch_reminders(organization):
    now=timezone.now()
    count=0
    reminders=m.InspectionReminder.objects.select_for_update().filter(organization=organization,active=True,next_due__lte=now,assigned_to__is_active=True)[:200]
    for reminder in reminders:
        org=reminder.organization
        if not org.notifications_enabled or not (org.notification_matrix or {}).get(reminder.assigned_to.role,{}).get('inspecciones',True):continue
        _,created=m.Notification.objects.get_or_create(organization=organization,reminder=reminder,occurrence=reminder.next_due,
            defaults={'user':reminder.assigned_to,'title':reminder.title,'body':f'Inspección pendiente del bus {reminder.bus.code}. Fecha programada: {timezone.localtime(reminder.next_due):%d/%m/%Y %H:%M}.'})
        count+=int(created)
        elapsed=(now-reminder.next_due).days//reminder.interval_days+1
        reminder.next_due+=timezone.timedelta(days=reminder.interval_days*elapsed)
        reminder.save(update_fields=['next_due','updated_at'])
    return count
