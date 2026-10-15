import io
import zipfile
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied,ValidationError
from django.http import HttpResponse,FileResponse,Http404
from django.shortcuts import get_object_or_404,redirect,render
from django.views.decorators.http import require_POST,require_GET
from django.db import transaction
from django.utils import timezone
from cmms import models as m
from cmms.views import access,queryset,display
from cmms.registry import REGISTRY,scoped
from cmms.modules.administracion.reports import CATALOG,dataset,pdf_bytes,csv_bytes

@login_required
def catalog_presets(request):
    from .catalog_seeds import preview,apply
    if request.method not in ('GET','POST'):
        from django.http import HttpResponseNotAllowed
        return HttpResponseNotAllowed(['GET','POST'])
    if request.method=='POST':
        keys=request.POST.getlist('catalogos')
        if not keys:messages.error(request,'Selecciona al menos un catálogo.')
        else:
            try:
                result=apply(request.user,keys)
                created=sum(row['creados'] for row in result.values());kept=sum(row['conservados'] for row in result.values())
                messages.success(request,f'Catálogos preparados: {created} altas; {kept} registros existentes conservados.')
                return redirect('catalog-presets')
            except ValidationError as exc:messages.error(request,' '.join(exc.messages))
    return render(request,'cmms/modules/catalog_presets.html',{'page_title':'Catálogos iniciales','catalog':preview(request.user)})

@login_required
@require_GET
def record_pdf(request,key):
    module=access(request,key); qs=queryset(request,module)
    rows=[[display(obj,name) for name,_ in module.columns] for obj in qs[:2000]]
    payload=pdf_bytes(module.label,[label for _,label in module.columns],rows,'Registros visibles de la consulta · hasta 2.000 registros')
    from cmms.services import audit
    audit(request.user,'Exportación PDF',request.user,{'modulo':key,'registros':len(rows)})
    response=HttpResponse(payload,content_type='application/pdf');response['Content-Disposition']=f'attachment; filename="setram_{key}.pdf"';return response

@login_required
def report(request,kind):
    try: data=dataset(request.user,kind,request.GET)
    except KeyError: raise Http404
    format=request.GET.get('formato')
    if format in ('csv','pdf'):
        payload=csv_bytes(data) if format=='csv' else pdf_bytes(data['title'],data['headers'],data['rows'],data['period'])
        response=HttpResponse(payload,content_type='text/csv; charset=utf-8' if format=='csv' else 'application/pdf')
        response['Content-Disposition']=f'attachment; filename="setram_{kind}.{format}"';return response
    return render(request,'cmms/modules/report.html',{'page_title':data['title'],'data':data,'extended_workspace':True})

@login_required
def report_zip(request):
    if request.user.role not in ('administrador','supervisor'):raise PermissionDenied
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        for kind in CATALOG:
            try:data=dataset(request.user,kind,request.GET)
            except PermissionDenied:continue
            archive.writestr(kind+'.csv',csv_bytes(data))
    response=HttpResponse(output.getvalue(),content_type='application/zip');response['Content-Disposition']='attachment; filename="setram_informes.zip"';return response

@login_required
def report_run_file(request,pk):
    access(request,'reportes_generados'); obj=get_object_or_404(scoped(REGISTRY['reportes_generados'],request.user),pk=pk)
    return FileResponse(obj.file.open('rb'),as_attachment=True,filename=obj.file.name.rsplit('/',1)[-1])

@login_required
def bus_photo_file(request,pk):
    access(request,'fotos_bus'); obj=get_object_or_404(scoped(REGISTRY['fotos_bus'],request.user),pk=pk)
    mime='image/png' if obj.image.name.lower().endswith('.png') else 'image/jpeg'
    return FileResponse(obj.image.open('rb'),content_type=mime)

@login_required
@require_POST
def purchase_partial(request,pk):
    access(request,'compras')
    from cmms.modules.inventario.services import receive
    try: receive(request.user,pk,request.POST.get('quantity'),request.POST.get('line'),request.POST.get('token'))
    except m.PurchaseOrder.DoesNotExist: raise Http404
    except ValidationError as exc:messages.error(request,' '.join(exc.messages))
    else: messages.success(request,'Recepción registrada y existencias actualizadas.')
    return redirect('detail',key='compras',pk=pk)

@transaction.atomic
def review_record(user,key,pk,state,notes):
    if user.role not in ('administrador','supervisor'): raise PermissionDenied
    model=m.FuelEntry if key=='combustible' else m.MaintenanceRequest
    obj=model.objects.select_for_update().get(pk=pk,organization=user.organization)
    if key=='combustible':
        if state not in ('verificado','observado'): raise ValidationError('Selecciona un estado de conciliación válido.')
        if state=='observado' and not notes.strip(): raise ValidationError('Describe la diferencia detectada.')
        obj.verification=state; obj.verification_notes=notes
    else:
        if state not in ('en_revision','rechazada') or obj.status=='convertida': raise ValidationError('La solicitud no admite esa revisión.')
        if state=='rechazada' and not notes.strip(): raise ValidationError('Registra el motivo del rechazo.')
        obj.status=state; obj.review_notes=notes
    obj.save()
    from cmms.services import audit
    audit(user,'Conciliación' if key=='combustible' else 'Revisión de solicitud',obj,{'estado':state,'notas':notes})
    return obj

@login_required
@require_POST
def widgets(request):
    from cmms.modules.portal.dashboard import WIDGETS
    selected=[key for key in request.POST.getlist('widgets') if key in dict(WIDGETS)]
    if not selected:messages.error(request,'Selecciona al menos un widget.')
    else:
        request.user.dashboard_widgets=list(dict.fromkeys(selected));request.user.save(update_fields=['dashboard_widgets'])
        messages.success(request,'Preferencias guardadas para tu cuenta.')
    return redirect('dashboard')

@login_required
def search(request):
    from django.db.models import Q
    from cmms.module import enabled
    query=request.GET.get('q','').strip()[:80]; groups=[]
    if query:
        for module in REGISTRY.values():
            if request.user.role not in module.read or not enabled(request.user,module.key) or module.model is m.Organization:continue
            predicate=Q()
            for name in module.search:predicate|=Q(**{name+'__icontains':query})
            rows=scoped(module,request.user).filter(predicate)[:5]
            if rows:groups.append({'module':module,'records':rows})
    return render(request,'cmms/modules/search.html',{'page_title':'Buscar en SETRAM','query':query,'groups':groups})

@login_required
def bus_qr(request,pk):
    from django.urls import reverse
    access(request,'buses');bus=get_object_or_404(scoped(REGISTRY['buses'],request.user),pk=pk)
    import qrcode
    from qrcode.image.svg import SvgPathImage
    target=request.GET.get('destino','solicitudes')
    if target not in ('solicitudes','inspecciones'):raise Http404
    access(request,target)
    uri=request.build_absolute_uri(reverse('create',args=[target]))+f'?bus={bus.pk}'
    picture=qrcode.make(uri,image_factory=SvgPathImage);stream=io.BytesIO();picture.save(stream)
    response=HttpResponse(stream.getvalue(),content_type='image/svg+xml');response['Content-Disposition']=f'inline; filename="bus_{bus.pk}_{target}.svg"';return response

@login_required
def fuel_analytics(request):
    module=access(request,'combustible')
    from cmms.modules.operacion.services import fuel_efficiency
    qs=queryset(request,module).select_related('bus')
    rows=fuel_efficiency(list(qs))
    return render(request,'cmms/modules/fuel_analytics.html',{'module':module,'page_title':'Consumo y conciliación','efficiency':rows,'entries':qs[:50],'extended_workspace':True})

@login_required
def catalog_import(request,key):
    module=access(request,key)
    from cmms.modules.importing import SUPPORTED,columns,import_catalog
    from django import forms
    if key not in SUPPORTED or request.user.role not in module.create:raise PermissionDenied
    if request.GET.get('plantilla'):
        response=HttpResponse('\ufeff'+','.join(columns(key))+'\r\n',content_type='text/csv; charset=utf-8')
        response['Content-Disposition']=f'attachment; filename="plantilla_{key}.csv"';return response
    class UploadForm(forms.Form):
        archivo=forms.FileField(widget=forms.ClearableFileInput(attrs={'class':'form-control','accept':'.csv,.json'}))
    form=UploadForm(request.POST or None,request.FILES or None)
    if request.method=='POST' and form.is_valid():
        try:
            result,repeated=import_catalog(request.user,key,form.cleaned_data['archivo'])
            messages.success(request,'Este archivo ya se importó; no se duplicaron registros.' if repeated else f'Importación completada: {result.records} registros.')
            return redirect('list',key=key)
        except ValidationError as exc:form.add_error('archivo',' '.join(exc.messages))
    return render(request,'cmms/modules/import_catalog.html',{'module':module,'page_title':'Importar '+module.label.lower(),'form':form,'columns':columns(key),'extended_workspace':True})
