"""Proceso aislado para extracción PDF, sin acceso a la base de datos."""
import json
import sys
from pypdf import PdfReader
reader=PdfReader(sys.argv[1])
if reader.is_encrypted: raise ValueError('El PDF está cifrado.')
text=[]
for page in reader.pages[:10]:
    text.append((page.extract_text() or '')[:3000])
sys.stdout.reconfigure(encoding='utf-8')
print(json.dumps({'pages':len(reader.pages),'pages_read':min(10,len(reader.pages)),'text':'\n'.join(text)[:30000]},ensure_ascii=False))
