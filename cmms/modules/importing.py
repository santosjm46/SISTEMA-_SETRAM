"""Importación atómica de catálogos, sin actualización destructiva de registros."""
import csv
import io
import json
import hashlib
from django.core.exceptions import ValidationError,PermissionDenied
from django.db import transaction,models
from cmms import models as m
from cmms.registry import REGISTRY
from cmms.forms import form_class
from cmms.services import save_record,audit

SUPPORTED={'buses','repuestos','neumaticos','proveedores','programas','tipos_falla','categorias_repuesto','biblioteca_tareas'}

def columns(key):
    module=REGISTRY[key]
    return [name for name in module.fields if not isinstance(module.model._meta.get_field(name),models.ManyToManyField)]

@transaction.atomic
def import_catalog(user,key,upload):
    if key not in SUPPORTED or user.role not in REGISTRY[key].create:raise PermissionDenied
    if upload.size>1024*1024:raise ValidationError('Máximo 1 MB y 200 registros.')
    raw=upload.read();digest=hashlib.sha256(raw).hexdigest()
    m.Organization.objects.select_for_update().get(pk=user.organization_id)
    existing=m.CatalogImport.objects.filter(organization=user.organization,module=key,digest=digest).first()
    if existing:return existing,True
    try:
        text=raw.decode('utf-8-sig');extension=upload.name.rsplit('.',1)[-1].lower()
        if extension=='json':records=json.loads(text)
        elif extension=='csv':
            first=text.splitlines()[0] if text.splitlines() else ''
            records=list(csv.DictReader(io.StringIO(text),delimiter=';' if first.count(';')>first.count(',') else ','))
        else:raise ValidationError('Selecciona CSV o JSON.')
    except (UnicodeDecodeError,ValueError,csv.Error):raise ValidationError('Archivo inválido; usa UTF-8 y columnas de la plantilla.')
    if not isinstance(records,list) or not 1<=len(records)<=200:raise ValidationError('Incluye entre 1 y 200 registros.')
    names=set(columns(key)); module=REGISTRY[key]
    for index,row in enumerate(records,1):
        if not isinstance(row,dict) or any(name not in names for name in row):raise ValidationError(f'Fila {index}: columna no admitida.')
        payload={}
        for field in module.model._meta.fields:
            if field.name not in names:continue
            value=row.get(field.name)
            if value in (None,'') and field.has_default():value=field.get_default()
            if isinstance(field,models.BooleanField):value='on' if str(value).lower() in ('true','1','si','sí','on') else ''
            if value is not None:payload[field.name]=value
        form=form_class(module)(payload,user=user,module=module)
        if not form.is_valid():
            details='; '.join(name+': '+', '.join(str(message) for message in errors) for name,errors in form.errors.items())
            raise ValidationError(f'Fila {index}: {details}')
        save_record(form,user)
    result=m.CatalogImport.objects.create(organization=user.organization,module=key,digest=digest,filename=upload.name[:180],records=len(records),actor=user)
    audit(user,'Catálogo importado',result,{'modulo':key,'registros':len(records)})
    return result,False
