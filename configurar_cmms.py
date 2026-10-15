"""Configuración local: las credenciales se introducen en el equipo."""
import json
import secrets
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

ROOT = Path(__file__).resolve().parent


def main():
    root = tk.Tk()
    root.title('SETRAM · Conectar PostgreSQL CMMS')
    root.geometry('520x420')
    root.attributes('-topmost', True)
    root.after(1500, lambda: root.attributes('-topmost', False))
    frame = ttk.Frame(root, padding=24)
    frame.pack(fill='both', expand=True)
    ttk.Label(frame, text='Conectar la base CMMS', font=('Segoe UI', 18)).pack(anchor='w')
    ttk.Label(frame, text='Introduce las credenciales de PostgreSQL local.\nSe guardan únicamente en .env dentro de este proyecto.').pack(anchor='w', pady=12)
    entries = {}
    for key, label, default in [('DB_HOST','Servidor','127.0.0.1'),('DB_PORT','Puerto','5432'),('DB_USER','Usuario','postgres'),('DB_PASSWORD','Contraseña','')]:
        row = ttk.Frame(frame)
        row.pack(fill='x', pady=5)
        ttk.Label(row, text=label, width=14).pack(side='left')
        entry = ttk.Entry(row, show='*' if key == 'DB_PASSWORD' else '')
        entry.insert(0, default)
        entry.pack(side='left', fill='x', expand=True)
        entries[key] = entry

    def save():
        try:
            import psycopg
            values = {key: entry.get() for key, entry in entries.items()}
            with psycopg.connect(dbname='CMMS', host=values['DB_HOST'], port=values['DB_PORT'],
                                 user=values['DB_USER'], password=values['DB_PASSWORD'], connect_timeout=5) as conn:
                with conn.cursor() as cursor:
                    cursor.execute('SELECT current_database()')
                    if cursor.fetchone()[0] != 'CMMS':
                        raise ValueError('La conexión no corresponde a CMMS.')
            target = ROOT / '.env'
            if target.exists():
                from dotenv import dotenv_values
                previous = dotenv_values(target)
            else:
                previous = {}
            values.update({'DB_NAME':'CMMS','DJANGO_SECRET_KEY':previous.get('DJANGO_SECRET_KEY') or secrets.token_urlsafe(48),
                           'DEBUG':'true','ALLOWED_HOSTS':'127.0.0.1,localhost','TIME_ZONE':'America/La_Paz'})
            target.write_text('\n'.join(key+'='+json.dumps(value,ensure_ascii=False) for key,value in values.items())+'\n',encoding='utf-8')
            messagebox.showinfo('Conexión confirmada','CMMS conectada. Ya puedes cerrar esta ventana y continuar con el desarrollo.')
            root.destroy()
        except Exception as exc:
            messagebox.showerror('No se pudo conectar', str(exc))

    ttk.Button(frame, text='Comprobar y guardar conexión', command=save).pack(fill='x', pady=20)
    root.mainloop()


if __name__ == '__main__':
    main()
