import hashlib
import secrets
from decimal import Decimal
from django.core.exceptions import ValidationError,PermissionDenied
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from cmms import models as m


def create_key(user,name,scopes=None):
    if user.role!='administrador': raise PermissionDenied
    secret=secrets.token_urlsafe(32)
    obj=m.IntegrationKey.objects.create(organization=user.organization,created_by=user,name=name,
        digest=hashlib.sha256(secret.encode()).hexdigest(),scopes=scopes if scopes is not None else ['telemetria'])
    from cmms.services import audit
    audit(user,'Integración creada',obj,{'nombre':name})
    return obj,f'{obj.public_id}.{secret}'


def authenticate_key(token):
    import uuid
    try:
        prefix,secret=token.split('.',1)
        key=m.IntegrationKey.objects.select_related('created_by','organization').filter(public_id=uuid.UUID(prefix),active=True,created_by__is_active=True,created_by__role='administrador').first()
    except (ValueError,AttributeError): return None
    if not key or key.created_by.organization_id!=key.organization_id or not secrets.compare_digest(key.digest,hashlib.sha256(secret.encode()).hexdigest()): return None
    return key


def _store_readings(organization,records):
    if not isinstance(records,list) or not 1<=len(records)<=200: raise ValidationError('Envía entre 1 y 200 lecturas.')
    for item in records:
        if not isinstance(item,dict) or not isinstance(item.get('device_id'),str): raise ValidationError('Cada lectura necesita un device_id de texto.')
    devices={obj.external_id:obj for obj in m.TelemetryDevice.objects.select_for_update().filter(
        organization=organization,active=True,external_id__in={item['device_id'] for item in records}).order_by('pk')}
    # Un orden fijo evita que dos lotes bloqueen buses distintos en orden inverso.
    list(m.Bus.objects.select_for_update().filter(organization=organization,pk__in={obj.bus_id for obj in devices.values()}).order_by('pk'))
    results=[]
    for item in records:
        if not isinstance(item,dict): raise ValidationError('Cada lectura debe ser un objeto JSON.')
        if not isinstance(item.get('device_id'),str): raise ValidationError('device_id debe ser texto.')
        device=devices.get(item['device_id'])
        if not device: raise ValidationError('Dispositivo no registrado o desactivado.')
        event=item.get('event_id','')
        if not isinstance(event,str) or not event.strip() or len(event)>100: raise ValidationError('Indica event_id de texto de hasta 100 caracteres.')
        # Bloquea el bus para serializar lecturas y reintentos de este dispositivo.
        bus=m.Bus.objects.select_for_update().get(pk=device.bus_id,organization=organization)
        measured=parse_datetime(str(item.get('measured_at','')))
        if not measured or timezone.is_naive(measured): raise ValidationError('measured_at necesita fecha ISO 8601 y zona horaria.')
        values={}
        try:
            for field in ('latitude','longitude','odometer','engine_hours','speed','temperature'):
                values[field]=Decimal(str(item[field])) if item.get(field) is not None else None
                if values[field] is not None and not values[field].is_finite(): raise ValueError()
        except Exception: raise ValidationError('Las lecturas numéricas no tienen un formato válido.')
        fault=item.get('fault_code','')
        if not isinstance(fault,str) or len(fault)>100: raise ValidationError('fault_code debe ser texto de hasta 100 caracteres.')
        reading=m.TelemetryReading(organization=organization,bus=bus,device=device,measured_at=measured,
            external_event=event,fault_code=fault,**values)
        # Validar el contenido incluso cuando se reutiliza una identidad de evento.
        reading.full_clean(validate_unique=False,validate_constraints=False)
        existing=m.TelemetryReading.objects.filter(device=device,external_event=event).first()
        if existing:
            if existing.measured_at!=reading.measured_at or existing.fault_code!=reading.fault_code or any(getattr(existing,f)!=getattr(reading,f) for f in values):
                raise ValidationError('event_id ya existe con otra lectura; usa una identidad nueva.')
            results.append({'id':existing.pk,'repetida':True}); continue
        reading.save()
        if reading.odometer>bus.odometer:
            bus.odometer=reading.odometer
            bus.save(update_fields=['odometer','updated_at'])
        if reading.engine_hours is not None and (bus.engine_hours is None or reading.engine_hours>bus.engine_hours):
            bus.engine_hours=reading.engine_hours
            bus.save(update_fields=['engine_hours','updated_at'])
        results.append({'id':reading.pk,'repetida':False})
    return results


@transaction.atomic
def ingest(key,records):
    results=_store_readings(key.organization,records)
    key.last_used=timezone.now()
    key.save(update_fields=['last_used'])
    from cmms.services import audit
    audit(key.created_by,'Telemetría recibida',key,{'lecturas':len(records),'nuevas':sum(not r['repetida'] for r in results)})
    return results


@transaction.atomic
def import_records(user,records,filename):
    if user.role not in ('administrador','supervisor'): raise PermissionDenied
    results=_store_readings(user.organization,records)
    from cmms.services import audit
    from pathlib import PurePath
    audit(user,'Telemetría importada',user,{'archivo':PurePath(filename).name[:120],
        'lecturas':len(records),'nuevas':sum(not r['repetida'] for r in results)})
    return results
