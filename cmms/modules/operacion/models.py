from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from cmms.core_models import Record, Bus, User

class ServiceRoute(Record):
    code=models.CharField('Código de ruta',max_length=40)
    name=models.CharField('Ruta',max_length=140)
    origin=models.CharField('Origen',max_length=140)
    destination=models.CharField('Destino',max_length=140)
    active=models.BooleanField('Activa',default=True)
    def __str__(self): return self.name
    class Meta(Record.Meta):
        constraints=[models.UniqueConstraint(fields=['organization','code'],name='cmms_unique_route')]

class ShiftLog(Record):
    bus=models.ForeignKey(Bus,on_delete=models.PROTECT,verbose_name='Bus')
    driver=models.ForeignKey(User,on_delete=models.PROTECT,verbose_name='Conductor')
    started_at=models.DateTimeField('Inicio')
    ended_at=models.DateTimeField('Fin')
    break_minutes=models.PositiveIntegerField('Descanso (minutos)',default=0)
    notes=models.TextField('Observaciones',blank=True)
    @property
    def driving_hours(self):
        if not self.started_at or not self.ended_at: return 0
        return round((self.ended_at-self.started_at).total_seconds()/3600-self.break_minutes/60,2)
    def clean(self):
        super().clean()
        if self.driver_id and self.driver.role != 'conductor': raise ValidationError({'driver':'Debe tener rol Conductor.'})
        if self.started_at and self.ended_at:
            if self.ended_at <= self.started_at: raise ValidationError({'ended_at':'El fin debe ser posterior al inicio.'})
            elif self.break_minutes*60 > (self.ended_at-self.started_at).total_seconds(): raise ValidationError({'break_minutes':'El descanso supera la jornada.'})
            if self.driver_id and ShiftLog.objects.filter(organization_id=self.organization_id,driver_id=self.driver_id,started_at__lt=self.ended_at,ended_at__gt=self.started_at).exclude(pk=self.pk).exists():
                raise ValidationError('La jornada se solapa con otra del conductor.')
        if self.ended_at and self.ended_at > timezone.now()+timezone.timedelta(minutes=5): raise ValidationError({'ended_at':'Registra una jornada realizada.'})
    def __str__(self): return f'{self.driver} · {self.started_at:%d/%m/%Y}'

class TripLog(Record):
    bus=models.ForeignKey(Bus,on_delete=models.PROTECT,verbose_name='Bus')
    driver=models.ForeignKey(User,on_delete=models.PROTECT,verbose_name='Conductor')
    route=models.ForeignKey(ServiceRoute,on_delete=models.PROTECT,verbose_name='Ruta')
    started_at=models.DateTimeField('Salida')
    ended_at=models.DateTimeField('Llegada',null=True,blank=True)
    start_km=models.DecimalField('Odómetro inicial (km)',max_digits=12,decimal_places=1,validators=[MinValueValidator(0)])
    end_km=models.DecimalField('Odómetro final (km)',max_digits=12,decimal_places=1,null=True,blank=True,validators=[MinValueValidator(0)])
    passengers=models.PositiveIntegerField('Pasajeros transportados',default=0)
    status=models.CharField('Estado',max_length=20,choices=[('programado','Programado'),('en_ruta','En ruta'),('completado','Completado')],default='programado')
    notes=models.TextField('Observaciones',blank=True)
    @property
    def distance(self): return self.end_km-self.start_km if self.end_km is not None else None
    def clean(self):
        super().clean()
        if self.driver_id and self.driver.role != 'conductor': raise ValidationError({'driver':'Debe tener rol Conductor.'})
        if self.end_km is not None and self.end_km < self.start_km: raise ValidationError({'end_km':'El odómetro no puede retroceder.'})
        if self.ended_at and self.ended_at <= self.started_at: raise ValidationError({'ended_at':'La llegada debe ser posterior a la salida.'})
        if self.status=='completado' and (not self.ended_at or self.end_km is None): raise ValidationError('Un recorrido completado necesita llegada y odómetro final.')
        if self.status=='en_ruta' and self.bus_id and self.bus.status!='operativo': raise ValidationError('El bus no está habilitado para salir.')
    def __str__(self): return f'{self.bus.code} · {self.route}'

class OperatingPolicy(Record):
    name=models.CharField('Política de operación',max_length=120)
    daily_driving_hours=models.DecimalField('Umbral interno de conducción por jornada (h)',max_digits=4,decimal_places=1,validators=[MinValueValidator(1),MaxValueValidator(24)])
    active=models.BooleanField('Activa',default=True)
    notes=models.TextField('Fuente y criterio operativo',help_text='Umbral interno definido por SETRAM; no representa una certificación normativa.')
    def __str__(self): return self.name
    class Meta(Record.Meta):
        constraints=[models.UniqueConstraint(fields=['organization'],condition=models.Q(active=True),name='cmms_one_active_operating_policy')]
