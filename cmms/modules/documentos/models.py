from django.db import models
from cmms.core_models import Record, Document, Bus, Department, User

class DocumentAnalysis(Record):
    document=models.OneToOneField(Document,on_delete=models.PROTECT,verbose_name='Documento')
    state=models.CharField('Estado',max_length=20,choices=[('pendiente','Pendiente'),('analizado','Analizado'),('revisar','Requiere revisión')],default='pendiente')
    method=models.CharField('Motor',max_length=80,default='Revisión documental local')
    extracted_text=models.TextField('Texto extraído',blank=True)
    findings=models.JSONField('Hallazgos',default=list)
    metadata=models.JSONField('Datos del archivo',default=dict)
    analyzed_at=models.DateTimeField(null=True,blank=True)
    def __str__(self): return str(self.document)

class Camera(Record):
    name=models.CharField('Cámara',max_length=120)
    department=models.ForeignKey(Department,on_delete=models.PROTECT,null=True,blank=True,verbose_name='Patio')
    bus=models.ForeignKey(Bus,on_delete=models.PROTECT,null=True,blank=True,verbose_name='Bus')
    stream_url=models.URLField('URL accesible desde el navegador',max_length=600)
    stream_type=models.CharField('Tipo de fuente',max_length=20,choices=[('video','Video MP4 / WebM'),('mjpeg','Imagen / MJPEG')],default='mjpeg')
    active=models.BooleanField('Activa',default=True)
    notes=models.TextField('Origen y autorización de la fuente',blank=True)
    def __str__(self): return self.name

class CameraObservation(Record):
    camera=models.ForeignKey(Camera,on_delete=models.PROTECT,verbose_name='Cámara')
    bus=models.ForeignKey(Bus,on_delete=models.PROTECT,null=True,blank=True,verbose_name='Bus')
    observed_at=models.DateTimeField('Fecha de observación')
    title=models.CharField('Observación',max_length=180)
    notes=models.TextField('Detalle')
    risk=models.CharField('Nivel',max_length=20,choices=[('normal','Normal'),('atencion','Atención'),('critico','Crítico')],default='normal')
    reported_by=models.ForeignKey(User,on_delete=models.PROTECT,editable=False)
    def __str__(self): return self.title
