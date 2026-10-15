"""Pruebas en un cluster PostgreSQL aislado. No usa ni modifica CMMS."""
import os
import argparse
import secrets
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent
if hasattr(sys.stdout,'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8',errors='replace')
BIN=Path('C:/Program Files/PostgreSQL/18/bin')
WORK=ROOT/'.validacion_postgres'
DATA=WORK/'data'


def run(args,env=None):
    print('Ejecutando: '+str(args[0])+' '+str(args[1]),flush=True)
    # Windows puede dejar pipes heredados abiertos en el proceso servidor.
    with tempfile.TemporaryFile(mode='w+',encoding='utf-8',errors='replace') as output:
        result=subprocess.run([str(a) for a in args],cwd=ROOT,env=env,stdout=output,stderr=output)
        output.seek(0)
        result.stdout, result.stderr = output.read(), ''
    print(result.stdout,flush=True)
    if result.returncode: raise RuntimeError('Falló el comando de validación: '+str(args[0]))
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--solo-visual',action='store_true')
    parser.add_argument('--sin-visual',action='store_true')
    args=parser.parse_args()
    WORK.mkdir(exist_ok=True)
    if not (DATA/'PG_VERSION').exists():
        run([BIN/'initdb.exe','-D',DATA,'-U','cmms_test','-A','trust','--encoding=UTF8','--locale=C'])
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0))
        port=sock.getsockname()[1]
    env=os.environ.copy()
    env.update({'DB_NAME':'postgres','DB_HOST':'127.0.0.1','DB_PORT':str(port),'DB_USER':'cmms_test',
                'DB_PASSWORD':'','DJANGO_SECRET_KEY':secrets.token_urlsafe(48),'DEBUG':'true','PYTHONIOENCODING':'utf-8'})
    try:
        run([BIN/'pg_ctl.exe','-D',DATA,'-l',WORK/'postgres.log','-o',f'-p {port} -h 127.0.0.1','-w','start'])
        if not args.solo_visual:
            run([sys.executable,'manage.py','makemigrations','cmms','--noinput'],env)
            run([sys.executable,'manage.py','check'],env)
            result=run([sys.executable,'manage.py','test','cmms','--noinput','--verbosity','2'],env)
            (ROOT/'RESULTADO_PRUEBAS.txt').write_text(result.stdout+result.stderr,encoding='utf-8')
        if args.sin_visual: return
        run([BIN/'dropdb.exe','--if-exists','-h','127.0.0.1','-p',str(port),'-U','cmms_test','setram_qa'])
        run([BIN/'createdb.exe','-h','127.0.0.1','-p',str(port),'-U','cmms_test','setram_qa'])
        visual_env=env.copy()
        visual_env.update({'DB_NAME':'setram_qa','SETRAM_QA':'1'})
        run([sys.executable,'manage.py','migrate','--noinput'],visual_env)
        run([sys.executable,'qa_visual.py'],visual_env)
    finally:
        subprocess.run([str(BIN/'pg_ctl.exe'),'-D',str(DATA),'-m','fast','-w','stop'],cwd=ROOT,capture_output=True)


if __name__=='__main__':
    main()
