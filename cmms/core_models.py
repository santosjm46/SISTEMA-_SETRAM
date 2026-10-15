from decimal import Decimal
from datetime import timedelta
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, FileExtensionValidator, MaxValueValidator
from django.db import models
from django.utils import timezone

POSITIVE = [MinValueValidator(0)]
PRIORITY = [('baja','Baja'),('media','Media'),('alta','Alta'),('critica','Crítica')]
FAILURE_SYSTEMS = [('motor','Motor'),('frenos','Frenos'),('electrico','Eléctrico'),('suspension','Suspensión'),('transmision','Transmisión'),('neumaticos','Neumáticos'),('carroceria','Carrocería / puertas'),('otro','Otro')]


class Organization(models.Model):
    name = models.CharField('Nombre',max_length=120,default='SETRAM')
    currency = models.CharField('Moneda',max_length=3,default='BOB')
    timezone = models.CharField('Zona horaria',max_length=64,default='America/La_Paz')
    enabled_modules = models.JSONField('Módulos habilitados',default=dict,blank=True)
    tax_id=models.CharField('NIT de la institución',max_length=30,blank=True)
    address=models.CharField('Dirección',max_length=240,blank=True)
    contact_email=models.EmailField('Correo de contacto',blank=True)
    phone=models.CharField('Teléfono institucional',max_length=40,blank=True)
    default_labor_rate=models.DecimalField('Tarifa de mano de obra (Bs/h)',max_digits=10,decimal_places=2,default=0,validators=POSITIVE)
    notifications_enabled=models.BooleanField('Notificaciones internas',default=True)
    notification_matrix=models.JSONField('Tipos de aviso por rol',default=dict,blank=True)
    kpi_alerts_enabled=models.BooleanField('Alertas de indicadores',default=False)
    minimum_availability=models.PositiveIntegerField('Disponibilidad mínima (%)',default=85,validators=[MaxValueValidator(100)])
    minimum_inspection_approval=models.PositiveIntegerField('Aprobación mínima de inspecciones (%)',default=90,validators=[MaxValueValidator(100)])
    minimum_tread_mm=models.DecimalField('Umbral interno de profundidad de neumáticos (mm)',max_digits=5,decimal_places=2,default=6,validators=POSITIVE)
    class Meta:
        db_table = 'cmms_organization'
    def __str__(self): return self.name


class User(AbstractUser):
    ROLES = [('administrador','Administrador'),('supervisor','Supervisor'),('tecnico','Técnico'),('conductor','Conductor')]
    organization = models.ForeignKey(Organization,on_delete=models.PROTECT,null=True,blank=True)
    role = models.CharField('Rol',max_length=20,choices=ROLES,default='tecnico')
    phone = models.CharField('Teléfono',max_length=30,blank=True)
    employee_code=models.CharField('Código de funcionario',max_length=40,blank=True)
    department=models.ForeignKey('cmms.Department',on_delete=models.PROTECT,null=True,blank=True,verbose_name='Patio / departamento')
    license_number=models.CharField('Licencia de conducción',max_length=80,blank=True)
    license_category=models.CharField('Categoría de licencia',max_length=30,blank=True)
    license_expiry=models.DateField('Vencimiento de licencia',null=True,blank=True)
    dashboard_widgets=models.JSONField('Preferencias del panel',default=list,blank=True)
    def clean(self):
        super().clean()
        if self.department_id and self.department.organization_id!=self.organization_id: raise ValidationError({'department':'El patio debe pertenecer a tu organización.'})
    class Meta:
        db_table = 'cmms_user'
    def __str__(self): return self.get_full_name() or self.username


class Record(models.Model):
    organization = models.ForeignKey(Organization,on_delete=models.PROTECT)
    created_at = models.DateTimeField('Fecha de registro',auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True
        ordering = ['-created_at']
    def clean(self):
        super().clean()
        for field in self._meta.fields:
            if isinstance(field, models.ForeignKey) and field.name != 'organization' and getattr(self,field.attname,None):
                related = getattr(self,field.name)
                if hasattr(related,'organization_id') and related.organization_id != self.organization_id:
                    raise ValidationError({field.name:'El registro debe pertenecer a la misma organización.'})


class Department(Record):
    name = models.CharField('Nombre',max_length=100)
    location = models.CharField('Ubicación',max_length=180,blank=True)
    active=models.BooleanField('Activo',default=True)
    def __str__(self): return self.name
    class Meta(Record.Meta):
        constraints = [models.UniqueConstraint(fields=['organization','name'],name='cmms_unique_department')]


class Bus(Record):
    code = models.CharField('Número interno',max_length=30)
    plate = models.CharField('Placa',max_length=20)
    brand = models.CharField('Marca',max_length=60)
    model = models.CharField('Modelo',max_length=60)
    year = models.PositiveIntegerField('Año',validators=[MinValueValidator(1980),MaxValueValidator(2100)])
    capacity = models.PositiveIntegerField('Capacidad de pasajeros',default=0)
    odometer = models.DecimalField('Odómetro (km)',max_digits=12,decimal_places=1,default=0,validators=POSITIVE)
    engine_hours = models.DecimalField('Horas de motor',max_digits=12,decimal_places=1,null=True,blank=True,validators=POSITIVE)
    status = models.CharField('Estado',max_length=20,choices=[('operativo','Operativo'),('taller','En taller'),('inmovilizado','Inmovilizado'),('baja','Baja')],default='operativo')
    route = models.CharField('Ruta / servicio',max_length=100,blank=True)
    fuel_type = models.CharField('Energía',max_length=20,choices=[('diesel','Diésel'),('gnv','GNV'),('electrico','Eléctrico')],default='diesel')
    department = models.ForeignKey(Department,on_delete=models.PROTECT,null=True,blank=True,verbose_name='Patio / departamento')
    driver = models.ForeignKey(User,on_delete=models.PROTECT,null=True,blank=True,verbose_name='Conductor',related_name='assigned_buses')
    notes = models.TextField('Observaciones',blank=True)
    vin=models.CharField('VIN / número de chasis',max_length=17,blank=True)
    registration_expiry=models.DateField('Vencimiento de registro',null=True,blank=True)
    insurance_expiry=models.DateField('Vencimiento de seguro',null=True,blank=True)
    service_date=models.DateField('Ingreso al servicio',null=True,blank=True)
    design_life_years=models.PositiveIntegerField('Vida útil de referencia (años)',null=True,blank=True,validators=[MinValueValidator(1),MaxValueValidator(50)])
    def __str__(self): return f'{self.code} · {self.plate}'
    def clean(self):
        super().clean()
        if self.vin:
            import re
            self.vin=self.vin.strip().upper()
            if not re.fullmatch(r'[A-HJ-NPR-Z0-9]{17}',self.vin): raise ValidationError({'vin':'El VIN tiene 17 caracteres; no utiliza I, O ni Q.'})
        if self.driver_id and self.driver.role != 'conductor':
            raise ValidationError({'driver':'Selecciona un usuario con rol Conductor.'})
        if self.pk:
            previous = Bus.objects.filter(pk=self.pk).first()
            if previous and self.odometer < previous.odometer:
                raise ValidationError({'odometer':'El odómetro no puede retroceder.'})
            if previous and previous.engine_hours is not None and (self.engine_hours is None or self.engine_hours < previous.engine_hours):
                raise ValidationError({'engine_hours':'Las horas de motor no pueden retroceder.'})
            if self.status == 'operativo' and self.inspection_set.filter(result='critico',resolved=False).exists():
                raise ValidationError({'status':'Hay una inspección crítica sin resolver.'})
            if self.status=='operativo' and self.safetyincident_set.filter(severity='critica').exclude(status='resuelto').exists():
                raise ValidationError({'status':'Hay un incidente crítico sin resolver.'})
    class Meta(Record.Meta):
        constraints = [models.UniqueConstraint(fields=['organization','code'],name='cmms_unique_bus_code'),models.UniqueConstraint(fields=['organization','plate'],name='cmms_unique_bus_plate'),models.CheckConstraint(condition=models.Q(odometer__gte=0),name='cmms_bus_positive_odometer')]


class MaintenanceRequest(Record):
    bus = models.ForeignKey(Bus,on_delete=models.PROTECT,verbose_name='Bus')
    title = models.CharField('Problema reportado',max_length=180)
    description = models.TextField('Descripción')
    failure_type=models.ForeignKey('cmms.FailureType',on_delete=models.PROTECT,null=True,blank=True,verbose_name='Tipo de falla / síntoma')
    priority = models.CharField('Prioridad',max_length=10,choices=PRIORITY,default='media')
    status = models.CharField('Estado',max_length=20,choices=[('pendiente','Pendiente'),('en_revision','En revisión'),('convertida','OT creada'),('rechazada','Rechazada')],default='pendiente')
    review_notes=models.TextField('Revisión / motivo de rechazo',blank=True)
    reported_by = models.ForeignKey(User,on_delete=models.PROTECT,verbose_name='Reportado por')
    def __str__(self): return self.title


class WorkOrder(Record):
    bus = models.ForeignKey(Bus,on_delete=models.PROTECT,verbose_name='Bus')
    title = models.CharField('Trabajo a realizar',max_length=180)
    description = models.TextField('Detalle / diagnóstico')
    kind = models.CharField('Tipo',max_length=20,choices=[('correctivo','Correctivo'),('preventivo','Preventivo')],default='correctivo')
    priority = models.CharField('Prioridad',max_length=10,choices=PRIORITY,default='media')
    status = models.CharField('Estado',max_length=20,choices=[('abierta','Abierta'),('en_progreso','En ejecución'),('revision','En revisión'),('cerrada','Cerrada')],default='abierta')
    assigned_to = models.ForeignKey(User,on_delete=models.PROTECT,null=True,blank=True,related_name='work_orders',verbose_name='Responsable')
    due_date = models.DateField('Fecha comprometida',null=True,blank=True)
    labor_cost = models.DecimalField('Mano de obra (Bs)',max_digits=12,decimal_places=2,default=0,validators=POSITIVE)
    resolution = models.TextField('Trabajo realizado / evidencia de resolución',blank=True)
    source_request = models.OneToOneField(MaintenanceRequest,on_delete=models.PROTECT,null=True,blank=True,verbose_name='Solicitud origen')
    completed_at = models.DateTimeField(null=True,blank=True)
    reported_by=models.ForeignKey(User,on_delete=models.PROTECT,null=True,blank=True,related_name='reported_orders',verbose_name='Reportado por')
    program=models.ForeignKey('cmms.ServiceProgram',on_delete=models.PROTECT,null=True,blank=True,verbose_name='Plantilla de servicio')
    budget=models.ForeignKey('cmms.Budget',on_delete=models.PROTECT,null=True,blank=True,verbose_name='Presupuesto')
    failure_category=models.CharField('Sistema afectado',max_length=30,choices=FAILURE_SYSTEMS,blank=True)
    failure_type=models.ForeignKey('cmms.FailureType',on_delete=models.PROTECT,null=True,blank=True,verbose_name='Tipo de falla / síntoma')
    estimated_hours=models.DecimalField('Duración estimada (h)',max_digits=8,decimal_places=2,default=0,blank=True,validators=POSITIVE)
    worked_hours=models.DecimalField('Horas de mano de obra',max_digits=8,decimal_places=2,default=0,blank=True,validators=POSITIVE)
    labor_rate=models.DecimalField('Tarifa (Bs/h)',max_digits=10,decimal_places=2,null=True,blank=True,validators=POSITIVE)
    billing_mode=models.CharField('Cálculo de mano de obra',max_length=20,choices=[('manual','Importe manual'),('por_hora','Horas × tarifa')],default='manual',blank=True)
    external_cost=models.DecimalField('Servicios externos (Bs)',max_digits=12,decimal_places=2,default=0,blank=True,validators=POSITIVE)
    location=models.CharField('Taller / lugar de intervención',max_length=160,blank=True)
    remarks=models.TextField('Notas adicionales',blank=True)
    started_at=models.DateTimeField('Inicio real',null=True,blank=True,editable=False)
    def __str__(self): return f'OT-{self.pk or "NUEVA":} · {self.title}'
    @property
    def parts_cost(self):
        return sum((m.quantity * m.unit_cost for m in self.stockmovement_set.filter(kind='salida')),Decimal('0'))
    @property
    def total_cost(self): return self.labor_cost + self.parts_cost + self.external_cost
    def clean(self):
        super().clean()
        if self.failure_type_id:self.failure_category=self.failure_type.system
        if self.billing_mode=='por_hora':
            if self.labor_rate is None: self.labor_rate=self.organization.default_labor_rate
            self.labor_cost=(self.worked_hours or Decimal(0))*self.labor_rate
        if self.assigned_to_id and self.assigned_to.role not in ('tecnico','supervisor','administrador'):
            raise ValidationError({'assigned_to':'El responsable debe ser técnico, supervisor o administrador.'})


class Checklist(Record):
    name = models.CharField('Nombre de plantilla',max_length=120)
    items = models.TextField('Puntos de inspección (uno por línea)',help_text='Las nuevas inspecciones guardan una copia de esta versión.')
    version = models.PositiveIntegerField('Versión',default=1)
    active = models.BooleanField('Activa',default=True)
    def __str__(self): return f'{self.name} · v{self.version}'


class Inspection(Record):
    bus = models.ForeignKey(Bus,on_delete=models.PROTECT,verbose_name='Bus')
    inspector = models.ForeignKey(User,on_delete=models.PROTECT,verbose_name='Inspector')
    kind = models.CharField('Tipo',max_length=20,choices=[('preoperacional','Preoperacional'),('postoperacional','Postoperacional'),('taller','Taller')],default='preoperacional')
    date = models.DateTimeField('Fecha y hora',default=timezone.now)
    odometer = models.DecimalField('Odómetro (km)',max_digits=12,decimal_places=1,validators=POSITIVE)
    result = models.CharField('Resultado',max_length=20,choices=[('aprobado','Aprobado'),('defecto','Defectos menores'),('critico','Defecto crítico')],default='aprobado')
    checklist = models.ForeignKey(Checklist,on_delete=models.PROTECT,verbose_name='Plantilla')
    snapshot = models.JSONField(default=dict,editable=False)
    findings = models.TextField('Hallazgos / defectos',blank=True)
    signature = models.CharField('Firma (nombre del inspector)',max_length=150)
    resolved = models.BooleanField(default=False,editable=False)
    work_order = models.OneToOneField(WorkOrder,on_delete=models.PROTECT,null=True,blank=True,editable=False)
    location=models.CharField('Lugar de inspección',max_length=180,blank=True)
    def __str__(self): return f'INS-{self.pk or "NUEVA"} · {self.bus}'
    def clean(self):
        super().clean()
        if self.result != 'aprobado' and not self.findings.strip():
            raise ValidationError({'findings':'Describe los defectos encontrados.'})
        if self.date > timezone.now() + timedelta(minutes=5):
            raise ValidationError({'date':'No se pueden registrar inspecciones futuras.'})
        if self.bus_id and self.odometer < self.bus.odometer:
            raise ValidationError({'odometer':'La lectura no puede ser menor al odómetro del bus.'})


class ServiceProgram(Record):
    name = models.CharField('Programa / servicio',max_length=160)
    tasks = models.TextField('Tareas estándar (una por línea)')
    interval_days = models.PositiveIntegerField('Intervalo sugerido (días)',default=0)
    interval_km = models.PositiveIntegerField('Intervalo sugerido (km)',default=0)
    active = models.BooleanField('Activo',default=True)
    task_templates=models.ManyToManyField('cmms.ServiceTask',blank=True,verbose_name='Tareas de la biblioteca')
    interval_hours=models.PositiveIntegerField('Intervalo sugerido (horas)',default=0,blank=True)
    catalog_source=models.CharField('Origen del catálogo',max_length=240,blank=True,editable=False)
    def __str__(self): return self.name


class PreventivePlan(Record):
    bus = models.ForeignKey(Bus,on_delete=models.PROTECT,verbose_name='Bus')
    title = models.CharField('Servicio',max_length=160)
    tasks = models.TextField('Tareas / alcance',blank=True)
    program = models.ForeignKey(ServiceProgram,on_delete=models.PROTECT,null=True,blank=True,verbose_name='Programa de servicio')
    next_date = models.DateField('Próxima fecha',null=True,blank=True)
    next_km = models.DecimalField('Próximo odómetro (km)',max_digits=12,decimal_places=1,null=True,blank=True,validators=POSITIVE)
    next_hours = models.DecimalField('Próximas horas de motor',max_digits=12,decimal_places=1,null=True,blank=True,validators=POSITIVE)
    interval_days = models.PositiveIntegerField('Intervalo (días)',default=0)
    interval_km = models.PositiveIntegerField('Intervalo (km)',default=0)
    interval_hours = models.PositiveIntegerField('Intervalo (horas de motor)',default=0)
    active = models.BooleanField('Activo',default=True)
    def __str__(self): return self.title
    @property
    def overdue(self):
        return bool(self.active and ((self.next_date and self.next_date<=timezone.localdate()) or
            (self.next_km is not None and self.bus.odometer>=self.next_km) or
            (self.next_hours is not None and self.bus.engine_hours is not None and self.bus.engine_hours>=self.next_hours)))
    def clean(self):
        super().clean()
        if not self.tasks.strip():
            raise ValidationError({'tasks':'Indica las tareas o selecciona un programa de servicio.'})
        if not self.next_date and self.next_km is None and self.next_hours is None:
            raise ValidationError('Indica fecha, kilometraje u horas de motor.')
        if self.next_date and not self.interval_days:
            raise ValidationError({'interval_days':'Define un intervalo mayor a cero.'})
        if self.next_km is not None and not self.interval_km:
            raise ValidationError({'interval_km':'Define un intervalo mayor a cero.'})
        if self.next_hours is not None and not self.interval_hours:
            raise ValidationError({'interval_hours':'Define un intervalo mayor a cero.'})


class PreventiveExecution(Record):
    plan = models.ForeignKey(PreventivePlan,on_delete=models.PROTECT)
    work_order = models.OneToOneField(WorkOrder,on_delete=models.PROTECT)
    next_date_before = models.DateField(null=True)
    next_km_before = models.DecimalField(max_digits=12,decimal_places=1,null=True)
    completed_at = models.DateTimeField(null=True)


class Supplier(Record):
    name = models.CharField('Proveedor',max_length=140)
    tax_id = models.CharField('NIT',max_length=30,blank=True)
    contact = models.CharField('Contacto',max_length=140,blank=True)
    phone = models.CharField('Teléfono',max_length=30,blank=True)
    email = models.EmailField('Correo',blank=True)
    active=models.BooleanField('Activo',default=True)
    lead_time_days=models.PositiveIntegerField('Plazo de entrega (días)',default=0,blank=True)
    address=models.CharField('Dirección',max_length=220,blank=True)
    payment_terms=models.CharField('Condiciones de pago',max_length=160,blank=True)
    def __str__(self): return self.name


class Part(Record):
    code = models.CharField('Código',max_length=40)
    name = models.CharField('Repuesto',max_length=140)
    unit = models.CharField('Unidad',max_length=30,default='unidad')
    quantity = models.DecimalField('Existencias',max_digits=12,decimal_places=2,default=0,editable=False)
    minimum = models.DecimalField('Existencia mínima',max_digits=12,decimal_places=2,default=0,validators=POSITIVE)
    unit_cost = models.DecimalField('Costo referencial (Bs)',max_digits=12,decimal_places=2,default=0,validators=POSITIVE)
    supplier = models.ForeignKey(Supplier,on_delete=models.PROTECT,null=True,blank=True,verbose_name='Proveedor')
    category=models.CharField('Categoría',max_length=80,blank=True)
    manufacturer=models.CharField('Fabricante',max_length=100,blank=True)
    storage_location=models.CharField('Ubicación en almacén',max_length=100,blank=True)
    auto_demand=models.BooleanField('Generar demanda al bajar del mínimo',default=False)
    application_notes=models.TextField('Especificación / compatibilidad pendiente',blank=True)
    catalog_source=models.CharField('Origen del catálogo',max_length=240,blank=True,editable=False)
    def __str__(self): return f'{self.code} · {self.name}'
    class Meta(Record.Meta):
        constraints = [models.UniqueConstraint(fields=['organization','code'],name='cmms_unique_part'),models.CheckConstraint(condition=models.Q(quantity__gte=0),name='cmms_part_nonnegative_stock')]


class StockMovement(Record):
    part = models.ForeignKey(Part,on_delete=models.PROTECT,verbose_name='Repuesto')
    kind = models.CharField('Movimiento',max_length=10,choices=[('entrada','Entrada'),('salida','Salida')])
    quantity = models.DecimalField('Cantidad',max_digits=12,decimal_places=2,validators=[MinValueValidator(Decimal('0.01'))])
    unit_cost = models.DecimalField('Costo unitario (Bs)',max_digits=12,decimal_places=2,validators=POSITIVE)
    work_order = models.ForeignKey(WorkOrder,on_delete=models.PROTECT,null=True,blank=True,verbose_name='Orden de trabajo')
    reference = models.CharField('Referencia / motivo',max_length=180)
    actor = models.ForeignKey(User,on_delete=models.PROTECT)
    def __str__(self): return f'{self.get_kind_display()} · {self.part}'
    def clean(self):
        super().clean()
        if self.kind == 'salida' and not self.work_order_id:
            raise ValidationError({'work_order':'Las salidas deben estar asociadas a una OT.'})
        if self.work_order_id and self.work_order.status == 'cerrada':
            raise ValidationError({'work_order':'No se pueden imputar repuestos a una OT cerrada.'})
    class Meta(Record.Meta):
        constraints=[models.CheckConstraint(condition=models.Q(quantity__gt=0),name='cmms_movement_positive')]


class PurchaseOrder(Record):
    supplier = models.ForeignKey(Supplier,on_delete=models.PROTECT,verbose_name='Proveedor')
    part = models.ForeignKey(Part,on_delete=models.PROTECT,verbose_name='Repuesto')
    quantity = models.DecimalField('Cantidad a comprar',max_digits=12,decimal_places=2,validators=[MinValueValidator(Decimal('0.01'))])
    unit_cost = models.DecimalField('Costo unitario (Bs)',max_digits=12,decimal_places=2,validators=POSITIVE)
    expected_date = models.DateField('Fecha esperada',null=True,blank=True)
    status = models.CharField('Estado',max_length=20,choices=[('pedido','Pedido'),('parcial','Recepción parcial'),('recibido','Recibido')],default='pedido')
    received_quantity=models.DecimalField('Recibido de la primera línea',max_digits=12,decimal_places=2,default=0,editable=False)
    reference = models.CharField('Referencia / cotización',max_length=180)
    received_at = models.DateTimeField(null=True,blank=True)
    receipt = models.OneToOneField(StockMovement,on_delete=models.PROTECT,null=True,blank=True,editable=False)
    def __str__(self): return f'OC-{self.pk or "NUEVA"} · {self.part}'
    @property
    def total(self): return self.quantity*self.unit_cost+sum((line.quantity*line.unit_cost for line in self.purchaseline_set.all()),Decimal(0)) if self.pk else self.quantity*self.unit_cost


class FuelEntry(Record):
    bus = models.ForeignKey(Bus,on_delete=models.PROTECT,verbose_name='Bus')
    date = models.DateField('Fecha',default=timezone.localdate)
    odometer = models.DecimalField('Odómetro (km)',max_digits=12,decimal_places=1,validators=POSITIVE)
    liters = models.DecimalField('Litros',max_digits=10,decimal_places=2,validators=[MinValueValidator(Decimal('0.01'))])
    cost = models.DecimalField('Importe (Bs)',max_digits=12,decimal_places=2,validators=POSITIVE)
    reference = models.CharField('Factura / comprobante',max_length=100)
    driver = models.ForeignKey(User,on_delete=models.PROTECT,verbose_name='Registrado por')
    station=models.CharField('Estación / surtidor',max_length=140,blank=True)
    full_tank=models.BooleanField('Carga a tanque lleno',default=False)
    verification=models.CharField('Conciliación',max_length=20,choices=[('pendiente','Pendiente'),('verificado','Verificado'),('observado','Observado')],default='pendiente',editable=False)
    verification_notes=models.TextField('Notas de conciliación',blank=True,editable=False)
    def __str__(self): return f'{self.bus} · {self.date}'
    def clean(self):
        super().clean()
        if self.date > timezone.localdate():
            raise ValidationError({'date':'La fecha no puede ser futura.'})
        if self.bus_id and self.bus.fuel_type != 'diesel':
            raise ValidationError({'bus':'Este registro en litros es para buses diésel. GNV y energía eléctrica requieren unidades específicas.'})


class Document(Record):
    bus = models.ForeignKey(Bus,on_delete=models.PROTECT,null=True,blank=True,verbose_name='Bus')
    title = models.CharField('Documento',max_length=180)
    kind = models.CharField('Tipo',max_length=30,choices=[('seguro','Seguro'),('inspeccion','Inspección técnica'),('registro','Registro'),('manual','Manual'),('otro','Otro')])
    expiry = models.DateField('Vencimiento',null=True,blank=True)
    file = models.FileField('Archivo',upload_to='documentos/%Y/%m/',validators=[FileExtensionValidator(['pdf','png','jpg','jpeg'])])
    notes = models.TextField('Observaciones',blank=True)
    user=models.ForeignKey(User,on_delete=models.PROTECT,null=True,blank=True,verbose_name='Persona / conductor')
    work_order=models.ForeignKey(WorkOrder,on_delete=models.PROTECT,null=True,blank=True,verbose_name='Orden de trabajo')
    def __str__(self): return self.title
    def clean(self):
        super().clean()
        if self.file and self.file.size > 10 * 1024 * 1024:
            raise ValidationError({'file':'Máximo 10 MB.'})
        if self.file:
            header=self.file.read(8)
            self.file.seek(0)
            extension=self.file.name.rsplit('.',1)[-1].lower()
            valid=(extension == 'pdf' and header.startswith(b'%PDF-')) or (extension == 'png' and header.startswith(b'\x89PNG\r\n\x1a\n')) or (extension in ('jpg','jpeg') and header.startswith(b'\xff\xd8\xff'))
            if not valid:
                raise ValidationError({'file':'El contenido no corresponde a un PDF, PNG o JPEG válido.'})


class Tire(Record):
    serial = models.CharField('Número de serie',max_length=80)
    bus = models.ForeignKey(Bus,on_delete=models.PROTECT,null=True,blank=True,verbose_name='Bus')
    position = models.CharField('Posición',max_length=60,blank=True)
    brand = models.CharField('Marca',max_length=60)
    tread_mm = models.DecimalField('Profundidad (mm)',max_digits=5,decimal_places=2,validators=POSITIVE)
    status = models.CharField('Estado',max_length=20,choices=[('montado','Montado'),('almacen','En almacén'),('reencauche','Reencauche'),('baja','Baja')],default='almacen')
    cost = models.DecimalField('Costo (Bs)',max_digits=12,decimal_places=2,default=0,validators=POSITIVE)
    size=models.CharField('Medida',max_length=60,blank=True)
    installed_at=models.DateField('Fecha de montaje',null=True,blank=True)
    installed_km=models.DecimalField('Odómetro al montaje (km)',max_digits=12,decimal_places=1,null=True,blank=True,validators=POSITIVE)
    original_tread_mm=models.DecimalField('Profundidad inicial (mm)',max_digits=5,decimal_places=2,null=True,blank=True,validators=POSITIVE)
    retread_count=models.PositiveIntegerField('Reencauches realizados',default=0,blank=True)
    def __str__(self): return self.serial
    def clean(self):
        super().clean()
        if self.status == 'montado' and (not self.bus_id or not self.position.strip()):
            raise ValidationError('Un neumático montado necesita bus y posición.')
    class Meta(Record.Meta):
        constraints=[models.UniqueConstraint(fields=['organization','serial'],name='cmms_unique_tire')]


class AuditEvent(Record):
    actor = models.ForeignKey(User,on_delete=models.PROTECT)
    action = models.CharField(max_length=80)
    entity = models.CharField(max_length=80)
    object_id = models.CharField(max_length=40)
    changes = models.JSONField(default=dict)
    def __str__(self): return f'{self.action} · {self.entity} {self.object_id}'


class Submission(models.Model):
    token = models.UUIDField(unique=True)
    actor = models.ForeignKey(User,on_delete=models.PROTECT)
    module = models.CharField(max_length=40)
    object_id = models.PositiveBigIntegerField()
