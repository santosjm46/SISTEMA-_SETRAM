import json
from django.core.management.base import BaseCommand,CommandError
from django.core.exceptions import PermissionDenied,ValidationError
from cmms import models as m
from cmms.modules.catalog_seeds import preview,apply,SPECS

class Command(BaseCommand):
    help='Previsualiza o carga catálogos iniciales; conserva registros existentes y no carga stock.'
    def add_arguments(self,parser):
        parser.add_argument('--usuario',type=int,required=True)
        parser.add_argument('--organizacion',type=int,required=True)
        parser.add_argument('--modulos',nargs='+',choices=list(SPECS))
        parser.add_argument('--aplicar',action='store_true')
    def handle(self,*args,**options):
        user=m.User.objects.filter(pk=options['usuario'],organization_id=options['organizacion'],is_active=True,role='administrador').first()
        if not user:raise CommandError('Selecciona un administrador activo de la organización indicada.')
        try:
            if options['aplicar']:result=apply(user,options['modulos'] or list(SPECS))
            else:result={group['key']:{'nuevos':group['new'],'conservados':group['kept']} for group in preview(user)['groups']}
        except (PermissionDenied,ValidationError) as exc:raise CommandError(str(exc))
        self.stdout.write(json.dumps({'aplicado':options['aplicar'],'resultado':result},ensure_ascii=True))
