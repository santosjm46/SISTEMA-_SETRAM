"""Extensiones transaccionales del núcleo por dominio."""
from django.core.exceptions import ValidationError
from cmms import models as m
from django.utils import timezone


def before_save(obj,user):
    if isinstance(obj,m.PurchaseLine): m.PurchaseOrder.objects.select_for_update().get(pk=obj.purchase_id,organization_id=user.organization_id)
    if isinstance(obj,m.WorkOrder) and not obj.pk and not obj.reported_by_id: obj.reported_by=user
    if isinstance(obj,m.WorkOrderComment):
        obj.author=user
        m.WorkOrder.objects.select_for_update().get(pk=obj.work_order_id,organization_id=user.organization_id)
    if isinstance(obj,m.ScheduledReport): obj.created_by=user
    if isinstance(obj,m.BusPhoto):
        obj.uploaded_by=user
        m.Bus.objects.select_for_update().get(pk=obj.bus_id,organization_id=user.organization_id)
    if isinstance(obj,m.WorkOrderTask):
        order=m.WorkOrder.objects.select_for_update().get(pk=obj.work_order_id,organization_id=user.organization_id)
        if order.status=='cerrada': raise ValidationError('La OT está cerrada.')
        if user.role=='tecnico' and order.assigned_to_id!=user.pk: raise ValidationError('La OT no está asignada a tu usuario.')
        if obj.status!='pendiente':
            obj.completed_by=user
            obj.completed_at=timezone.now()
        else:
            obj.completed_by=None
            obj.completed_at=None
    if isinstance(obj,(m.SafetyIncident,m.CameraObservation)): obj.reported_by=user
    if isinstance(obj,m.ShiftLog):
        m.User.objects.select_for_update().get(pk=obj.driver_id,organization_id=user.organization_id)
    if isinstance(obj,m.TripLog):
        bus=m.Bus.objects.select_for_update().get(pk=obj.bus_id,organization_id=user.organization_id)
        if obj.status=='en_ruta' and m.TripLog.objects.filter(bus=bus,status='en_ruta').exclude(pk=obj.pk).exists(): raise ValidationError('El bus ya tiene un recorrido en curso.')
        if obj.status=='completado' and obj.end_km is not None and obj.end_km>bus.odometer:
            bus.odometer=obj.end_km
            bus.save(update_fields=['odometer','updated_at'])
    if isinstance(obj,m.TelemetryReading):
        bus=m.Bus.objects.select_for_update().get(pk=obj.bus_id,organization_id=user.organization_id)
        if obj.odometer>bus.odometer:
            bus.odometer=obj.odometer
            bus.save(update_fields=['odometer','updated_at'])
        if obj.engine_hours is not None and (bus.engine_hours is None or obj.engine_hours>bus.engine_hours):
            bus.engine_hours=obj.engine_hours
            bus.save(update_fields=['engine_hours','updated_at'])
    if isinstance(obj,m.SafetyIncident) and obj.severity=='critica':
        bus=m.Bus.objects.select_for_update().get(pk=obj.bus_id,organization_id=user.organization_id)
        bus.status='inmovilizado'
        bus.save(update_fields=['status','updated_at'])


def after_save(obj,user,creating):
    if isinstance(obj,m.WorkOrder) and creating:
        if obj.program_id:
            templates=list(obj.program.task_templates.filter(active=True,organization=obj.organization))
            for template in templates:
                m.WorkOrderTask.objects.create(organization=obj.organization,work_order=obj,template=template,title=template.name)
            if not templates:
                for title in obj.program.tasks.splitlines():
                    if title.strip(): m.WorkOrderTask.objects.create(organization=obj.organization,work_order=obj,title=title.strip()[:160])
    if isinstance(obj,m.SafetyIncident) and creating and obj.severity=='critica':
        order=m.WorkOrder.objects.create(organization=obj.organization,bus=obj.bus,title='Incidente crítico: '+obj.title[:130],description=obj.description,priority='critica')
        obj.work_order=order
        obj.status='ot_creada'
        obj.save(update_fields=['work_order','status'])
        from cmms.services import audit
        audit(user,'OT generada por incidente',order)
    if isinstance(obj,(m.WorkOrder,m.MaintenanceRequest,m.Inspection,m.SafetyIncident)):
        from cmms.modules.inspecciones.services import notify
        topic='ordenes' if isinstance(obj,m.WorkOrder) else 'solicitudes' if isinstance(obj,m.MaintenanceRequest) else 'inspecciones'
        recipients=list(m.User.objects.filter(organization=obj.organization,is_active=True,role__in=('administrador','supervisor')))
        if isinstance(obj,m.WorkOrder) and obj.assigned_to_id:recipients.append(obj.assigned_to)
        for recipient in {person.pk:person for person in recipients}.values():
            if recipient.pk!=user.pk:
                key='ordenes' if isinstance(obj,m.WorkOrder) else 'solicitudes' if isinstance(obj,m.MaintenanceRequest) else 'inspecciones' if isinstance(obj,m.Inspection) else 'incidentes'
                notify(recipient,topic,'Nuevo registro' if creating else 'Registro actualizado',str(obj),f'/modulos/{key}/{obj.pk}/')


def on_order_closed(order):
    m.SafetyIncident.objects.filter(work_order=order).update(status='resuelto',resolution=order.resolution)
    m.Recall.objects.filter(work_order=order).update(status='atendido',resolution=order.resolution)


def critical_holds(bus):
    return bus.safetyincident_set.filter(severity='critica').exclude(status='resuelto').exists()
