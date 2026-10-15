from cmms.module import Module, MANAGERS, ALL
from cmms import models as m
MODULES=[
    Module('cumplimiento','Cumplimiento y vencimientos','Requisito','Seguridad',m.ComplianceRequirement,('title','reference','bus','responsible','due_date','status','evidence'),(('title','Requisito'),('bus','Bus'),('due_date','Vencimiento'),('status','Estado'),('overdue','Vencido')),search=('title','reference'),route='security:index'),
    Module('retiros','Retiros y campañas','Campaña','Seguridad',m.Recall,('reference','manufacturer','bus','description','due_date'),(('reference','Campaña'),('bus','Bus'),('manufacturer','Fabricante'),('status','Estado')),edit=MANAGERS,search=('reference','manufacturer')),
    Module('incidentes','Incidentes de seguridad','Incidente','Seguridad',m.SafetyIncident,('bus','title','description','severity','occurred_at'),(('bus','Bus'),('title','Incidente'),('severity','Severidad'),('status','Estado')),create=ALL,edit=(),search=('title','description')),
]
MODULES[0].fields+=('category','impact')
MODULES[1].fields+=('source_url','campaign_type')
