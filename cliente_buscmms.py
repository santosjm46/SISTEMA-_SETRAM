"""Interfaz JSON local sobre la sesión de Chrome, sin exportar credenciales."""
import argparse
import json
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright
from visor_auditoria import DATA, capture


def main():
    parser = argparse.ArgumentParser(description="Consultar BusCMMS usando el Chrome del visor")
    parser.add_argument("accion", choices=["estado", "menus", "captura", "abrir"])
    parser.add_argument("--ruta", help="Ruta de menú previamente obtenida con menus")
    args = parser.parse_args()
    connection = DATA / "conexion.json"
    if not connection.exists():
        raise RuntimeError("Reabre el visor actualizado y pulsa Abrir Chrome para publicar la conexión.")
    port = json.loads(connection.read_text(encoding="utf-8"))["puerto"]
    if not isinstance(port, int) or not 1024 <= port <= 65535:
        raise RuntimeError("Puerto local inválido.")
    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp(f"http://127.0.0.1:{port}", timeout=10000)
        pages = [p for c in browser.contexts for p in c.pages
                 if urlsplit(p.url).hostname == "ai.buscmms.com"]
        if not pages:
            raise RuntimeError("Abre BusCMMS en el Chrome del visor.")
        page = pages[-1]
        path = urlsplit(page.url).path
        if args.accion == "estado":
            result = {"ruta": path, "titulo": page.title(), "pantalla_login": "login" in path.lower()}
        else:
            if "login" in path.lower():
                raise RuntimeError("Completa el acceso con Google en Chrome primero.")
            links = page.locator("a[href]").evaluate_all("""nodes => nodes.map(a => ({
                texto: a.innerText.trim(), url: a.href
            })).filter(a => a.texto)""")
            menus = []
            for link in links:
                url = urlsplit(link["url"])
                if url.scheme == "https" and url.hostname == "ai.buscmms.com" and not url.query and not url.fragment:
                    if not any(word in url.path.lower() for word in ("logout", "signout", "delete", "remove", "login")):
                        item = {"texto": link["texto"], "ruta": url.path}
                        if item not in menus:
                            menus.append(item)
            if args.accion == "menus":
                result = {"menus": menus}
            elif args.accion == "abrir":
                if args.ruta not in [item["ruta"] for item in menus]:
                    raise RuntimeError("La ruta debe ser un enlace de menú de la pantalla actual.")
                page.goto("https://ai.buscmms.com" + args.ruta, wait_until="domcontentloaded", timeout=30000)
                result = {"ruta": urlsplit(page.url).path, "titulo": page.title()}
            else:
                result = {"evidencia": str(capture(page))}
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        raise SystemExit(1)
