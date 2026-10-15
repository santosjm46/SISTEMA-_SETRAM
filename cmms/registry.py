from importlib import import_module
from .module import Module, MANAGERS, ALL, buses_for, scoped
DOMAINS=['flota', 'personal', 'mantenimiento', 'inspecciones', 'inventario', 'operacion', 'documentos', 'administracion']
DOMAINS.extend(['telemetria','predictivo','seguridad'])
MODULES=[]
for domain in DOMAINS:
    MODULES.extend(import_module('cmms.modules.'+domain+'.registry').MODULES)
for item in MODULES:
    item.section={'Gestion de flota':'Gestión de flota','Operacion':'Operación','Organizacion':'Organización'}.get(item.section,item.section)
REGISTRY={item.key:item for item in MODULES}
if len(REGISTRY)!=len(MODULES): raise RuntimeError('Hay claves de módulo duplicadas.')
