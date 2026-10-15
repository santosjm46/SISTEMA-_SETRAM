from cmms.module import Module, MANAGERS, ALL
from cmms import models as m

MODULES=[
Module('departamentos','Patios y departamentos','Departamento','Administración',m.Department,('name','location'),(('name','Departamento'),('location','Ubicación')),read=MANAGERS,search=('name','location')),
Module('auditoria','Historial de auditoría','Evento','Administración',m.AuditEvent,(),(('created_at','Fecha'),('actor','Usuario'),('action','Acción'),('entity','Entidad'),('object_id','Registro')),read=MANAGERS,create=(),edit=(),search=('action','entity','object_id'))
]
for item in MODULES:
    item.section='Organizacion'
MODULES.extend([
    Module('comenzar','Comenzar / Configuración inicial','Organización','Inicio',m.Organization,(),(('name','Organización'),),create=(),edit=(),search=('name',),route='portal:start'),
    Module('ejecutivo','Panel ejecutivo','Organización','Inicio',m.Organization,(),(('name','Organización'),),read=MANAGERS,create=(),edit=(),search=('name',),route='portal:executive'),
    Module('pulso_flota','Fleet Pulse / Estado técnico','Bus','Gestión de flota',m.Bus,(),(('code','Bus'),('status','Estado')),create=(),edit=(),search=('code','plate'),route='portal:pulse'),
    Module('organizacion','Detalles de organización','Organización','Organización',m.Organization,(),(('name','Organización'),('currency','Moneda'),('timezone','Zona horaria')),read=MANAGERS,create=(),edit=(),search=('name',),route='administration:organization'),
    Module('visibilidad','Visibilidad de módulos','Organización','Organización',m.Organization,(),(('name','Organización'),),read=('administrador',),create=(),edit=(),search=('name',),route='administration:visibility'),
    Module('facturacion','Facturación y pagos','Comprobante','Organización',m.Invoice,('reference','supplier','budget','document','date','due_date','amount','status','notes'),(('reference','Comprobante'),('supplier','Proveedor'),('amount','Importe Bs'),('status','Estado'),('due_date','Pago')),read=MANAGERS,search=('reference','notes'),route='administration:finance'),
    Module('presupuestos','Presupuesto de mantenimiento','Presupuesto','Organización',m.Budget,('name','year','department','amount','notes'),(('name','Presupuesto'),('year','Gestión'),('amount','Importe Bs')),read=MANAGERS,search=('name','notes')),
    Module('contratos','Contratos y servicios','Contrato','Organización',m.Contract,('reference','supplier','title','start_date','end_date','amount','status','notes'),(('reference','Contrato'),('supplier','Proveedor'),('end_date','Vencimiento'),('amount','Importe Bs'),('status','Estado')),read=MANAGERS,search=('reference','title')),
])
MODULES[0].fields+=('active',)
MODULES.extend([
    Module('turnos_patio','Turnos de patio','Turno','Organización',m.DepartmentShift,('department','name','weekday','start_time','end_time','responsible','active'),(('department','Patio'),('name','Turno'),('weekday','Día'),('start_time','Inicio'),('end_time','Fin')),read=MANAGERS,search=('name',)),
    Module('reportes_programados','Informes programados','Programación','Organización',m.ScheduledReport,('name','kind','interval_days','next_run','active'),(('name','Informe'),('kind','Tipo'),('next_run','Próxima generación'),('active','Activo')),read=MANAGERS,search=('name',)),
    Module('reportes_generados','Informes generados','Informe','Organización',m.ReportRun,(),(('schedule','Informe'),('scheduled_at','Programado'),('records','Registros')),read=MANAGERS,create=(),edit=(),search=('schedule__name',)),
])
