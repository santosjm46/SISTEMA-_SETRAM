from django.contrib.auth.decorators import login_required
from django.utils import timezone
from cmms.registry import scoped,REGISTRY
from cmms.views import access
from cmms.modules.ui import page

@login_required
def index(request):
    access(request,'cumplimiento')
    requirements=scoped(REGISTRY['cumplimiento'],request.user).select_related('bus','responsible')
    docs=scoped(REGISTRY['documentos'],request.user).filter(expiry__isnull=False)
    applicable=requirements.exclude(status='no_aplica')
    count=applicable.count()
    completed=applicable.filter(status='completado').count()
    today=timezone.localdate()
    return page(request,'cumplimiento','cmms/modules/compliance.html',requirements=requirements[:30],
        expired=docs.filter(expiry__lt=today),upcoming=docs.filter(expiry__gte=today,expiry__lte=today+timezone.timedelta(days=30)),
        stats=[{'label':'Requisitos aplicables','value':count},{'label':'Completados','value':completed},
               {'label':'Cumplimiento registrado','value':f'{round(completed/count*100)}%' if count else 'Sin datos'},
               {'label':'Requisitos vencidos','value':applicable.exclude(status='completado').filter(due_date__lt=today).count()}])
