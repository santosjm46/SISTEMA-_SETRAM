from cmms.module import Module, MANAGERS, ALL
from cmms import models as m
MODULES=[
    Module('telemetria','Telemetría y ubicación','Lectura','Telemetría',m.TelemetryReading,('bus','device','measured_at','latitude','longitude','odometer','engine_hours','speed','temperature','fault_code'),(('bus','Bus'),('device','Dispositivo'),('external_event','Evento externo'),('measured_at','Fecha'),('latitude','Latitud'),('longitude','Longitud'),('odometer','Km'),('engine_hours','Motor h'),('speed','Km/h'),('temperature','Refrigerante °C'),('fault_code','Falla')),edit=(),search=('fault_code',),route='telemetry:index'),
    Module('dispositivos','Dispositivos de telemetría','Dispositivo','Telemetría',m.TelemetryDevice,('name','external_id','bus','provider','active'),(('name','Dispositivo'),('bus','Bus'),('provider','Origen'),('active','Activo')),read=MANAGERS,search=('name','external_id')),
    Module('integraciones','Integraciones y API','Integración','Telemetría',m.IntegrationKey,(),(('name','Integración'),('active','Activa'),('last_used','Último uso')),read=('administrador',),create=(),edit=(),search=('name',),route='telemetry:keys'),
]
