from datetime import timedelta
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from . import models as m


def audit(user, action, obj, changes=None):
    m.AuditEvent.objects.create(organization_id=user.organization_id,actor=user,action=action,
                              entity=obj._meta.label,object_id=str(obj.pk),changes=changes or {})


@transaction.atomic
def save_record(form, user):
    obj = form.save(commit=False)
    obj.organization_id = user.organization_id
    creating = obj.pk is None
    before = {}
    if not creating:
        previous = type(obj).objects.select_for_update().get(pk=obj.pk,organization_id=user.organization_id)
        before = {f.name:str(getattr(previous,f.attname)) for f in previous._meta.fields if f.name in form.fields and f.name not in ('password','file','stream_url','digest')}
        # No sobrescribir existencias, estados u otros campos que no se editan
        # si cambiaron mientras el formulario estaba abierto.
        for field in obj._meta.fields:
            if field.name not in form.fields and field.name not in ('id','organization','created_at','updated_at','password'):
                setattr(obj,field.attname,getattr(previous,field.attname))
        if isinstance(obj,m.WorkOrder) and previous.status == 'cerrada':
            raise ValidationError('Una OT cerrada no admite edición.')
        if isinstance(obj,m.WorkOrderTask) and (previous.work_order.status=='cerrada' or obj.work_order_id!=previous.work_order_id):
            raise ValidationError('La tarea pertenece a su OT original; una OT cerrada no admite cambios.')
        if isinstance(obj,m.PurchaseLine) and (previous.purchase_id!=obj.purchase_id or previous.purchase.status!='pedido'):
            raise ValidationError('La línea pertenece a su compra original y no cambia después de iniciar la recepción.')
        if isinstance(obj,m.Checklist) and previous.items != obj.items:
            obj.version = previous.version + 1
    if isinstance(obj,m.User):
        password = form.cleaned_data.get('password')
        if password:
            obj.set_password(password)
        obj.is_staff = False
        obj.is_superuser = False
    if isinstance(obj,m.MaintenanceRequest): obj.reported_by = user
    if isinstance(obj,m.FuelEntry): obj.driver = user
    if isinstance(obj,m.StockMovement):
        obj.actor = user
        part = m.Part.objects.select_for_update().get(pk=obj.part_id,organization_id=user.organization_id)
        if obj.work_order_id:
            order = m.WorkOrder.objects.select_for_update().get(pk=obj.work_order_id,organization_id=user.organization_id)
            if order.status == 'cerrada':
                raise ValidationError('La OT ya fue cerrada; no admite movimientos.')
        difference = obj.quantity if obj.kind == 'entrada' else -obj.quantity
        if part.quantity + difference < 0:
            raise ValidationError('Existencias insuficientes. No se guardó el movimiento.')
        part.quantity += difference
        part.save(update_fields=['quantity','updated_at'])
    if isinstance(obj,(m.Inspection,m.FuelEntry,m.Bus)):
        bus = m.Bus.objects.select_for_update().get(pk=obj.pk if isinstance(obj,m.Bus) else obj.bus_id,organization_id=user.organization_id) if not isinstance(obj,m.Bus) or obj.pk else None
        if bus and obj.odometer < bus.odometer:
            raise ValidationError('La lectura del odómetro quedó desactualizada; revisa el bus.')
        if bus and not isinstance(obj,m.Bus):
            bus.odometer = obj.odometer
            if isinstance(obj,m.Inspection) and obj.result == 'critico': bus.status = 'inmovilizado'
            bus.save(update_fields=['odometer','status','updated_at'])
    from .modules.hooks import before_save,after_save
    before_save(obj,user)
    obj.full_clean(exclude=['password'] if isinstance(obj,m.User) else None)
    obj.save()
    form.save_m2m()
    after_save(obj,user,creating)
    if isinstance(obj,m.WorkOrder) and creating:
        for template in form.cleaned_data.get('task_templates',[]):
            if not obj.workordertask_set.filter(template=template).exists():
                m.WorkOrderTask.objects.create(organization=obj.organization,work_order=obj,template=template,title=template.name)
        for title in (form.cleaned_data.get('additional_tasks') or '').splitlines():
            if title.strip(): m.WorkOrderTask.objects.create(organization=obj.organization,work_order=obj,title=title.strip()[:160])
    if isinstance(obj,m.Inspection) and obj.result != 'aprobado':
        order = m.WorkOrder.objects.create(organization_id=user.organization_id,bus=obj.bus,
            title=f'Hallazgos de inspección INS-{obj.pk}',description=obj.findings,
            priority='critica' if obj.result == 'critico' else 'media')
        obj.work_order = order
        obj.save(update_fields=['work_order'])
        audit(user,'OT generada por inspección',order)
    after = {name:str(getattr(obj,name,'')) for name in form.fields if name not in ('password','file','stream_url','digest') and not name.startswith('item_') and name != 'confirm'}
    audit(user,'Creación' if creating else 'Edición',obj,{'antes':before,'despues':after})
    return obj


@transaction.atomic
def transition(user, order_id, target):
    order = m.WorkOrder.objects.select_for_update().get(pk=order_id,organization_id=user.organization_id)
    if user.role not in ('administrador','supervisor') and not (user.role == 'tecnico' and order.assigned_to_id == user.pk):
        raise PermissionDenied
    allowed = {'abierta':('en_progreso',),'en_progreso':('revision',),'revision':('en_progreso','cerrada')}
    if target not in allowed.get(order.status,()):
        raise ValidationError('La transición solicitada no corresponde al estado actual.')
    if target == 'en_progreso' and not order.assigned_to_id:
        raise ValidationError('Asigna un responsable antes de iniciar la OT.')
    if target in ('revision','cerrada') and not order.resolution.strip():
        raise ValidationError('Registra el trabajo realizado antes de enviar a revisión.')
    if target in ('revision','cerrada') and order.workordertask_set.filter(status='pendiente').exists():
        raise ValidationError('Completa o justifica las tareas pendientes de la OT.')
    if target == 'cerrada' and user.role not in ('administrador','supervisor'):
        raise PermissionDenied
    prior = order.status
    order.status = target
    if target=='en_progreso' and not order.started_at: order.started_at=timezone.now()
    if target == 'cerrada':
        order.completed_at = timezone.now()
        # El cierre mantiene el bloqueo de bus y plan en la misma transacción.
        bus = m.Bus.objects.select_for_update().get(pk=order.bus_id)
        order.save(update_fields=['status','completed_at','updated_at'])
        m.Inspection.objects.filter(work_order=order).update(resolved=True)
        from .modules.hooks import on_order_closed,critical_holds
        on_order_closed(order)
        if bus.status == 'inmovilizado' and not critical_holds(bus) and not bus.inspection_set.filter(result='critico',resolved=False).exists() and not bus.workorder_set.filter(priority='critica').exclude(status='cerrada').exists():
            bus.status = 'operativo'
            bus.save(update_fields=['status','updated_at'])
        execution = m.PreventiveExecution.objects.filter(work_order=order).first()
        if execution:
            plan = m.PreventivePlan.objects.select_for_update().get(pk=execution.plan_id)
            if plan.interval_days: plan.next_date = timezone.localdate() + timedelta(days=plan.interval_days)
            if plan.interval_km: plan.next_km = bus.odometer + plan.interval_km
            if plan.interval_hours:
                if bus.engine_hours is None: raise ValidationError('Registra horas de motor antes de cerrar este preventivo.')
                plan.next_hours=bus.engine_hours+plan.interval_hours
            plan.save()
            execution.completed_at = timezone.now()
            execution.save(update_fields=['completed_at'])
    else:
        order.save(update_fields=['status','started_at','updated_at'])
    audit(user,'Cambio de estado',order,{'antes':prior,'despues':target})
    if order.assigned_to_id and order.assigned_to_id!=user.pk:
        from .modules.inspecciones.services import notify
        notify(order.assigned_to,'ordenes','Estado de OT actualizado',str(order)+' · '+order.get_status_display(),f'/modulos/ordenes/{order.pk}/')
    return order


@transaction.atomic
def convert_request(user, request_id):
    if user.role not in ('administrador','supervisor'): raise PermissionDenied
    req = m.MaintenanceRequest.objects.select_for_update().get(pk=request_id,organization_id=user.organization_id)
    existing = m.WorkOrder.objects.filter(source_request=req).first()
    if existing: return existing
    if req.status not in ('pendiente','en_revision'): raise ValidationError('La solicitud ya no está pendiente.')
    order = m.WorkOrder.objects.create(organization=req.organization,bus=req.bus,title=req.title,
                                     description=req.description,priority=req.priority,source_request=req,
                                     failure_type=req.failure_type,failure_category=req.failure_type.system if req.failure_type_id else '')
    req.status = 'convertida'
    req.save(update_fields=['status','updated_at'])
    audit(user,'Solicitud convertida a OT',order)
    return order


@transaction.atomic
def generate_preventive(user, plan_id):
    if user.role not in ('administrador','supervisor'): raise PermissionDenied
    plan = m.PreventivePlan.objects.select_for_update().get(pk=plan_id,organization_id=user.organization_id)
    if not plan.active: raise ValidationError('El plan está desactivado.')
    existing = m.PreventiveExecution.objects.filter(plan=plan,completed_at__isnull=True).first()
    if existing: return existing.work_order
    order = m.WorkOrder.objects.create(organization=plan.organization,bus=plan.bus,title=plan.title,
                                     description=plan.tasks,kind='preventivo',due_date=plan.next_date,program=plan.program,reported_by=user)
    from .modules.hooks import after_save
    after_save(order,user,True)
    m.PreventiveExecution.objects.create(organization=plan.organization,plan=plan,work_order=order,
                                        next_date_before=plan.next_date,next_km_before=plan.next_km)
    audit(user,'OT preventiva generada',order)
    return order


def receive_purchase(user,purchase_id):
    from .modules.inventario.services import receive
    return receive(user,purchase_id)
