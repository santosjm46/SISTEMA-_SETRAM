import uuid
from django.db import models
from django.utils import timezone
from cmms.core_models import Record, User

class TeamInvitation(Record):
    public_id=models.UUIDField(default=uuid.uuid4,unique=True,editable=False)
    email=models.EmailField('Correo de la persona invitada')
    role=models.CharField('Rol',max_length=20,choices=User.ROLES)
    digest=models.CharField(max_length=64,editable=False)
    expires_at=models.DateTimeField('Vencimiento')
    accepted_at=models.DateTimeField('Aceptada',null=True,blank=True)
    created_by=models.ForeignKey(User,on_delete=models.PROTECT)
    active=models.BooleanField('Activa',default=True)
    @property
    def available(self):
        return (self.active and not self.accepted_at and self.expires_at>timezone.now()
                and self.created_by.is_active and self.created_by.role=='administrador'
                and self.created_by.organization_id==self.organization_id)
    def __str__(self): return self.email

class TeamJoinRequest(Record):
    username=models.CharField('Usuario solicitado',max_length=150)
    email=models.EmailField('Correo')
    first_name=models.CharField('Nombre',max_length=150,blank=True)
    last_name=models.CharField('Apellido',max_length=150,blank=True)
    password_hash=models.CharField(max_length=128,editable=False)
    requested_role=models.CharField('Rol solicitado',max_length=20,choices=[('conductor','Conductor'),('tecnico','Técnico')])
    status=models.CharField('Estado',max_length=20,choices=[('pendiente','Pendiente'),('aprobada','Aprobada'),('rechazada','Rechazada')],default='pendiente')
    review_notes=models.TextField('Revisión / verificación de identidad',blank=True)
    reviewed_by=models.ForeignKey(User,on_delete=models.PROTECT,null=True,blank=True,related_name='join_reviews')
    def __str__(self):return f'{self.username} · {self.get_status_display()}'

class ReactivationRequest(Record):
    user=models.ForeignKey(User,on_delete=models.PROTECT)
    reason=models.TextField('Motivo')
    status=models.CharField(max_length=20,choices=[('pendiente','Pendiente'),('aprobada','Aprobada'),('rechazada','Rechazada')],default='pendiente')
    reviewed_by=models.ForeignKey(User,on_delete=models.PROTECT,null=True,blank=True,related_name='reactivation_reviews')
    review_notes=models.TextField(blank=True)
    def __str__(self):return str(self.user)
    class Meta(Record.Meta):
        constraints=[models.UniqueConstraint(fields=['user'],condition=models.Q(status='pendiente'),name='cmms_one_pending_reactivation')]
