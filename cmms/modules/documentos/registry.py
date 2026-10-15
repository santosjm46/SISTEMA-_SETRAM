from cmms.module import Module, MANAGERS, ALL
from cmms import models as m

MODULES=[
Module('documentos','Documentos y vencimientos','Documento','Operación',m.Document,('bus','title','kind','expiry','file','notes'),(('title','Documento'),('bus','Bus'),('kind','Tipo'),('expiry','Vencimiento')),search=('title','notes'))
]
for item in MODULES:
    item.section='Documentos'
MODULES[0].fields+=('user','work_order')
MODULES.extend([
    Module('auditor_documental','Auditor documental / IA','Análisis','Documentos',m.DocumentAnalysis,(),(('document','Documento'),('state','Estado'),('analyzed_at','Analizado')),read=MANAGERS+('tecnico',),create=(),edit=(),search=('state',),route='documents:auditor'),
    Module('camaras','Cámaras y fuentes de video','Cámara','Documentos',m.Camera,('name','department','bus','stream_url','stream_type','active','notes'),(('name','Cámara'),('department','Patio'),('active','Activa')),read=MANAGERS,search=('name','notes')),
    Module('vision','Visión en vivo','Observación','Documentos',m.CameraObservation,('camera','bus','observed_at','title','notes','risk'),(('camera','Cámara'),('bus','Bus'),('title','Observación'),('risk','Nivel')),read=MANAGERS,create=MANAGERS,edit=(),search=('title','notes'),route='documents:vision'),
])
MODULES.extend([
    Module('capturas_vision','Capturas de la fuente de visión','Captura','Documentos',m.VisionFrame,(),(('camera','Cámara'),('measured_at','Captura'),('model_version','Motor')),read=MANAGERS,create=(),edit=(),search=('camera__name','model_version')),
    Module('detecciones','Detecciones y revisión','Detección','Documentos',m.VisionDetection,('status','review_notes'),(('frame','Captura'),('label','Objeto'),('plate','Placa'),('confidence','Confianza %'),('status','Revisión')),read=MANAGERS,create=(),edit=MANAGERS,search=('label','plate')),
])
