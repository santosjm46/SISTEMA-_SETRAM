from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from cmms.core_models import Record, Bus, User, WorkOrder

class ComplianceRequirement(Record):
    title=models.CharField('Requisito',max_length=180)
    reference=models.CharField('Referencia / fuente',max_length=180,blank=True)
    bus=models.ForeignKey(Bus,on_delete=models.PROTECT,null=True,blank=True,verbose_name='Bus')
    responsible=models.ForeignKey(User,on_delete=models.PROTECT,verbose_name='Responsable')
    due_date=models.DateField('Vencimiento')
    status=models.CharField('Estado',max_length=20,choices=[('pendiente','Pendiente'),('en_proceso','En proceso'),('completado','Completado'),('no_aplica','No aplica')],default='pendiente')
    evidence=models.TextField('Evidencia / justificación',blank=True)
    category=models.CharField('Categoría',max_length=30,choices=[('vehiculo','Vehículo'),('conductor','Conductor'),('operacion','Operación'),('documental','Documental')],default='vehiculo',blank=True)
    impact=models.CharField('Impacto',max_length=20,choices=[('bajo','Bajo'),('medio','Medio'),('alto','Alto'),('critico','Crítico')],default='medio',blank=True)
    @property
    def overdue(self): return self.status not in ('completado','no_aplica') and self.due_date < timezone.localdate()
    def clean(self):
        super().clean()
        if self.status in ('completado','no_aplica') and not self.evidence.strip(): raise ValidationError({'evidence':'Describe la evidencia o justificación.'})
    def __str__(self): return self.title

class Recall(Record):
    reference=models.CharField('Campaña / boletín',max_length=100)
    manufacturer=models.CharField('Fabricante',max_length=100)
    bus=models.ForeignKey(Bus,on_delete=models.PROTECT,verbose_name='Bus afectado')
    description=models.TextField('Acción requerida')
    due_date=models.DateField('Fecha objetivo',null=True,blank=True)
    status=models.CharField('Estado',max_length=20,choices=[('abierto','Abierto'),('ot_creada','OT creada'),('atendido','Atendido')],default='abierto')
    work_order=models.OneToOneField(WorkOrder,on_delete=models.PROTECT,null=True,blank=True,editable=False)
    resolution=models.TextField('Resultado / evidencia',blank=True)
    source_url=models.URLField('Fuente / boletín del fabricante',blank=True)
    campaign_type=models.CharField('Tipo',max_length=25,choices=[('fabricante','Campaña del fabricante'),('actualizacion','Actualización operativa')],default='fabricante',blank=True)
    def __str__(self): return f'{self.reference} · {self.bus.code}'
    def clean(self):
        super().clean()
        if self.status=='atendido' and not self.resolution.strip(): raise ValidationError({'resolution':'Registra evidencia de atención.'})
    class Meta(Record.Meta):
        constraints=[models.UniqueConstraint(fields=['organization','bus','reference'],name='cmms_unique_recall')]

class SafetyIncident(Record):
    bus=models.ForeignKey(Bus,on_delete=models.PROTECT,verbose_name='Bus')
    reported_by=models.ForeignKey(User,on_delete=models.PROTECT,editable=False)
    title=models.CharField('Incidente',max_length=180)
    description=models.TextField('Descripción')
    severity=models.CharField('Severidad',max_length=20,choices=[('menor','Menor'),('alta','Alta'),('critica','Crítica')],default='menor')
    occurred_at=models.DateTimeField('Fecha y hora',default=timezone.now)
    status=models.CharField('Estado',max_length=20,choices=[('abierto','Abierto'),('ot_creada','OT creada'),('resuelto','Resuelto')],default='abierto')
    resolution=models.TextField('Resolución',blank=True)
    work_order=models.OneToOneField(WorkOrder,on_delete=models.PROTECT,null=True,blank=True,editable=False)
    def __str__(self): return self.title
    def clean(self):
        super().clean()
        if self.status=='resuelto' and not self.resolution.strip(): raise ValidationError({'resolution':'Registra la resolución.'})
