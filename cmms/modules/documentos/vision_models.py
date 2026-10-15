from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator,MaxValueValidator
from cmms.core_models import Record,Bus
from .models import Camera

class VisionFrame(Record):
    camera=models.ForeignKey(Camera,on_delete=models.PROTECT)
    external_event=models.CharField('Evento de la fuente',max_length=100)
    measured_at=models.DateTimeField('Fecha de captura')
    model_version=models.CharField('Motor / versión declarada por la fuente',max_length=120)
    digest=models.CharField(max_length=64,editable=False)
    def __str__(self):return f'{self.camera} · {self.measured_at:%d/%m/%Y %H:%M}'
    class Meta(Record.Meta):
        constraints=[models.UniqueConstraint(fields=['camera','external_event'],name='cmms_unique_vision_frame')]

class VisionDetection(Record):
    frame=models.ForeignKey(VisionFrame,on_delete=models.PROTECT)
    bus=models.ForeignKey(Bus,on_delete=models.PROTECT,null=True,blank=True)
    object_id=models.CharField('Objeto de la fuente',max_length=80)
    label=models.CharField('Etiqueta',max_length=160)
    plate=models.CharField('Placa detectada',max_length=30,blank=True)
    x=models.DecimalField(max_digits=7,decimal_places=6,validators=[MinValueValidator(0),MaxValueValidator(1)])
    y=models.DecimalField(max_digits=7,decimal_places=6,validators=[MinValueValidator(0),MaxValueValidator(1)])
    width=models.DecimalField(max_digits=7,decimal_places=6,validators=[MinValueValidator(0),MaxValueValidator(1)])
    height=models.DecimalField(max_digits=7,decimal_places=6,validators=[MinValueValidator(0),MaxValueValidator(1)])
    confidence=models.DecimalField('Confianza declarada (%)',max_digits=5,decimal_places=2,validators=[MinValueValidator(0),MaxValueValidator(100)])
    risk=models.CharField('Nivel sugerido por la fuente',max_length=20,choices=[('normal','Normal'),('atencion','Atención'),('critico','Crítico')],default='normal')
    status=models.CharField('Revisión humana',max_length=20,choices=[('pendiente','Pendiente'),('confirmada','Confirmada'),('descartada','Descartada')],default='pendiente')
    review_notes=models.TextField('Evidencia / revisión',blank=True)
    def __str__(self):return self.label
    def clean(self):
        super().clean()
        if self.width<=0 or self.height<=0 or self.x+self.width>1 or self.y+self.height>1:raise ValidationError('La caja debe estar dentro del encuadre normalizado.')
        if self.status!='pendiente' and not self.review_notes.strip():raise ValidationError({'review_notes':'Registra la evidencia de tu revisión.'})
