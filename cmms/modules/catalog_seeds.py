"""Catálogos iniciales revisables: creación aditiva, con origen y sin stock."""
import hashlib
import json
from pathlib import Path
from django.conf import settings
from django.core.exceptions import PermissionDenied,ValidationError
from django.db import transaction
from cmms import models as m
from cmms.module import enabled
from cmms.services import audit

SPECS={
    'categorias_repuesto':('Categorías de repuestos',m.PartCategory,'code'),
    'tipos_falla':('Tipos de falla y síntomas',m.FailureType,'code'),
    'repuestos':('Repuestos generales',m.Part,'code'),
    'biblioteca_tareas':('Tareas de referencia',m.ServiceTask,'name'),
    'programas':('Programas sin frecuencia asignada',m.ServiceProgram,'name'),
}


def bundle():
    return json.loads((Path(settings.BASE_DIR)/'catalogos/setram_base_v1.json').read_text(encoding='utf-8'))


def authorize(user,keys):
    if not user.is_active or user.role!='administrador' or not user.organization_id:raise PermissionDenied
    if not keys or any(key not in SPECS or not enabled(user,key) for key in keys):raise PermissionDenied


def prepared(data,key):
    task_names={row['code']:row['name'] for row in data['catalogs']['biblioteca_tareas']}
    rows=[]
    allowed={
        'categorias_repuesto':{'code','name','source_label'},
        'tipos_falla':{'code','name','system','description'},
        'repuestos':{'code','name','category','unit','application_notes'},
        'biblioteca_tareas':{'code','name','instructions'},
        'programas':{'name','task_codes'},
    }
    for raw in data['catalogs'][key]:
        entry=dict(raw);origin=entry.pop('origin','setram_general')
        if origin not in data['origins'] or set(entry)-allowed[key]:raise ValidationError('El catálogo contiene un origen o campo no permitido.')
        entry['catalog_source']=data['origins'][origin]
        if key=='tipos_falla':
            entry.setdefault('description',f"Reporte orientativo: {entry['name']}. Registrar las condiciones y evidencia; la causa debe confirmarse mediante diagnóstico según el manual del bus.")
        elif key=='repuestos':
            entry.setdefault('application_notes',data['part_notes']);entry.setdefault('unit','unidad')
        elif key=='biblioteca_tareas':
            entry.pop('code');entry.setdefault('instructions',data['task_notes']);entry['estimated_hours']=0
        elif key=='programas':
            try:names=[task_names[code] for code in entry.pop('task_codes')]
            except KeyError:raise ValidationError('La plantilla apunta a una tarea inexistente.')
            entry['tasks']='\n'.join(names)
        rows.append(entry)
    return rows


def existing_rows(model,user,identity):
    rows=list(model.objects.filter(organization_id=user.organization_id))
    return {str(getattr(row,identity)).strip().casefold():row for row in rows}, {row.name.strip().casefold():row for row in rows}


def preview(user):
    keys=[key for key in SPECS if enabled(user,key)]
    authorize(user,keys)
    data=bundle();groups=[]
    for key in keys:
        title,model,identity=SPECS[key];by_key,by_name=existing_rows(model,user,identity);rows=[]
        for entry in prepared(data,key):
            existing=by_key.get(str(entry[identity]).strip().casefold()) or by_name.get(entry['name'].strip().casefold())
            rows.append({'name':entry['name'],'code':entry.get('code','—'),'source':entry['catalog_source'],
                         'existing':bool(existing),'system':dict(m.FAILURE_SYSTEMS).get(entry.get('system'),entry.get('category',''))})
        groups.append({'key':key,'title':title,'rows':rows,'new':sum(not row['existing'] for row in rows),'kept':sum(row['existing'] for row in rows)})
    return {'version':data['version'],'groups':groups,'reference':data['reference']}


@transaction.atomic
def apply(user,keys):
    keys=list(dict.fromkeys(keys));authorize(user,keys)
    m.Organization.objects.select_for_update().get(pk=user.organization_id)
    data=bundle();summary={}
    for key,(title,model,identity) in SPECS.items():
        if key not in keys:continue
        by_key,by_name=existing_rows(model,user,identity);created=[];kept=0
        for entry in prepared(data,key):
            marker=str(entry[identity]).strip().casefold();name=entry['name'].strip().casefold()
            if marker in by_key or name in by_name:
                kept+=1;continue
            obj=model(organization_id=user.organization_id,**entry)
            obj.full_clean();obj.save()
            if key=='programas' and enabled(user,'biblioteca_tareas'):
                names=obj.tasks.splitlines()
                templates=list(m.ServiceTask.objects.filter(organization=user.organization,active=True,name__in=names))
                if len(templates)==len(names):obj.task_templates.set(templates)
            by_key[marker]=obj;by_name[name]=obj;created.append(obj.pk)
            audit(user,'Alta desde catálogo inicial',obj,{'version':data['version'],'origen':entry['catalog_source']})
        summary[key]={'creados':len(created),'conservados':kept}
        if created:
            digest=hashlib.sha256(json.dumps({'version':data['version'],'rows':data['catalogs'][key]},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
            m.CatalogImport.objects.get_or_create(organization=user.organization,module=key,digest=digest,
                defaults={'filename':'setram_base_v1.json','records':len(created),'actor':user})
    return summary
