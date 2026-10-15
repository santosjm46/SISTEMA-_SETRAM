from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from cmms.core_models import Record, Supplier, Department, Document,User

class Budget(Record):
    name=models.CharField('Presupuesto',max_length=160)
    year=models.PositiveIntegerField('Gestión',validators=[MinValueValidator(2020)])
    department=models.ForeignKey(Department,on_delete=models.PROTECT,null=True,blank=True,verbose_name='Departamento')
    amount=models.DecimalField('Importe autorizado (Bs)',max_digits=14,decimal_places=2,validators=[MinValueValidator(0)])
    notes=models.TextField('Alcance y fuente',blank=True)
    def __str__(self): return f'{self.name} · {self.year}'

class Contract(Record):
    reference=models.CharField('Número / referencia',max_length=100)
    supplier=models.ForeignKey(Supplier,on_delete=models.PROTECT,verbose_name='Proveedor')
    title=models.CharField('Objeto del contrato',max_length=180)
    start_date=models.DateField('Inicio')
    end_date=models.DateField('Vencimiento')
    amount=models.DecimalField('Importe (Bs)',max_digits=14,decimal_places=2,validators=[MinValueValidator(0)])
    status=models.CharField('Estado',max_length=20,choices=[('vigente','Vigente'),('cerrado','Cerrado'),('cancelado','Cancelado')],default='vigente')
    notes=models.TextField('Condiciones / observaciones',blank=True)
    def __str__(self): return self.reference
    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.end_date < self.start_date: raise ValidationError({'end_date':'El vencimiento debe ser posterior al inicio.'})

class Invoice(Record):
    reference=models.CharField('Comprobante / factura',max_length=100)
    supplier=models.ForeignKey(Supplier,on_delete=models.PROTECT,verbose_name='Proveedor')
    budget=models.ForeignKey(Budget,on_delete=models.PROTECT,null=True,blank=True,verbose_name='Presupuesto')
    document=models.ForeignKey(Document,on_delete=models.PROTECT,null=True,blank=True,verbose_name='Respaldo')
    date=models.DateField('Fecha del comprobante')
    due_date=models.DateField('Fecha de pago',null=True,blank=True)
    amount=models.DecimalField('Importe (Bs)',max_digits=14,decimal_places=2,validators=[MinValueValidator(0)])
    status=models.CharField('Estado',max_length=20,choices=[('pendiente','Pendiente'),('pagada','Pagada'),('anulada','Anulada')],default='pendiente')
    notes=models.TextField('Referencia de pago / observaciones',blank=True)
    def __str__(self): return self.reference
    def clean(self):
        super().clean()
        if self.status=='pagada' and not self.notes.strip(): raise ValidationError({'notes':'Registra el respaldo o referencia del pago.'})
    class Meta(Record.Meta):
        constraints=[models.UniqueConstraint(fields=['organization','supplier','reference'],name='cmms_unique_invoice')]

class DepartmentShift(Record):
    department=models.ForeignKey(Department,on_delete=models.PROTECT,verbose_name='Patio / departamento')
    name=models.CharField('Turno',max_length=100)
    weekday=models.PositiveIntegerField('Día',choices=[(0,'Lunes'),(1,'Martes'),(2,'Miércoles'),(3,'Jueves'),(4,'Viernes'),(5,'Sábado'),(6,'Domingo')])
    start_time=models.TimeField('Inicio')
    end_time=models.TimeField('Fin')
    responsible=models.ForeignKey(User,on_delete=models.PROTECT,verbose_name='Responsable')
    active=models.BooleanField('Activo',default=True)
    def __str__(self): return f'{self.department} · {self.name} · {self.get_weekday_display()}'

class ScheduledReport(Record):
    name=models.CharField('Informe programado',max_length=140)
    kind=models.CharField('Informe',max_length=30,choices=[('hos','Jornadas/HOS'),('dvir','DVIR'),('maintenance','Mantenimiento'),('fuel','Combustible'),('drivers','Conductores'),('costs','Costos de flota'),('fleet','Estado de flota'),('inspections','Inspecciones'),('compliance','Cumplimiento'),('inventory','Inventario'),('tires','Neumáticos')])
    interval_days=models.PositiveIntegerField('Repetir cada (días)',default=7,validators=[MinValueValidator(1)])
    next_run=models.DateTimeField('Próxima generación')
    active=models.BooleanField('Activo',default=True)
    created_by=models.ForeignKey(User,on_delete=models.PROTECT,editable=False)
    def __str__(self): return self.name
    class Meta(Record.Meta):
        constraints=[models.CheckConstraint(condition=models.Q(interval_days__gte=1),name='cmms_report_interval_positive')]

class ReportRun(Record):
    schedule=models.ForeignKey(ScheduledReport,on_delete=models.PROTECT)
    scheduled_at=models.DateTimeField('Fecha programada')
    file=models.FileField('PDF',upload_to='informes/%Y/%m/')
    records=models.PositiveIntegerField('Registros incluidos',default=0)
    def __str__(self): return str(self.schedule)
    class Meta(Record.Meta):
        constraints=[models.UniqueConstraint(fields=['schedule','scheduled_at'],name='cmms_unique_report_run')]

class CatalogImport(Record):
    module=models.CharField(max_length=40)
    digest=models.CharField(max_length=64,editable=False)
    filename=models.CharField(max_length=180)
    records=models.PositiveIntegerField()
    actor=models.ForeignKey(User,on_delete=models.PROTECT)
    class Meta(Record.Meta):
        constraints=[models.UniqueConstraint(fields=['organization','module','digest'],name='cmms_unique_catalog_import')]
