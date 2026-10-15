"""Catálogo de informes con los mismos permisos y filtros que las consultas."""
import io
import csv
import textwrap
import zipfile
from decimal import Decimal
from datetime import date
from django.core.exceptions import PermissionDenied
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from cmms import models as m

CATALOG={
 'hos':('Jornadas y descansos','jornadas'),
 'dvir':('Resumen DVIR','inspecciones'),
 'maintenance':('Mantenimiento','ordenes'),
 'fuel':('Consumo de combustible','combustible'),
 'drivers':('Actividad de conductores','recorridos'),
 'costs':('Costos de flota','ordenes'),
 'fleet':('Estado de buses','buses'),
 'inspections':('Inspecciones técnicas','informes_inspeccion'),
 'compliance':('Cumplimiento','cumplimiento'),
 'inventory':('Repuestos y existencias','repuestos'),
 'tires':('Neumáticos y desgaste','neumaticos'),
}

def dataset(user,kind,params=None):
    from django.http import HttpRequest
    from cmms.registry import REGISTRY
    from cmms.views import access,queryset,display
    if user.role not in ('administrador','supervisor'): raise PermissionDenied
    if kind not in CATALOG: raise KeyError(kind)
    title,key=CATALOG[kind]; request=HttpRequest(); request.user=user; request.GET=params or {}
    module=access(request,key); qs=queryset(request,module)
    columns=list(module.columns)
    if kind in ('maintenance','costs'): columns += [('labor_cost','Mano de obra Bs'),('parts_cost','Repuestos Bs'),('external_cost','Externos Bs'),('total_cost','Total Bs'),('failure_category','Sistema')]
    if kind=='fuel': columns += [('full_tank','Tanque lleno'),('station','Surtidor'),('verification','Conciliación')]
    if kind=='fleet': columns += [('vin','VIN'),('registration_expiry','Registro vence'),('insurance_expiry','Seguro vence')]
    if kind=='tires': columns += [('size','Medida'),('installed_at','Montaje'),('retread_count','Reencauches')]
    rows=[[display(obj,name) for name,_ in columns] for obj in qs[:2000]]
    return {'title':title,'module':module,'headers':[label for _,label in columns],'rows':rows,'total':qs.count(),
            'period':f"{params.get('desde','Historial') if params else 'Historial'} → {params.get('hasta','Hoy') if params else 'Hoy'}",'generated':timezone.localtime()}

def pdf_bytes(title,headers,rows,subtitle=''):
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject,NameObject,DecodedStreamObject
    writer=PdfWriter()
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica'),NameObject('/Encoding'):NameObject('/WinAnsiEncoding')})
    font_id=writer._add_object(font)
    def escaped(text): return str(text).replace('\x00','').replace('\\','\\\\').replace('(','\\(').replace(')','\\)')
    lines=[f'SETRAM · {title}',subtitle,f'Generado: {timezone.localtime():%d/%m/%Y %H:%M} · BOB / km', ' | '.join(headers),'']
    for row in rows:
        value=' | '.join(str(cell).replace('\n',' ') for cell in row)
        lines.extend(textwrap.wrap(value,width=120) or [''])
    if not rows: lines.append('No hay registros en esta consulta.')
    for index in range(0,len(lines),56):
        page=writer.add_blank_page(width=595,height=842)
        page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):font_id})})
        content='BT /F1 9 Tf 36 800 Td 13 TL\n'+'\n'.join('('+escaped(line)+') Tj T*' for line in lines[index:index+56])+'\nET'
        stream=DecodedStreamObject();stream.set_data(content.encode('cp1252',errors='replace'))
        page[NameObject('/Contents')]=writer._add_object(stream)
    output=io.BytesIO();writer.write(output); return output.getvalue()

def csv_bytes(data):
    from cmms.views import csv_safe
    output=io.StringIO(); writer=csv.writer(output,delimiter=';');writer.writerow(data['headers'])
    for row in data['rows']: writer.writerow([csv_safe(cell) for cell in row])
    return ('\ufeff'+output.getvalue()).encode('utf-8')

@transaction.atomic
def process_schedules(org):
    now=timezone.now(); count=0
    schedules=m.ScheduledReport.objects.select_for_update().filter(organization=org,active=True,next_run__lte=now).order_by('pk')[:30]
    for schedule in schedules:
        actor=schedule.created_by
        if not actor.is_active or actor.role not in ('administrador','supervisor') or actor.organization_id!=org.pk: continue
        period_start=timezone.localdate()-timezone.timedelta(days=schedule.interval_days)
        try: data=dataset(actor,schedule.kind,{'desde':period_start.isoformat(),'hasta':timezone.localdate().isoformat()})
        except PermissionDenied: continue
        occurrence=schedule.next_run
        existing=m.ReportRun.objects.filter(schedule=schedule,scheduled_at=occurrence).first()
        if not existing:
            result=m.ReportRun(organization=org,schedule=schedule,scheduled_at=occurrence,records=len(data['rows']))
            result.file.save(f'{schedule.kind}_{schedule.pk}_{now:%Y%m%d_%H%M%S}.pdf',ContentFile(pdf_bytes(data['title'],data['headers'],data['rows'],data['period'])),save=False)
            result.save(); count+=1
            from cmms.modules.inspecciones.services import notify
            notify(actor,'sistema','Informe disponible',schedule.name,f'/modulos/reportes_generados/{result.pk}/',f'informe:{result.pk}')
        elapsed=(now-schedule.next_run).days//schedule.interval_days+1
        schedule.next_run+=timezone.timedelta(days=elapsed*schedule.interval_days);schedule.save(update_fields=['next_run','updated_at'])
    return count
