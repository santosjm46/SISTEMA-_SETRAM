"""Inventario y evidencias de páginas enlazadas, sin enviar formularios."""
import argparse
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright
from visor_auditoria import DATA, capture

BLOCK = ("logout", "signout", "delete", "remove", "login", "register", "reset", "invite", "checkout")


def links(page):
    raw = page.locator('a[href]').evaluate_all("""nodes => nodes.map(a => ({texto: a.innerText.trim(), url: a.href}))""")
    result = {}
    for item in raw:
        url = urlsplit(item['url'])
        if (url.scheme == 'https' and url.hostname == 'ai.buscmms.com' and
                not url.query and not url.fragment and item['texto'] and
                not any(term in url.path.lower() for term in BLOCK)):
            result.setdefault(url.path, item['texto'])
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--entorno', required=True, choices=['administrador', 'usuario'])
    parser.add_argument('--rutas-desde', help='Inventario previo para volver a comprobar sus rutas')
    args = parser.parse_args()
    connection = json.loads((DATA / 'conexion.json').read_text(encoding='utf-8'))
    folder = DATA / ('revision_' + args.entorno + '_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
    folder.mkdir(parents=True)
    records = []
    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp(f"http://127.0.0.1:{connection['puerto']}", timeout=10000)
        pages = [p for c in browser.contexts for p in c.pages if urlsplit(p.url).hostname == 'ai.buscmms.com']
        if not pages:
            raise RuntimeError('No hay sesión BusCMMS abierta.')
        source = pages[-1]
        if 'login' in urlsplit(source.url).path:
            raise RuntimeError('Inicia sesión antes de auditar.')
        # Solo se expanden los grupos identificados de la barra lateral.
        pending = links(source)
        if args.rutas_desde:
            previous = json.loads(Path(args.rutas_desde).read_text(encoding='utf-8'))
            pending.update({r['ruta']: r['menu'] for r in previous})
        groups = ['Gestión de Flota', 'Inspecciones', 'Mantenimiento', 'Repuestos e Inventario', 'Documento', 'Organización']
        for label in groups:
            group = source.get_by_role('link', name=label, exact=True)
            if group.count() and urlsplit(group.first.get_attribute('href') or '').path in ('/es/dashboard', ''):
                try:
                    group.first.click(timeout=2500)
                    source.wait_for_timeout(200)
                except Exception:
                    pass
            pending.update(links(source))
        (folder / 'menus.json').write_text(json.dumps(pending, ensure_ascii=False, indent=2), encoding='utf-8')
        page = source.context.new_page()
        try:
            for route, label in list(pending.items()):
                record = {'ruta': route, 'menu': label, 'entorno_declarado': args.entorno}
                try:
                    response = page.goto('https://ai.buscmms.com' + route, wait_until='domcontentloaded', timeout=25000)
                    try:
                        page.wait_for_function("""() => Array.from(document.querySelectorAll('h1,h2,h3')).some(
                            h => h.innerText.trim() && !/^BusCMMS\\s*AI$/i.test(h.innerText.trim())) &&
                            !/Loading|Cargando|cargando/.test(document.body.innerText)""", timeout=18000)
                        page.wait_for_timeout(1000)
                        record['carga'] = 'Contenido detectado'
                    except Exception:
                        record['carga'] = 'Carga no confirmada en 18 segundos; requiere revisión'
                    record['http'] = response.status if response else None
                    record['ruta_final'] = urlsplit(page.url).path
                    if urlsplit(page.url).hostname != 'ai.buscmms.com' or 'login' in record['ruta_final']:
                        record['resultado'] = 'Redirección; no se capturó el acceso'
                    else:
                        evidence = capture(page)
                        record['evidencia'] = str(evidence.relative_to(DATA.parent))
                        record['titulos'] = page.locator('h1,h2,h3').all_text_contents()
                        record['botones'] = page.get_by_role('button').all_text_contents()
                        record['campos'] = page.locator('input,select,textarea').evaluate_all("""nodes => nodes.map(e => ({
                          tipo: e.type || e.tagName, nombre: e.name, etiqueta: e.getAttribute('aria-label'),
                          placeholder: e.getAttribute('placeholder'), requerido: e.required,
                          deshabilitado: e.disabled
                        }))""")
                except Exception as exc:
                    record['error'] = str(exc)
                records.append(record)
                (folder / 'inventario.json').write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
                print(json.dumps({'ruta': route, 'resultado': record.get('error', record.get('resultado', 'capturada'))}, ensure_ascii=False), flush=True)
        finally:
            page.close()
    print(str(folder), flush=True)


if __name__ == '__main__':
    main()
