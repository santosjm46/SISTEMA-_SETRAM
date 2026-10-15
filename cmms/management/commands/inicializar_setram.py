from django.core.management.base import BaseCommand
from cmms.models import Organization, Checklist

class Command(BaseCommand):
    help = 'Inicializa SETRAM y una plantilla base; no crea buses ni datos operativos ficticios.'
    def handle(self,*args,**options):
        org = Organization.objects.order_by('pk').first()
        if org is None:
            org = Organization.objects.create(name='SETRAM',currency='BOB',timezone='America/La_Paz')
        Checklist.objects.get_or_create(organization=org,name='Inspección preoperacional · base',defaults={'items':'Frenos de servicio y estacionamiento\nNeumáticos y ruedas\nLuces y señalización\nPuertas y acceso de pasajeros\nEspejos y visibilidad\nBocina\nNiveles y fugas visibles\nEquipamiento de emergencia\nLimpieza y estado del habitáculo'})
        self.stdout.write(self.style.SUCCESS('SETRAM inicializado. Revisa y adapta la plantilla de inspección antes de operar.'))
