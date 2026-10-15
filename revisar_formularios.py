"""Abrir formularios específicos sin completarlos ni enviarlos."""
import json
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright
from visor_auditoria import DATA, capture

TARGETS = [('/es/team-members', 'Invitar miembro'), ('/es/dvir', 'Nuevo DVIR'),
           ('/es/maintenance', 'Crear orden de trabajo'),
           ('/es/maintenance/pm-schedules', 'Crear PM Programación')]


def main():
    port = json.loads((DATA / 'conexion.json').read_text(encoding='utf-8'))['puerto']
    inventory = DATA / 'revision_administrador_20261014_103322' / 'inventario.json'
    known = {r['ruta'] for r in json.loads(inventory.read_text(encoding='utf-8'))}
    results = []
    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp(f'http://127.0.0.1:{port}', timeout=10000)
        page = browser.contexts[0].new_page()
        try:
            for route, button in TARGETS:
                if route not in known:
                    continue
                result = {'ruta': route, 'accion_solo_apertura': button}
                try:
                    page.goto('https://ai.buscmms.com' + route, wait_until='domcontentloaded', timeout=30000)
                    if 'login' in urlsplit(page.url).path:
                        raise RuntimeError('Sesión no autenticada')
                    page.get_by_role('button', name=button, exact=True).first.click(timeout=20000)
                    page.wait_for_timeout(2000)
                    result['evidencia'] = str(capture(page).relative_to(DATA.parent))
                    result['labels'] = page.locator('label').all_text_contents()
                    result['dialogos'] = page.get_by_role('dialog').all_text_contents()
                    result['campos'] = page.locator('input,textarea,select').evaluate_all("""nodes => nodes.map(e => ({
                        tipo:e.type || e.tagName, nombre:e.name, placeholder:e.getAttribute('placeholder'),
                        requerido:e.required, opciones:e.tagName === 'SELECT' ? Array.from(e.options).map(o=>o.text) : []
                    }))""")
                except Exception as exc:
                    result['error'] = str(exc)
                results.append(result)
                (DATA / 'formularios_administrador.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
                print(json.dumps(result, ensure_ascii=True), flush=True)
        finally:
            page.close()


if __name__ == '__main__':
    main()
