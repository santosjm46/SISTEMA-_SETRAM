import json
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError,PermissionDenied
from django.http import JsonResponse,HttpResponse
from django.shortcuts import get_object_or_404,redirect,render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from cmms import models as m
from cmms.registry import REGISTRY,scoped,buses_for
from cmms.views import access
from cmms.module import enabled
from cmms.modules.ui import page
from .services import create_key,authenticate_key,ingest,import_records

@login_required
def index(request):
    access(request,'telemetria')
    buses=buses_for(request.user)
    readings=scoped(REGISTRY['telemetria'],request.user).select_related('bus','device').order_by('-measured_at')
    latest=[]
    for bus in buses:
        row=readings.filter(bus=bus).first()
        latest.append({'bus':bus,'reading':row,'fresh':bool(row and timezone.now()-row.measured_at<=timezone.timedelta(hours=24))})
    return page(request,'telemetria','cmms/modules/telemetry.html',latest=latest,readings=readings[:30],
        stats=[{'label':'Buses visibles','value':buses.count()},{'label':'Lecturas recibidas','value':readings.count()},
               {'label':'Dispositivos activos','value':m.TelemetryDevice.objects.filter(bus__in=buses,active=True).count()},
               {'label':'Con datos recientes','value':sum(item['fresh'] for item in latest)}])

@login_required
def keys(request):
    access(request,'integraciones')
    token=None
    if request.method=='POST':
        if request.POST.get('revocar'):
            obj=get_object_or_404(m.IntegrationKey,pk=request.POST['revocar'],organization=request.user.organization)
            obj.active=False; obj.save(update_fields=['active'])
            from cmms.services import audit
            audit(request.user,'Integración revocada',obj)
            messages.success(request,'Clave revocada. Ya no puede enviar lecturas.')
            return redirect('telemetry:keys')
        name=request.POST.get('name','').strip()
        if not name or len(name)>120: messages.error(request,'Indica un nombre de hasta 120 caracteres.')
        else:
            selected=[scope for scope in request.POST.getlist('scopes') if scope in ('telemetria','vision')]
            _,token=create_key(request.user,name,selected or ['telemetria'])
    return page(request,'integraciones','cmms/modules/keys.html',keys=m.IntegrationKey.objects.filter(organization=request.user.organization),new_token=token)


@login_required
def import_file(request):
    module=access(request,'telemetria')
    if request.user.role not in ('administrador','supervisor'): raise PermissionDenied
    from django import forms
    from .files import parse_file
    class UploadForm(forms.Form):
        archivo=forms.FileField(label='Archivo de lecturas',widget=forms.ClearableFileInput(attrs={'class':'form-control','accept':'.csv,.json'}))
    form=UploadForm(request.POST or None,request.FILES or None)
    if request.method=='POST' and form.is_valid():
        try:
            upload=form.cleaned_data['archivo']
            records=parse_file(upload)
            results=import_records(request.user,records,upload.name)
            created=sum(not r['repetida'] for r in results)
            messages.success(request,f'Importación completada: {created} lecturas nuevas y {len(results)-created} repetidas.')
            return redirect('telemetry:index')
        except ValidationError as exc: form.add_error('archivo',' '.join(exc.messages))
    return render(request,'cmms/modules/import_telemetry.html',{'module':module,'page_title':'Importar telemetría','form':form})


@login_required
def file_template(request):
    access(request,'telemetria')
    if request.user.role not in ('administrador','supervisor'): raise PermissionDenied
    from .files import FIELDS
    response=HttpResponse('\ufeff'+','.join(FIELDS)+'\r\n',content_type='text/csv; charset=utf-8')
    response['Content-Disposition']='attachment; filename="plantilla_telemetria.csv"'
    return response

@csrf_exempt
@require_POST
def ingest_endpoint(request):
    auth=request.headers.get('Authorization','')
    key=authenticate_key(auth[7:] if auth.startswith('Bearer ') else '')
    if not key: return JsonResponse({'error':'Credencial inválida o revocada'},status=401)
    if not enabled(key.created_by,'telemetria') or key.scopes and 'telemetria' not in key.scopes: return JsonResponse({'error':'La clave no autoriza telemetría'},status=403)
    if len(request.body)>1024*1024: return JsonResponse({'error':'El lote supera 1 MB'},status=413)
    try:
        payload=json.loads(request.body)
        if not isinstance(payload,dict): raise ValueError
        results=ingest(key,payload.get('readings'))
        return JsonResponse({'lecturas':results,'nuevas':sum(not r['repetida'] for r in results)})
    except (ValueError,TypeError): return JsonResponse({'error':'JSON inválido'},status=400)
    except ValidationError as exc: return JsonResponse({'error':exc.messages},status=422)
