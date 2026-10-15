from .registry import MODULES
from .module import enabled
from .models import Notification
from django.urls import reverse

def navigation(request):
    if not request.user.is_authenticated:
        return {}
    groups = {}
    for module in MODULES:
        if request.user.role in module.read and enabled(request.user,module.key):
            groups.setdefault(module.section, []).append({'key':module.key,'label':module.label,
                'url':reverse(module.route) if module.route else reverse('list',args=[module.key])})
    return {'navigation':groups,'is_manager':request.user.role in ('administrador','supervisor'),
        'catalog_seed_url':reverse('catalog-presets') if request.user.role=='administrador' else '',
        'extended_workspace':True,
        'unread_notifications':Notification.objects.filter(user=request.user,read_at__isnull=True).count(),
        'notifications_enabled':enabled(request.user,'notificaciones')}
