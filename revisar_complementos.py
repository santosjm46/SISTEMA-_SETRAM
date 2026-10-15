"""Revisión complementaria de páginas y formularios con espera adicional."""
import json
import argparse
import re
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright
from visor_auditoria import DATA, capture


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--solo', choices=['inspecciones'])
    args = parser.parse_args()
    port = json.loads((DATA / 'conexion.json').read_text(encoding='utf-8'))['puerto']
    records = []
    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp(f'http://127.0.0.1:{port}', timeout=10000)
        page = browser.contexts[0].new_page()
        try:
            page.goto('https://ai.buscmms.com/es/dashboard', wait_until='domcontentloaded', timeout=30000)
            page.wait_for_timeout(6000)
            from auditar_entorno import links
            routes = links(page)
            group = page.get_by_role('link', name=re.compile(r'^(Inspecciones|Inspections)$'))
            if group.count():
                group.first.click(timeout=10000)
                page.wait_for_timeout(1500)
                routes.update(links(page))
            inventory = json.loads((DATA / 'revision_administrador_20261014_103322' / 'inventario.json').read_text(encoding='utf-8'))
            routes.update({r['ruta']:r['menu'] for r in inventory})
            targets = [('/es/inspections', None), ('/es/organization', None),
                       ('/es/predictive-maintenance', None), ('/es/maintenance', 'Crear orden de trabajo'),
                       ('/es/dvir', 'Nuevo DVIR'), ('/es/maintenance/pm-schedules', 'Crear PM Programación')]
            if args.solo:
                # Enlace observado en la consulta inicial de menús del panel.
                routes.setdefault('/es/inspections', 'Inspection Compliance (enlace observado previamente)')
                targets = [(route, None) for route in routes if 'inspection' in route.lower()]
                targets.extend([('/es/inspections', 'Listas de verificación de inspección'),
                                ('/es/inspections', 'Inspection Reminders')])
                if not targets:
                    print('No se detectaron enlaces de inspecciones; no se revisaron esas pantallas.', flush=True)
            for route, button in targets:
                record = {'ruta':route, 'boton_apertura':button}
                try:
                    if route not in routes:
                        raise RuntimeError('Ruta no encontrada en enlaces observados')
                    page.goto('https://ai.buscmms.com' + route, wait_until='domcontentloaded', timeout=45000)
                    page.wait_for_timeout(6000)
                    if urlsplit(page.url).hostname != 'ai.buscmms.com' or 'login' in urlsplit(page.url).path:
                        raise RuntimeError('Acceso redirigido fuera de página autenticada')
                    if button:
                        control = page.get_by_role('button', name=button, exact=True)
                        if not control.count():
                            control = page.get_by_text(button, exact=True)
                        control.first.click(timeout=15000)
                        page.wait_for_timeout(6000)
                    record['evidencia'] = str(capture(page).relative_to(DATA.parent))
                    record['texto'] = (DATA.parent / record['evidencia'] / 'texto.txt').read_text(encoding='utf-8')
                    record['ruta_final'] = urlsplit(page.url).path
                    record['campos'] = page.locator('select').evaluate_all("nodes=>nodes.map(e=>Array.from(e.options).map(o=>o.text))")
                    if args.solo and len(targets) < 10:
                        seen = {r for r, _ in targets}
                        for candidate, label in links(page).items():
                            if ('inspection' in candidate.lower() or label in (
                                    'Listas de verificación de inspección', 'Inspection Reminders', 'Inspection Checklists')) and candidate not in seen and not any(
                                    term in candidate.lower() for term in ('/new', '/create', '/edit')):
                                targets.append((candidate, None))
                                seen.add(candidate)
                except Exception as exc:
                    record['error'] = str(exc)
                records.append(record)
                output = 'complementos_inspecciones.json' if args.solo else 'complementos_administrador.json'
                (DATA / output).write_text(json.dumps(records, ensure_ascii=False, indent=2),encoding='utf-8')
                print(json.dumps({k:v for k,v in record.items() if k not in ('texto','campos')},ensure_ascii=True),flush=True)
        finally:
            page.close()


if __name__ == '__main__':
    main()
