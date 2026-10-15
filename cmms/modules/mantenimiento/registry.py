from cmms.module import Module, MANAGERS, ALL
from cmms import models as m

MODULES=[
Module('solicitudes','Solicitudes de mantenimiento','Solicitud','Mantenimiento',m.MaintenanceRequest,('bus','title','description','priority'),(('id','N.º'),('bus','Bus'),('title','Problema'),('priority','Prioridad'),('status','Estado')),create=ALL,edit=(),search=('title','description')),
Module('ordenes','Órdenes de trabajo','Orden de trabajo','Mantenimiento',m.WorkOrder,('bus','title','description','kind','priority','assigned_to','due_date','labor_cost','resolution'),(('id','OT'),('bus','Bus'),('title','Trabajo'),('assigned_to','Responsable'),('status','Estado'),('due_date','Compromiso')),edit=MANAGERS+('tecnico',)),
Module('preventivos','Mantenimiento preventivo','Plan preventivo','Mantenimiento',m.PreventivePlan,('bus','title','program','tasks','next_date','next_km','interval_days','interval_km','active'),(('bus','Bus'),('title','Servicio'),('next_date','Próxima fecha'),('next_km','Próximo km'),('overdue','Vencido'),('active','Activo'))),
Module('programas','Programas de servicio','Programa','Mantenimiento',m.ServiceProgram,('name','tasks','interval_days','interval_km','active'),(('name','Programa'),('interval_days','Días'),('interval_km','Kilómetros'),('active','Activo')),read=MANAGERS+('tecnico',),search=('name','tasks'))
]
for item in MODULES:
    item.section='Mantenimiento'
MODULES[2].fields=MODULES[2].fields+('next_hours','interval_hours')
MODULES[1].fields+=('reported_by','program','failure_category','estimated_hours','location','budget','billing_mode','worked_hours','labor_rate','external_cost','remarks')
MODULES[3].fields+=('task_templates','interval_hours')
MODULES.extend([
    Module('biblioteca_tareas','Biblioteca de tareas','Tarea estándar','Mantenimiento',m.ServiceTask,('name','instructions','estimated_hours','active'),(('name','Tarea'),('estimated_hours','Duración h'),('active','Activa')),read=MANAGERS+('tecnico',),search=('name','instructions')),
    Module('tareas_ot','Tareas de órdenes de trabajo','Tarea de OT','Mantenimiento',m.WorkOrderTask,('work_order','template','title','status','spent_hours','completion_notes'),(('work_order','OT'),('title','Tarea'),('status','Estado'),('spent_hours','Horas')),read=MANAGERS+('tecnico',),create=MANAGERS+('tecnico',),edit=MANAGERS+('tecnico',),search=('title','completion_notes')),
])
MODULES.append(Module('comentarios_ot','Comentarios de OT','Comentario','Mantenimiento',m.WorkOrderComment,('work_order','text'),(('work_order','OT'),('text','Comentario'),('author','Autor'),('created_at','Fecha')),read=MANAGERS+('tecnico',),create=MANAGERS+('tecnico',),edit=(),search=('text',)))
MODULES[0].fields+=('failure_type',)
MODULES[1].fields+=('failure_type',)
MODULES.append(Module('tipos_falla','Tipos de falla y síntomas','Tipo de falla','Mantenimiento',m.FailureType,('code','name','system','description','active'),(('code','Código'),('name','Falla / síntoma'),('system','Sistema'),('active','Activo')),read=ALL,search=('code','name','description')))
