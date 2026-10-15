from cmms.module import Module, MANAGERS, ALL
from cmms import models as m

MODULES=[
Module('personal','Personal y roles','Usuario','Administración',m.User,('username','first_name','last_name','email','phone','role','is_active'),(('username','Usuario'),('first_name','Nombre'),('last_name','Apellido'),('role','Rol'),('is_active','Activo')),read=('administrador',),create=('administrador',),edit=('administrador',),search=('username','first_name','last_name','email'))
]
for item in MODULES:
    item.section='Equipo'
MODULES[0].fields+=('employee_code','department','license_number','license_category','license_expiry')
MODULES.append(Module('invitaciones','Invitaciones de equipo','Invitación','Equipo',m.TeamInvitation,(),(('email','Correo'),('role','Rol'),('expires_at','Vencimiento'),('accepted_at','Aceptada')),read=('administrador',),create=(),edit=(),search=('email',),route='team:invitations'))
MODULES.extend([
    Module('ingresos_equipo','Aprobaciones de ingreso','Solicitud de ingreso','Equipo',m.TeamJoinRequest,(),(('username','Usuario'),('email','Correo'),('requested_role','Rol'),('status','Estado')),read=('administrador',),create=(),edit=(),search=('username','email')),
    Module('reactivaciones','Solicitudes de reactivación','Reactivación','Equipo',m.ReactivationRequest,(),(('user','Usuario'),('status','Estado'),('created_at','Solicitud')),read=('administrador',),create=(),edit=(),search=('user__username','reason')),
])
