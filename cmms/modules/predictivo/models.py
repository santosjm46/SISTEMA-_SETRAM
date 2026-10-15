from django.db import models
from django.core.exceptions import ValidationError
from cmms.core_models import Record, Bus, WorkOrder

class PredictiveAssessment(Record):
    bus=models.ForeignKey(Bus,on_delete=models.PROTECT,verbose_name='Bus')
    score=models.PositiveIntegerField('Índice de riesgo',null=True,blank=True)
    level=models.CharField('Nivel',max_length=20,choices=[('sin_datos','Sin datos suficientes'),('bajo','Bajo'),('medio','Medio'),('alto','Alto'),('critico','Crítico')])
    algorithm=models.CharField('Método',max_length=80,default='Reglas SETRAM v1')
    signals=models.JSONField('Señales y procedencia',default=list)
    coverage=models.JSONField('Cobertura de datos',default=dict)
    def __str__(self): return f'{self.bus.code} · {self.get_level_display()}'

class PredictionRecommendation(Record):
    assessment=models.ForeignKey(PredictiveAssessment,on_delete=models.PROTECT,verbose_name='Evaluación')
    bus=models.ForeignKey(Bus,on_delete=models.PROTECT,verbose_name='Bus')
    title=models.CharField('Recomendación',max_length=180)
    explanation=models.TextField('Justificación')
    review_notes=models.TextField('Motivo de revisión / descarte',blank=True)
    status=models.CharField('Estado',max_length=20,choices=[('pendiente','Pendiente'),('ot_creada','OT creada'),('descartada','Descartada')],default='pendiente')
    work_order=models.OneToOneField(WorkOrder,on_delete=models.PROTECT,null=True,blank=True,editable=False)
    estimated_cost=models.DecimalField('Costo de intervención estimado (Bs)',max_digits=12,decimal_places=2,null=True,blank=True)
    potential_savings=models.DecimalField('Ahorro potencial declarado (Bs)',max_digits=12,decimal_places=2,null=True,blank=True)
    economic_basis=models.TextField('Fuente y supuestos económicos',blank=True)
    def __str__(self): return self.title
    def clean(self):
        super().clean()
        if self.status=='ot_creada' and not self.work_order_id: raise ValidationError('Genera la OT mediante la acción del módulo.')
        if self.status=='descartada' and not self.review_notes.strip(): raise ValidationError({'review_notes':'Indica por qué descartas la recomendación.'})
        if (self.estimated_cost is not None or self.potential_savings is not None) and not self.economic_basis.strip(): raise ValidationError({'economic_basis':'Documenta los supuestos de esta estimación.'})
        if any(v is not None and v<0 for v in (self.estimated_cost,self.potential_savings)): raise ValidationError('Los importes estimados no pueden ser negativos.')
