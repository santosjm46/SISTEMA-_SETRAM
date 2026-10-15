from cmms.module import Module, MANAGERS, ALL
from cmms import models as m

MODULES=[
Module('buses','Flota de buses','Bus','Operación',m.Bus,('code','plate','brand','model','year','capacity','odometer','status','route','fuel_type','department','driver','notes'),(('code','Bus'),('plate','Placa'),('brand','Marca'),('odometer','Kilómetros'),('status','Estado'),('driver','Conductor')),search=('code','plate','brand','route')),
Module('neumaticos','Neumáticos','Neumático','Recursos',m.Tire,('serial','bus','position','brand','tread_mm','status','cost'),(('serial','Serie'),('bus','Bus'),('position','Posición'),('tread_mm','Profundidad mm'),('status','Estado')),read=MANAGERS+('tecnico',),search=('serial','brand'))
]
for item in MODULES:
    item.section='Gestion de flota'
MODULES[0].fields=MODULES[0].fields+('engine_hours',)
MODULES[0].fields+=('vin','registration_expiry','insurance_expiry','service_date','design_life_years')
MODULES[1].fields+=('size','installed_at','installed_km','original_tread_mm','retread_count')
MODULES.append(Module('fotos_bus','Galería de buses','Foto','Gestión de flota',m.BusPhoto,('bus','caption','image'),(('bus','Bus'),('caption','Descripción'),('created_at','Fecha')),search=('caption',),edit=()))
