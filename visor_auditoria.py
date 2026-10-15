"""Visor local de evidencias: el usuario inicia sesión en Chrome."""
import json
import os
import queue
import re
import socket
import subprocess
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "auditoria"
PROFILE = ROOT / ".perfil_visor"
COMMAND = DATA / "solicitud_captura.json"
LOGIN = "https://ai.buscmms.com/es/login/admin"


def chrome_path():
    for base in (os.environ.get("PROGRAMFILES", ""), os.environ.get("PROGRAMFILES(X86)", ""), os.environ.get("LOCALAPPDATA", "")):
        candidate = Path(base) / "Google/Chrome/Application/chrome.exe"
        if candidate.is_file():
            return candidate
    raise RuntimeError("No se encontró Google Chrome instalado.")


def capture(page):
    url = urlsplit(page.url)
    if url.scheme != "https" or url.hostname != "ai.buscmms.com":
        raise RuntimeError("Selecciona una pestaña de BusCMMS para capturar.")
    if "login" in url.path.lower():
        raise RuntimeError("Inicia sesión primero. No se captura el formulario de acceso.")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    folder = DATA / stamp
    folder.mkdir(parents=True)
    page.screenshot(path=str(folder / "pantalla.png"), full_page=True,
                    mask=[page.locator('input, textarea, [contenteditable="true"]')])
    # innerText no incluye valores de input; se excluyen editores y campos.
    visible = page.locator("body").evaluate("""body => {
        const walker = document.createTreeWalker(body, NodeFilter.SHOW_TEXT);
        const lines = [];
        while (walker.nextNode()) {
            const node = walker.currentNode, element = node.parentElement;
            if (!element || element.closest('input, textarea, script, style, [contenteditable="true"]')) continue;
            if (!element.getClientRects().length || getComputedStyle(element).visibility === 'hidden') continue;
            const text = node.textContent.trim();
            if (text) lines.push(text);
        }
        return lines.join('\\n');
    }""")
    record = {"fecha_local": datetime.now().isoformat(), "ruta": url.path,
              "titulo": page.title(), "captura": str(folder / "pantalla.png"),
              "texto": str(folder / "texto.txt")}
    (folder / "texto.txt").write_text(visible, encoding="utf-8")
    (folder / "metadata.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    (DATA / "ultima_captura.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return folder


class Viewer:
    def __init__(self, root):
        self.root = root
        self.tasks = queue.Queue()
        self.events = queue.Queue()
        self.port = None
        DATA.mkdir(exist_ok=True)
        root.title("Visor de auditoría · BusCMMS")
        root.geometry("740x460")
        frame = ttk.Frame(root, padding=20)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Auditoría de BusCMMS", font=("Segoe UI", 18)).pack(anchor="w")
        ttk.Label(frame, text="1. Pulsa Abrir Chrome para entrar al portal de administrador.\n2. Pulsa Iniciar con Google y elige tu cuenta en Chrome.\n3. Tras entrar al sistema, pulsa Capturar página.", wraplength=680).pack(anchor="w", pady=16)
        buttons = ttk.Frame(frame)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Abrir Chrome", command=self.open_browser).pack(side="left", padx=4)
        ttk.Button(buttons, text="Iniciar con Google", command=lambda: self.tasks.put("google")).pack(side="left", padx=4)
        ttk.Button(buttons, text="Conectar sesión", command=lambda: self.tasks.put("connect")).pack(side="left", padx=4)
        ttk.Button(buttons, text="Capturar página", command=lambda: self.tasks.put("capture")).pack(side="left", padx=4)
        ttk.Button(frame, text="Abrir carpeta de evidencias", command=lambda: os.startfile(DATA)).pack(anchor="w", pady=12)
        self.status = tk.StringVar(value="Listo. No se solicitan ni guardan contraseñas en el visor.")
        ttk.Label(frame, textvariable=self.status, wraplength=620).pack(anchor="w", pady=12)
        ttk.Label(frame, text="Chrome conserva la sesión en .perfil_visor. Las evidencias pueden contener datos de tu empresa.\nEl visor captura páginas; no modifica registros ni comparte archivos automáticamente.", wraplength=620).pack(anchor="w")
        threading.Thread(target=self.worker, daemon=True).start()
        root.after(200, self.poll)

    def open_browser(self):
        if self.port:
            self.status.set("Chrome ya fue abierto. Inicia sesión y pulsa Conectar sesión.")
            return
        try:
            executable = chrome_path()
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                self.port = sock.getsockname()[1]
            subprocess.Popen([str(executable), f"--remote-debugging-port={self.port}",
                              "--remote-debugging-address=127.0.0.1", f"--user-data-dir={PROFILE}",
                              "--no-first-run", LOGIN])
            (DATA / "conexion.json").write_text(json.dumps({"puerto": self.port}), encoding="utf-8")
            self.status.set("Chrome abierto. Completa el acceso allí y pulsa Conectar sesión.")
        except Exception as exc:
            self.port = None
            messagebox.showerror("No se pudo abrir Chrome", str(exc))

    def worker(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.events.put("Falta Playwright. Ejecuta instalar_visor.ps1.")
            return
        with sync_playwright() as pw:
            browser = None
            while True:
                try:
                    task = self.tasks.get(timeout=0.5)
                except queue.Empty:
                    if browser:
                        # Procesa eventos y peticiones locales de captura para la auditoría.
                        try:
                            if browser.contexts and browser.contexts[0].pages:
                                browser.contexts[0].pages[0].wait_for_timeout(50)
                            if COMMAND.exists():
                                request = json.loads(COMMAND.read_text(encoding="utf-8"))
                                COMMAND.unlink()
                                if request.get("accion") == "capturar":
                                    self.tasks.put("capture")
                        except Exception as exc:
                            self.events.put(f"Sesión: {exc}")
                            browser = None
                    continue
                try:
                    if task == "connect":
                        if not self.port:
                            raise RuntimeError("Pulsa Abrir Chrome primero.")
                        browser = pw.chromium.connect_over_cdp(f"http://127.0.0.1:{self.port}")
                        self.events.put("Conectado. Navega a BusCMMS y pulsa Capturar página.")
                    elif task == "google":
                        if not self.port:
                            raise RuntimeError("Pulsa Abrir Chrome primero.")
                        if not browser or not browser.is_connected():
                            browser = pw.chromium.connect_over_cdp(f"http://127.0.0.1:{self.port}")
                        pages = [p for c in browser.contexts for p in c.pages
                                 if urlsplit(p.url).hostname == "ai.buscmms.com"]
                        page = pages[-1] if pages else browser.contexts[0].new_page()
                        if "login" not in urlsplit(page.url).path:
                            if urlsplit(page.url).hostname == "ai.buscmms.com":
                                self.events.put("Ya estás dentro de BusCMMS. Puedes capturar la página.")
                                continue
                            page.goto(LOGIN, wait_until="domcontentloaded", timeout=30000)
                        page.bring_to_front()
                        pattern = re.compile(r"continuar con google|continue with google|sign in with google", re.I)
                        button = page.get_by_role("button", name=pattern)
                        if not button.count():
                            button = page.get_by_role("link", name=pattern)
                        if not button.count():
                            button = page.get_by_text(pattern)
                        button.first.click(timeout=15000)
                        self.events.put("Acceso con Google iniciado. Elige tu cuenta y completa la verificación en Chrome; después captura una página de BusCMMS.")
                    elif task == "capture":
                        if not browser or not browser.is_connected():
                            raise RuntimeError("Conecta la sesión primero.")
                        pages = [p for c in browser.contexts for p in c.pages
                                 if urlsplit(p.url).hostname == "ai.buscmms.com"]
                        if not pages:
                            raise RuntimeError("No hay pestañas de BusCMMS abiertas.")
                        active = [p for p in pages if p.evaluate("document.visibilityState === 'visible'")]
                        folder = capture((active or pages)[-1])
                        self.events.put(f"Evidencia guardada: {folder.name}")
                except Exception as exc:
                    self.events.put(f"No se completó: {exc}")

    def poll(self):
        while not self.events.empty():
            self.status.set(self.events.get())
        self.root.after(200, self.poll)


if __name__ == "__main__":
    window = tk.Tk()
    Viewer(window)
    window.mainloop()
