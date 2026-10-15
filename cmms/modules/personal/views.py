import hashlib
import secrets
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction
from django.shortcuts import get_object_or_404,redirect,render
from django.utils import timezone
from django.urls import reverse
from cmms import models as m
from cmms.views import access
from cmms.modules.ui import page

@login_required
def invitations(request):
    access(request,'invitaciones')
    link=None
    if request.method=='POST':
        if request.POST.get('revocar'):
            obj=get_object_or_404(m.TeamInvitation,pk=request.POST['revocar'],organization=request.user.organization)
            obj.active=False; obj.save(update_fields=['active'])
            messages.success(request,'Invitación revocada.')
            return redirect('team:invitations')
        email=request.POST.get('email','').strip()
        role=request.POST.get('role','')
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError
        try:
            validate_email(email)
            if role not in dict(m.User.ROLES): raise ValidationError('Selecciona un rol válido.')
            secret=secrets.token_urlsafe(32)
            obj=m.TeamInvitation(organization=request.user.organization,email=email,role=role,
                created_by=request.user,digest=hashlib.sha256(secret.encode()).hexdigest(),expires_at=timezone.now()+timezone.timedelta(days=7))
            obj.full_clean(); obj.save()
            link=request.build_absolute_uri(reverse('team:accept',args=[obj.public_id]))+'#codigo='+secret
            from cmms.services import audit
            audit(request.user,'Invitación creada',obj,{'rol':role,'correo':email})
        except ValidationError as exc: messages.error(request,' '.join(exc.messages))
    return page(request,'invitaciones','cmms/modules/invitations.html',invitations=m.TeamInvitation.objects.filter(organization=request.user.organization),roles=m.User.ROLES,new_link=link)

class JoinForm(UserCreationForm):
    class Meta:
        model=m.User
        fields=('username','first_name','last_name')

def accept(request,public_id):
    obj=get_object_or_404(m.TeamInvitation,public_id=public_id)
    secret=request.POST.get('invite_secret','')
    valid=obj.available and (request.method=='GET' or secrets.compare_digest(obj.digest,hashlib.sha256(secret.encode()).hexdigest()))
    if not valid: return render(request,'registration/invitation.html',{'invalid':True},status=410)
    form=JoinForm(request.POST or None)
    for field in form.fields.values(): field.widget.attrs['class']='form-control'
    if request.method=='POST' and form.is_valid():
        with transaction.atomic():
            obj=m.TeamInvitation.objects.select_for_update().get(pk=obj.pk)
            if not obj.available: return render(request,'registration/invitation.html',{'invalid':True},status=410)
            user=form.save(commit=False)
            user.organization=obj.organization; user.role=obj.role; user.email=obj.email
            user.save()
            obj.accepted_at=timezone.now(); obj.save(update_fields=['accepted_at'])
            from cmms.services import audit
            audit(user,'Ingreso por invitación',user,{'rol':user.role})
        return redirect('login')
    return render(request,'registration/invitation.html',{'form':form,'invitation':obj})
