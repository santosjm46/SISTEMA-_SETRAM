"""Creación interactiva local del administrador inicial."""
import os
import tkinter as tk
from tkinter import messagebox, ttk

os.environ.setdefault('DJANGO_SETTINGS_MODULE','setram.settings')


def main():
    import django
    django.setup()
    from django.contrib.auth.password_validation import validate_password
    from django.db import transaction
    from cmms.models import User, Organization
    root = tk.Tk()
    root.title('SETRAM · Crear administrador')
    root.geometry('520x430')
    root.attributes('-topmost',True)
    root.after(1500,lambda:root.attributes('-topmost',False))
    frame = ttk.Frame(root,padding=25)
    frame.pack(fill='both',expand=True)
    ttk.Label(frame,text='Tu cuenta de administrador',font=('Segoe UI',17)).pack(anchor='w',pady=10)
    ttk.Label(frame,text='Esta contraseña pertenece a SETRAM CMMS,\nno a Google ni a PostgreSQL.').pack(anchor='w',pady=10)
    entries = {}
    for key,label,default in [('username','Usuario','admin'),('first_name','Nombre',''),('email','Correo',''),('password','Contraseña',''),('confirm','Repetir contraseña','')]:
        row = ttk.Frame(frame)
        row.pack(fill='x',pady=6)
        ttk.Label(row,text=label,width=19).pack(side='left')
        entry = ttk.Entry(row,show='*' if key in ('password','confirm') else '')
        entry.insert(0,default)
        entry.pack(side='left',fill='x',expand=True)
        entries[key]=entry

    def create():
        try:
            data={key:entry.get() for key,entry in entries.items()}
            if data.pop('confirm') != data['password']: raise ValueError('Las contraseñas no coinciden.')
            if not data['username'].strip(): raise ValueError('Indica un usuario.')
            with transaction.atomic():
                org=Organization.objects.order_by('pk').first()
                if org is None: raise ValueError('Inicializa SETRAM antes de crear el administrador.')
                if User.objects.filter(organization=org,role='administrador').exists():
                    raise ValueError('Ya existe un administrador. Usa Personal y roles para agregar cuentas.')
                password=data.pop('password')
                user=User(organization=org,role='administrador',**data)
                validate_password(password,user)
                user.set_password(password)
                user.full_clean()
                user.save()
            messagebox.showinfo('Cuenta creada','Administrador creado. Ingresa en http://127.0.0.1:8000 con esa cuenta.')
            root.destroy()
        except Exception as exc:
            messagebox.showerror('No se pudo crear la cuenta',str(exc))

    ttk.Button(frame,text='Crear administrador',command=create).pack(fill='x',pady=15)
    root.mainloop()


if __name__=='__main__':
    main()
