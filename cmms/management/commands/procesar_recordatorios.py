"""Notificaciones internas. Se puede ejecutar una vez o como proceso periódico."""
import time
from django.core.management.base import BaseCommand
from django.db import close_old_connections
from cmms.models import Organization
from cmms.modules.inspecciones.services import dispatch_reminders,send_kpi_alerts


class Command(BaseCommand):
    help='Genera avisos internos de inspección que están pendientes.'

    def add_arguments(self,parser):
        parser.add_argument('--continuo',action='store_true')
        parser.add_argument('--intervalo',type=int,default=60)

    def handle(self,*args,**options):
        interval=max(15,options['intervalo'])
        while True:
            close_old_connections()
            try:
                count=0
                for org in Organization.objects.all():
                    flags=org.enabled_modules
                    if flags.get('recordatorios',True) and flags.get('notificaciones',True):
                        count+=dispatch_reminders(org)
                        count+=send_kpi_alerts(org)
                    if flags.get('reportes_programados',True):
                        from cmms.modules.administracion.reports import process_schedules
                        process_schedules(org)
                    if flags.get('repuestos',True) and flags.get('demandas_compra',True):
                        from cmms.modules.inventario.services import update_demands
                        update_demands(org)
                if count or not options['continuo']: self.stdout.write(f'Avisos generados: {count}')
            except Exception as exc:
                if not options['continuo']: raise
                # Las credenciales y contenido de los registros no se imprimen.
                self.stderr.write('No se pudo procesar avisos: '+type(exc).__name__)
            if not options['continuo']: break
            time.sleep(interval)
