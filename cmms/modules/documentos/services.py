import hashlib
import json
import subprocess
import sys
from pathlib import Path
from django.utils import timezone
from cmms import models as m


def analyze_document(doc,user):
    findings=[]
    with doc.file.open('rb') as stream:
        digest=hashlib.file_digest(stream,'sha256').hexdigest()
    metadata={'sha256':digest,'bytes':doc.file.size,'formato':doc.file.name.rsplit('.',1)[-1].lower()}
    text=''
    if metadata['formato']=='pdf':
        try:
            worker=Path(__file__).with_name('pdf_worker.py')
            result=subprocess.run([sys.executable,str(worker),doc.file.path],capture_output=True,timeout=15,encoding='utf-8',errors='replace')
            if result.returncode: raise ValueError('No se pudo extraer el PDF.')
            data=json.loads(result.stdout)
            text=data.pop('text')
            metadata.update(data)
            if not text.strip(): findings.append('No hay texto extraíble: requiere revisión visual u OCR.')
            if data['pages']>10: findings.append('Extracción limitada a las primeras 10 páginas.')
        except subprocess.TimeoutExpired: findings.append('Se alcanzó el límite de extracción; revisar manualmente.')
        except Exception: findings.append('El PDF requiere revisión manual para extraer contenido.')
    else: findings.append('Imagen registrada: el contenido se revisa visualmente; no se ejecutó OCR.')
    if doc.expiry and doc.expiry<timezone.localdate(): findings.append('El documento está vencido.')
    if doc.kind in ('seguro','registro','inspeccion') and not doc.expiry: findings.append('Falta registrar vencimiento para este documento.')
    duplicate=m.DocumentAnalysis.objects.filter(organization=doc.organization,metadata__sha256=digest).exclude(document=doc).exists()
    if duplicate: findings.append('Hay otro documento con el mismo contenido en la organización.')
    analysis,_=m.DocumentAnalysis.objects.update_or_create(document=doc,organization=doc.organization,
        defaults={'state':'revisar' if findings else 'analizado','method':'Revisión documental local','extracted_text':text,
                  'findings':findings,'metadata':metadata,'analyzed_at':timezone.now()})
    from cmms.services import audit
    audit(user,'Documento analizado',analysis,{'hallazgos':len(findings),'motor':analysis.method})
    return analysis
