from django.core.exceptions import PermissionDenied,ValidationError
from django.db import transaction
from cmms import models as m

@transaction.atomic
def create_order(user,key,pk):
    if user.role not in ('administrador','supervisor'): raise PermissionDenied
    mapping={'recomendaciones':m.PredictionRecommendation,'retiros':m.Recall,'incidentes':m.SafetyIncident}
    model=mapping[key]
    obj=model.objects.select_for_update().get(pk=pk,organization_id=user.organization_id)
    if obj.work_order_id: return obj.work_order
    if getattr(obj,'status','') in ('descartada','resuelto','atendido'): raise ValidationError('El registro ya no está pendiente.')
    title=obj.title if hasattr(obj,'title') else f'Campaña {obj.reference}'
    description=getattr(obj,'explanation',getattr(obj,'description',''))
    priority='critica' if getattr(obj,'severity','')=='critica' or getattr(getattr(obj,'assessment',None),'level','')=='critico' else 'alta'
    order=m.WorkOrder.objects.create(organization=obj.organization,bus=obj.bus,title=title[:180],description=description,priority=priority)
    obj.work_order=order
    obj.status='ot_creada'
    obj.save(update_fields=['work_order','status'])
    from cmms.services import audit
    audit(user,'OT creada desde '+key,order,{'origen_id':obj.pk})
    audit(user,'Vinculado a OT',obj,{'orden':order.pk})
    return order
