from cmms.module import Module, MANAGERS, ALL
from cmms import models as m

MODULES=[
Module('combustible','Combustible','Carga de combustible','Recursos',m.FuelEntry,('bus','date','odometer','liters','cost','reference'),(('bus','Bus'),('date','Fecha'),('liters','Litros'),('cost','Importe Bs'),('odometer','Kilómetros')),create=MANAGERS+('conductor',),edit=(),search=('reference',))
]
for item in MODULES:
    item.section='Operacion'
MODULES[0].fields+=('station','full_tank')
MODULES.extend([
    Module('rutas','Rutas y servicios','Ruta','Operación',m.ServiceRoute,('code','name','origin','destination','active'),(('code','Código'),('name','Ruta'),('origin','Origen'),('destination','Destino')),search=('code','name')),
    Module('jornadas','HOS / Jornadas de conducción','Jornada','Operación',m.ShiftLog,('bus','driver','started_at','ended_at','break_minutes','notes'),(('driver','Conductor'),('bus','Bus'),('started_at','Inicio'),('ended_at','Fin'),('driving_hours','Conducción h')),create=MANAGERS+('conductor',),edit=(),search=('notes',),route='operation:hos'),
    Module('recorridos','Libro de registro / Recorridos','Recorrido','Operación',m.TripLog,('bus','driver','route','started_at','ended_at','start_km','end_km','passengers','status','notes'),(('bus','Bus'),('driver','Conductor'),('route','Ruta'),('status','Estado'),('distance','Km')),create=MANAGERS+('conductor',),edit=MANAGERS+('conductor',),search=('notes',)),
    Module('politicas','Políticas de operación','Política','Operación',m.OperatingPolicy,('name','daily_driving_hours','active','notes'),(('name','Política'),('daily_driving_hours','Umbral h'),('active','Activa')),read=MANAGERS,search=('name','notes')),
])
