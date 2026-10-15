import json
import hashlib
from decimal import Decimal,InvalidOperation
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from cmms import models as m
from cmms.module import enabled
from cmms.modules.telemetria.services import authenticate_key

@transaction.atomic
def ingest_frame(key,payload):
    if not isinstance(payload,dict):raise ValidationError('Envía un objeto JSON.')
    camera=m.Camera.objects.select_for_update().filter(organization=key.organization,pk=payload.get('camera_id'),active=True).first()
    if not camera:raise ValidationError('Cámara no registrada o inactiva.')
    event=payload.get('event_id','');version=payload.get('model_version','')
    if not isinstance(event,str) or not event or len(event)>100 or not isinstance(version,str) or not version or len(version)>120:raise ValidationError('Indica evento y versión del motor de la fuente.')
    measured=parse_datetime(str(payload.get('measured_at','')))
    if not measured or timezone.is_naive(measured) or measured>timezone.now()+timezone.timedelta(minutes=5):raise ValidationError('Fecha ISO con zona horaria, sin adelanto mayor a cinco minutos.')
    objects=payload.get('objects')
    if not isinstance(objects,list) or len(objects)>50:raise ValidationError('Incluye una lista de hasta cincuenta objetos.')
    digest=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    previous=m.VisionFrame.objects.filter(camera=camera,external_event=event).first()
    if previous:
        if previous.digest!=digest:raise ValidationError('El evento ya existe con otro contenido.')
        return previous,True
    frame=m.VisionFrame.objects.create(organization=key.organization,camera=camera,external_event=event,model_version=version,measured_at=measured,digest=digest)
    ids=set()
    for item in objects:
        if not isinstance(item,dict):raise ValidationError('Cada detección debe ser un objeto.')
        object_id=item.get('object_id','')
        if not isinstance(object_id,str) or not object_id or object_id in ids:raise ValidationError('Los objetos necesitan un identificador único por captura.')
        ids.add(object_id)
        bbox=item.get('bbox')
        if not isinstance(bbox,list) or len(bbox)!=4:raise ValidationError('bbox es [x,y,ancho,alto] entre 0 y 1.')
        try:
            values=[Decimal(str(value)) for value in bbox];confidence=Decimal(str(item.get('confidence')))
            if any(not value.is_finite() or not 0<=value<=1 for value in values) or not confidence.is_finite() or not 0<=confidence<=100:raise ValueError()
            values=[value.quantize(Decimal('.000001')) for value in values];confidence=confidence.quantize(Decimal('.01'))
        except (ValueError,InvalidOperation,TypeError):raise ValidationError('Coordenadas o confianza inválidas.')
        bus=None
        if item.get('bus_code'):
            bus=m.Bus.objects.filter(organization=key.organization,code=item['bus_code']).first()
            if not bus:raise ValidationError('El bus no pertenece a esta organización.')
        if camera.bus_id and bus and bus.pk!=camera.bus_id:raise ValidationError('La cámara fija del bus no coincide con la detección.')
        detection=m.VisionDetection(organization=key.organization,frame=frame,bus=bus,object_id=object_id,label=item.get('label',''),plate=item.get('plate',''),
            x=values[0],y=values[1],width=values[2],height=values[3],confidence=confidence,risk=item.get('risk','normal'))
        detection.full_clean();detection.save()
    from cmms.services import audit
    audit(key.created_by,'Detecciones recibidas',frame,{'objetos':len(objects),'motor':version})
    return frame,False

@csrf_exempt
@require_POST
def endpoint(request):
    auth=request.headers.get('Authorization','');key=authenticate_key(auth[7:] if auth.startswith('Bearer ') else '')
    if not key:return JsonResponse({'error':'Credencial inválida'},status=401)
    if 'vision' not in key.scopes or not enabled(key.created_by,'vision'):return JsonResponse({'error':'La clave no autoriza visión'},status=403)
    if len(request.body)>1024*1024:return JsonResponse({'error':'Máximo 1 MB'},status=413)
    try:
        frame,repeated=ingest_frame(key,json.loads(request.body));return JsonResponse({'frame':frame.pk,'repetida':repeated,'objetos':frame.visiondetection_set.count()})
    except (ValueError,TypeError):return JsonResponse({'error':'JSON inválido'},status=400)
    except ValidationError as exc:return JsonResponse({'error':exc.messages},status=422)
