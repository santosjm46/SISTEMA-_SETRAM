from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from cmms.core_models import Record, WorkOrder, User,FAILURE_SYSTEMS

class FailureType(Record):
    code=models.CharField('Código interno',max_length=40)
    name=models.CharField('Tipo de falla / síntoma',max_length=140)
    system=models.CharField('Sistema afectado',max_length=30,choices=FAILURE_SYSTEMS)
    description=models.TextField('Descripción orientativa',blank=True)
    active=models.BooleanField('Activo',default=True)
    catalog_source=models.CharField('Origen del catálogo',max_length=240,blank=True,editable=False)
    def __str__(self):return self.name
    class Meta(Record.Meta):
        constraints=[models.UniqueConstraint(fields=['organization','code'],name='cmms_unique_failure_type')]

class ServiceTask(Record):
    name=models.CharField('Tarea estándar',max_length=140)
    instructions=models.TextField('Procedimiento y evidencia requerida')
    estimated_hours=models.DecimalField('Duración estimada (h)',max_digits=7,decimal_places=2,validators=[MinValueValidator(0)])
    active=models.BooleanField('Activa',default=True)
    catalog_source=models.CharField('Origen del catálogo',max_length=240,blank=True,editable=False)
    def __str__(self): return self.name

class WorkOrderTask(Record):
    work_order=models.ForeignKey(WorkOrder,on_delete=models.PROTECT,verbose_name='Orden de trabajo')
    template=models.ForeignKey(ServiceTask,on_delete=models.PROTECT,null=True,blank=True,verbose_name='Tarea estándar')
    title=models.CharField('Tarea',max_length=160)
    status=models.CharField('Estado',max_length=20,choices=[('pendiente','Pendiente'),('hecha','Realizada'),('no_aplica','No aplica')],default='pendiente')
    spent_hours=models.DecimalField('Tiempo utilizado (h)',max_digits=8,decimal_places=2,default=0,validators=[MinValueValidator(0)])
    completion_notes=models.TextField('Resultado / evidencia',blank=True)
    completed_by=models.ForeignKey(User,on_delete=models.PROTECT,null=True,blank=True,editable=False)
    completed_at=models.DateTimeField(null=True,blank=True,editable=False)
    def __str__(self): return self.title
    def clean(self):
        super().clean()
        if self.status!='pendiente' and not self.completion_notes.strip(): raise ValidationError({'completion_notes':'Registra el resultado o justificación.'})
        if self.work_order_id and self.work_order.status=='cerrada': raise ValidationError('Una OT cerrada no admite tareas ni cambios.')

class WorkOrderComment(Record):
    work_order=models.ForeignKey(WorkOrder,on_delete=models.PROTECT,verbose_name='Orden de trabajo')
    author=models.ForeignKey(User,on_delete=models.PROTECT,editable=False)
    text=models.TextField('Comentario / evidencia')
    def __str__(self): return self.text[:70]
