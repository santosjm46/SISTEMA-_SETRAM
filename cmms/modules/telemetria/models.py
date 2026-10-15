import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from cmms.core_models import Record, Bus, User

class TelemetryDevice(Record):
    name=models.CharField('Dispositivo',max_length=120)
    external_id=models.CharField('Identificador externo',max_length=100)
    bus=models.ForeignKey(Bus,on_delete=models.PROTECT,verbose_name='Bus')
    provider=models.CharField('Origen',max_length=30,choices=[('generico','API normalizada'),('samsara','Samsara (normalizado)'),('geotab','Geotab (normalizado)'),('manual','Registro manual')],default='generico')
    active=models.BooleanField('Activo',default=True)
    def __str__(self): return self.name
    class Meta(Record.Meta):
        constraints=[models.UniqueConstraint(fields=['organization','external_id'],name='cmms_unique_telemetry_device')]

class TelemetryReading(Record):
    bus=models.ForeignKey(Bus,on_delete=models.PROTECT,verbose_name='Bus')
    device=models.ForeignKey(TelemetryDevice,on_delete=models.PROTECT,null=True,blank=True,verbose_name='Dispositivo')
    measured_at=models.DateTimeField('Fecha de lectura',default=timezone.now)
    external_event=models.CharField(max_length=100,blank=True,editable=False)
    latitude=models.DecimalField('Latitud',max_digits=10,decimal_places=7,null=True,blank=True,validators=[MinValueValidator(-90),MaxValueValidator(90)])
    longitude=models.DecimalField('Longitud',max_digits=10,decimal_places=7,null=True,blank=True,validators=[MinValueValidator(-180),MaxValueValidator(180)])
    odometer=models.DecimalField('Odómetro (km)',max_digits=12,decimal_places=1,validators=[MinValueValidator(0)])
    engine_hours=models.DecimalField('Horas de motor',max_digits=12,decimal_places=1,null=True,blank=True,validators=[MinValueValidator(0)])
    speed=models.DecimalField('Velocidad (km/h)',max_digits=6,decimal_places=1,null=True,blank=True,validators=[MinValueValidator(0)])
    temperature=models.DecimalField('Temperatura de refrigerante (°C)',max_digits=6,decimal_places=1,null=True,blank=True)
    fault_code=models.CharField('Código de falla',max_length=100,blank=True)
    def __str__(self): return f'{self.bus.code} · {self.measured_at:%d/%m/%Y %H:%M}'
    def clean(self):
        super().clean()
        if (self.latitude is None) != (self.longitude is None):
            raise ValidationError('Latitud y longitud deben indicarse juntas.')
        if self.device_id and self.device.bus_id != self.bus_id:
            raise ValidationError({'device':'El dispositivo no corresponde al bus.'})
        if self.measured_at > timezone.now()+timezone.timedelta(minutes=5):
            raise ValidationError({'measured_at':'La lectura no puede estar en el futuro.'})
    class Meta(Record.Meta):
        constraints=[models.UniqueConstraint(fields=['device','external_event'],condition=~models.Q(external_event=''),name='cmms_unique_telemetry_event')]

class IntegrationKey(Record):
    public_id=models.UUIDField(default=uuid.uuid4,unique=True,editable=False)
    name=models.CharField('Integración',max_length=120)
    digest=models.CharField(max_length=64,editable=False)
    active=models.BooleanField('Activa',default=True)
    created_by=models.ForeignKey(User,on_delete=models.PROTECT)
    last_used=models.DateTimeField(null=True,blank=True)
    scopes=models.JSONField('Capacidades autorizadas',default=list,blank=True)
    def __str__(self): return self.name
