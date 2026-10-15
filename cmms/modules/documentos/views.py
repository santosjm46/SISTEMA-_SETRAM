from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404,redirect
from django.utils import timezone
from cmms import models as m
from cmms.registry import REGISTRY,scoped
from cmms.views import access
from cmms.modules.ui import page
from .services import analyze_document
from .ai import configured,analyze_text

@login_required
def auditor(request):
    access(request,'auditor_documental')
    documents=scoped(REGISTRY['documentos'],request.user)
    if request.method=='POST':
        doc=get_object_or_404(documents,pk=request.POST.get('document'))
        analysis=analyze_document(doc,request.user)
        if request.POST.get('authorize_ai')=='on':
            try:
                output=analyze_text(analysis.extracted_text)
                analysis.metadata={**analysis.metadata,'ia':output}
                analysis.method='Revisión local + IA asistida'
                analysis.state='revisar' if output['requiere_revision'] or analysis.findings else 'analizado'
                analysis.save(update_fields=['metadata','method','state'])
                from cmms.services import audit
                audit(request.user,'Análisis IA autorizado',analysis,{'proveedor':'OpenAI','caracteres_enviados':min(6000,len(analysis.extracted_text))})
            except ValidationError as exc: messages.error(request,' '.join(exc.messages))
        return redirect('detail',key='auditor_documental',pk=analysis.pk)
    analyses=scoped(REGISTRY['auditor_documental'],request.user).select_related('document')
    return page(request,'auditor_documental','cmms/modules/auditor.html',documents=documents,analyses=analyses[:30],ai_ready=configured(),
        stats=[{'label':'Documentos visibles','value':documents.count()},{'label':'Analizados','value':analyses.count()},
               {'label':'Requieren revisión','value':analyses.filter(state='revisar').count()},
               {'label':'Proveedor IA','value':'Configurado' if configured() else 'Sin configurar'}])

@login_required
def vision(request):
    access(request,'vision')
    cameras=m.Camera.objects.filter(organization=request.user.organization,active=True)
    selected=cameras.filter(pk=request.GET.get('camera')).first() if str(request.GET.get('camera','')).isdigit() else cameras.first()
    observations=m.CameraObservation.objects.filter(organization=request.user.organization).select_related('camera','bus')
    if selected: observations=observations.filter(camera=selected)
    frame=m.VisionFrame.objects.filter(organization=request.user.organization,camera=selected).order_by('-measured_at').first() if selected else None
    detections=list(frame.visiondetection_set.all()) if frame else []
    overlays=[{'x':float(row.x)*1000,'y':float(row.y)*1000,'width':float(row.width)*1000,'height':float(row.height)*1000,'label':row.label,'confidence':str(row.confidence)} for row in detections]
    return page(request,'vision','cmms/modules/vision.html',cameras=cameras,selected=selected,observations=observations[:30],frame=frame,detections=detections,overlays=overlays)
