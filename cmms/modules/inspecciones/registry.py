from cmms.module import Module, MANAGERS, ALL
from cmms import models as m

MODULES=[
Module('inspecciones','Inspecciones / DVIR','Inspección','Operación',m.Inspection,('bus','kind','date','odometer','checklist','findings','signature'),(('id','N.º'),('bus','Bus'),('date','Fecha'),('result','Resultado'),('resolved','Resuelto')),create=ALL,edit=(),search=('findings','signature')),
Module('plantillas','Listas de verificación','Plantilla','Operación',m.Checklist,('name','items','active'),(('name','Plantilla'),('version','Versión'),('active','Activa')),search=('name','items'))
]
for item in MODULES:
    item.section='Inspecciones'
MODULES[0].label='Registros DVIR'
MODULES.extend([
    Module('informes_inspeccion','Informes de inspección','Inspección técnica','Inspecciones',m.Inspection,('bus','kind','date','odometer','checklist','findings','signature'),(('bus','Bus'),('date','Fecha'),('inspector','Inspector'),('result','Resultado')),create=MANAGERS+('tecnico',),edit=(),search=('findings','signature')),
    Module('recordatorios','Recordatorios de inspección','Recordatorio','Inspecciones',m.InspectionReminder,('title','bus','assigned_to','checklist','next_due','interval_days','active'),(('title','Recordatorio'),('bus','Bus'),('assigned_to','Responsable'),('next_due','Próximo'),('active','Activo'))),
    Module('notificaciones','Notificaciones','Notificación','Inspecciones',m.Notification,(),(('title','Notificación'),('created_at','Fecha'),('read_at','Leída')),create=(),edit=(),search=('title','body'),route='inspections:notifications'),
])
for item in MODULES:
    if item.model is m.Inspection: item.fields+=('location',)
