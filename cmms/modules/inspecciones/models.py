from django.db import models
from django.core.validators import MinValueValidator
from cmms.core_models import Record, Bus, User, Checklist

class InspectionReminder(Record):
    title=models.CharField('Recordatorio',max_length=150)
    bus=models.ForeignKey(Bus,on_delete=models.PROTECT,verbose_name='Bus')
    assigned_to=models.ForeignKey(User,on_delete=models.PROTECT,verbose_name='Responsable')
    checklist=models.ForeignKey(Checklist,on_delete=models.PROTECT,null=True,blank=True,verbose_name='Plantilla')
    next_due=models.DateTimeField('Próximo envío en la aplicación')
    interval_days=models.PositiveIntegerField('Repetir cada (días)',default=1,validators=[MinValueValidator(1)])
    active=models.BooleanField('Activo',default=True)
    def __str__(self): return self.title
    class Meta(Record.Meta):
        constraints=[models.CheckConstraint(condition=models.Q(interval_days__gte=1),name='cmms_reminder_interval_positive')]

class Notification(Record):
    user=models.ForeignKey(User,on_delete=models.PROTECT,verbose_name='Destinatario')
    title=models.CharField('Notificación',max_length=180)
    body=models.TextField('Detalle')
    read_at=models.DateTimeField('Leída',null=True,blank=True)
    reminder=models.ForeignKey(InspectionReminder,on_delete=models.PROTECT,null=True,blank=True)
    occurrence=models.DateTimeField(null=True,blank=True)
    kind=models.CharField('Tipo',max_length=30,default='inspecciones')
    link=models.CharField('Destino interno',max_length=240,blank=True)
    dedupe_key=models.CharField(max_length=150,blank=True,default='')
    def __str__(self): return self.title
    class Meta(Record.Meta):
        constraints=[models.UniqueConstraint(fields=['reminder','occurrence'],condition=models.Q(reminder__isnull=False),name='cmms_unique_reminder_notification'),models.UniqueConstraint(fields=['organization','user','dedupe_key'],condition=~models.Q(dedupe_key=''),name='cmms_unique_notification_key')]
