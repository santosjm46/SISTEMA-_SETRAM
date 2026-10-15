from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404,redirect
from django.utils import timezone
from cmms import models as m
from cmms.registry import MANAGERS
from cmms.views import access
from cmms.modules.ui import page
from .services import dispatch_reminders

@login_required
def notifications(request):
    access(request,'notificaciones')
    if request.method=='POST':
        if request.POST.get('procesar'):
            if request.user.role not in MANAGERS: raise PermissionDenied
            count=dispatch_reminders(request.user.organization)
            messages.success(request,f'{count} notificaciones generadas.')
        elif request.POST.get('leida'):
            item=get_object_or_404(m.Notification,pk=request.POST['leida'],user=request.user,organization=request.user.organization)
            item.read_at=timezone.now(); item.save(update_fields=['read_at'])
        return redirect('inspections:notifications')
    records=m.Notification.objects.filter(user=request.user,organization=request.user.organization)
    return page(request,'notificaciones','cmms/modules/notifications.html',notifications=records[:100],
        stats=[{'label':'Sin leer','value':records.filter(read_at__isnull=True).count()},{'label':'Recibidas','value':records.count()}])
