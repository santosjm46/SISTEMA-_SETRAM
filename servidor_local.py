"""Servidor de desarrollo local: no expone la aplicación a la red."""
import os
import sys
import subprocess
from pathlib import Path

os.environ['DEBUG']='true'
os.environ['ALLOWED_HOSTS']='127.0.0.1,localhost'
os.environ.setdefault('DJANGO_SETTINGS_MODULE','setram.settings')
if hasattr(sys.stdout,'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8',errors='replace')
from django.core.management import execute_from_command_line
root=Path(__file__).resolve().parent
with (root/'recordatorios.log').open('a',encoding='utf-8') as log:
    worker=subprocess.Popen([sys.executable,str(root/'manage.py'),'procesar_recordatorios','--continuo'],
        cwd=root,stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:
        execute_from_command_line([sys.argv[0],'runserver','127.0.0.1:8000','--noreload'])
    finally:
        if worker.poll() is None:
            if os.name=='nt':
                # El redirector Python de un venv puede tener otro proceso hijo.
                subprocess.run(['taskkill.exe','/PID',str(worker.pid),'/T','/F'],
                    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            else: worker.terminate()
            try: worker.wait(timeout=5)
            except subprocess.TimeoutExpired: worker.kill()
