import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from cmms.core_models import Record,PurchaseOrder,Part,StockMovement,User

class PartCategory(Record):
    code=models.SlugField('Código interno',max_length=60)
    name=models.CharField('Categoría',max_length=80)
    source_label=models.CharField('Etiqueta en la referencia',max_length=100,blank=True)
    active=models.BooleanField('Activa',default=True)
    catalog_source=models.CharField('Origen del catálogo',max_length=240,blank=True,editable=False)
    def __str__(self):return self.name
    class Meta(Record.Meta):
        constraints=[models.UniqueConstraint(fields=['organization','code'],name='cmms_unique_part_category')]

class PurchaseLine(Record):
    purchase=models.ForeignKey(PurchaseOrder,on_delete=models.PROTECT,verbose_name='Orden de compra')
    part=models.ForeignKey(Part,on_delete=models.PROTECT,verbose_name='Repuesto')
    quantity=models.DecimalField('Cantidad pedida',max_digits=12,decimal_places=2,validators=[MinValueValidator(.01)])
    unit_cost=models.DecimalField('Costo unitario (Bs)',max_digits=12,decimal_places=2,validators=[MinValueValidator(0)])
    received_quantity=models.DecimalField('Cantidad recibida',max_digits=12,decimal_places=2,default=0,editable=False)
    def __str__(self): return f'{self.purchase} · {self.part}'
    def clean(self):
        super().clean()
        if self.purchase_id and self.purchase.status!='pedido': raise ValidationError('Las líneas se definen antes de comenzar la recepción.')
    class Meta(Record.Meta):
        constraints=[models.CheckConstraint(condition=models.Q(received_quantity__gte=0)&models.Q(received_quantity__lte=models.F('quantity')),name='cmms_line_received_bounds')]

class PurchaseReceipt(Record):
    token=models.UUIDField(default=uuid.uuid4,unique=True,editable=False)
    purchase=models.ForeignKey(PurchaseOrder,on_delete=models.PROTECT)
    line=models.ForeignKey(PurchaseLine,on_delete=models.PROTECT,null=True,blank=True)
    quantity=models.DecimalField(max_digits=12,decimal_places=2)
    movement=models.OneToOneField(StockMovement,on_delete=models.PROTECT)
    actor=models.ForeignKey(User,on_delete=models.PROTECT)
    def __str__(self): return f'Recepción OC-{self.purchase_id} · {self.quantity}'

class PurchaseDemand(Record):
    part=models.ForeignKey(Part,on_delete=models.PROTECT)
    quantity=models.DecimalField('Reposición solicitada',max_digits=12,decimal_places=2)
    status=models.CharField('Estado',max_length=20,choices=[('pendiente','Pendiente'),('oc_creada','OC creada'),('resuelta','Resuelta')],default='pendiente')
    purchase=models.ForeignKey(PurchaseOrder,on_delete=models.PROTECT,null=True,blank=True)
    def __str__(self):return str(self.part)
    class Meta(Record.Meta):
        constraints=[models.UniqueConstraint(fields=['part'],condition=models.Q(status='pendiente'),name='cmms_one_pending_demand')]
