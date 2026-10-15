import csv
import io
import json
from django.core.exceptions import ValidationError

FIELDS=('device_id','event_id','measured_at','odometer','engine_hours','latitude','longitude','speed','temperature','fault_code')
NUMERIC=('odometer','engine_hours','latitude','longitude','speed','temperature')


def parse_file(upload):
    if upload.size>1024*1024: raise ValidationError('El archivo supera 1 MB.')
    suffix=upload.name.rsplit('.',1)[-1].lower()
    if suffix not in ('csv','json'): raise ValidationError('Selecciona un archivo CSV o JSON.')
    try: raw=upload.read().decode('utf-8-sig')
    except UnicodeDecodeError: raise ValidationError('Guarda el archivo en UTF-8.')
    if suffix=='json':
        try:
            payload=json.loads(raw)
            records=payload.get('readings') if isinstance(payload,dict) else payload
        except ValueError: raise ValidationError('El archivo no contiene JSON válido.')
    else:
        first=raw.splitlines()[0] if raw.splitlines() else ''
        reader=csv.DictReader(io.StringIO(raw),delimiter=';' if first.count(';')>first.count(',') else ',')
        headers=reader.fieldnames or []
        if not {'device_id','event_id','measured_at','odometer'}<=set(headers):
            raise ValidationError('Faltan columnas: device_id, event_id, measured_at y odometer son obligatorias.')
        if len(set(headers))!=len(headers) or any(h not in FIELDS for h in headers):
            raise ValidationError('Usa las columnas de la plantilla sin duplicados.')
        records=[]
        try:
            for row in reader:
                if None in row or any(value is None for value in row.values()): raise ValidationError('Hay una fila con columnas incompletas o adicionales.')
                row={k:v.strip() for k,v in row.items()}
                if not any(row.values()): continue
                for k in NUMERIC:
                    if k in row and row[k]=='': row[k]=None
                records.append(row)
                if len(records)>200: raise ValidationError('El archivo supera 200 lecturas.')
        except csv.Error: raise ValidationError('El CSV no tiene una estructura válida.')
    if not isinstance(records,list) or not 1<=len(records)<=200: raise ValidationError('El archivo debe contener entre 1 y 200 lecturas.')
    return records
