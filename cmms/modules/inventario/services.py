import uuid
from decimal import Decimal,InvalidOperation
from django.db import transaction
from django.core.exceptions import PermissionDenied,ValidationError
from django.utils import timezone
from cmms import models as m

@transaction.atomic
def receive(user,purchase_id,quantity=None,line_id=None,token=None):
    if user.role not in ('administrador','supervisor'): raise PermissionDenied
    purchase=m.PurchaseOrder.objects.select_for_update().get(pk=purchase_id,organization=user.organization)
    lines=list(purchase.purchaseline_set.select_for_update().order_by('pk'))
    targets=[(None,purchase.part,purchase.quantity,purchase.received_quantity,purchase.unit_cost)]+[(line,line.part,line.quantity,line.received_quantity,line.unit_cost) for line in lines]
    partial=quantity is not None
    if partial:
        try:
            quantity=Decimal(str(quantity)); token=uuid.UUID(str(token))
            if not quantity.is_finite() or quantity<=0 or quantity.as_tuple().exponent < -2: raise ValueError()
        except (InvalidOperation,ValueError,TypeError): raise ValidationError('Cantidad positiva con hasta dos decimales y token de formulario válido.')
        previous=m.PurchaseReceipt.objects.filter(token=token,organization=user.organization).first()
        selected=int(line_id) if str(line_id or '').isdigit() and int(line_id)>0 else None
        if previous:
            if previous.purchase_id!=purchase.pk or previous.line_id!=selected or previous.quantity!=quantity: raise ValidationError('El formulario ya se utilizó con otra recepción.')
            return purchase
        targets=[row for row in targets if (row[0].pk if row[0] else None)==selected]
        if not targets: raise ValidationError('La línea no pertenece a esta orden.')
    elif purchase.status=='recibido': return purchase
    # Recepciones concurrentes del mismo pedido y bloqueos de almacén ordenados.
    list(m.Part.objects.select_for_update().filter(pk__in={row[1].pk for row in targets},organization=user.organization).order_by('pk'))
    from cmms.services import audit
    for line,part,ordered,received,cost in targets:
        amount=quantity if partial else ordered-received
        if not amount: continue
        if amount>ordered-received: raise ValidationError('La cantidad excede lo pendiente de recibir.')
        movement=m.StockMovement(organization=user.organization,part=part,kind='entrada',quantity=amount,unit_cost=cost,actor=user,reference=f'Recepción OC-{purchase.pk}')
        movement.full_clean(); movement.save()
        part.refresh_from_db(); part.quantity+=amount; part.save(update_fields=['quantity','updated_at'])
        receipt=m.PurchaseReceipt.objects.create(organization=user.organization,purchase=purchase,line=line,quantity=amount,movement=movement,actor=user,token=token if partial else uuid.uuid4())
        if line:
            line.received_quantity+=amount; line.save(update_fields=['received_quantity','updated_at'])
        else:
            purchase.received_quantity+=amount
            if not purchase.receipt_id: purchase.receipt=movement
        audit(user,'Recepción de compra',receipt,{'cantidad':str(amount),'movimiento':movement.pk})
    complete=purchase.received_quantity==purchase.quantity and all(line.received_quantity==line.quantity for line in lines)
    purchase.status='recibido' if complete else 'parcial'
    purchase.received_at=timezone.now() if complete else None
    purchase.save(update_fields=['received_quantity','receipt','status','received_at','updated_at'])
    audit(user,'Compra recibida' if complete else 'Compra recibida parcialmente',purchase)
    return purchase

@transaction.atomic
def update_demands(org):
    parts=m.Part.objects.select_for_update().filter(organization=org,auto_demand=True).order_by('pk')
    count=0
    for part in parts:
        gap=part.minimum-part.quantity
        if gap>0:
            if m.PurchaseDemand.objects.filter(part=part,status='oc_creada',purchase__status__in=('pedido','parcial')).exists():continue
            demand,created=m.PurchaseDemand.objects.get_or_create(organization=org,part=part,status='pendiente',defaults={'quantity':gap})
            if not created and demand.quantity!=gap:demand.quantity=gap;demand.save(update_fields=['quantity','updated_at'])
            count+=int(created)
        else:m.PurchaseDemand.objects.filter(part=part,status='pendiente').update(status='resuelta')
    return count

@transaction.atomic
def demand_to_purchase(user,pk):
    if user.role not in ('administrador','supervisor'):raise PermissionDenied
    demand=m.PurchaseDemand.objects.select_for_update().get(pk=pk,organization=user.organization)
    if demand.purchase_id:return demand.purchase
    if demand.status!='pendiente':raise ValidationError('La demanda ya no está pendiente.')
    if not demand.part.supplier_id:raise ValidationError('Asigna un proveedor al repuesto antes de crear la orden.')
    purchase=m.PurchaseOrder.objects.create(organization=user.organization,supplier=demand.part.supplier,part=demand.part,quantity=demand.quantity,unit_cost=demand.part.unit_cost,reference=f'Reposición de demanda {demand.pk}')
    demand.status='oc_creada';demand.purchase=purchase;demand.save()
    from cmms.services import audit
    audit(user,'Demanda convertida a compra',demand,{'compra':purchase.pk})
    return purchase
