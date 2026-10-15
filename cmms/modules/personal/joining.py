import io
from django import forms
from django.core import signing
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied,ValidationError
from django.db import transaction,IntegrityError
from django.http import HttpResponse,Http404
from django.shortcuts import get_object_or_404,render
from cmms import models as m

SALT='setram-join-request-v1'

class RequestForm(UserCreationForm):
    email=forms.EmailField(label='Correo institucional')
    requested_role=forms.ChoiceField(label='Rol solicitado',choices=[('conductor','Conductor'),('tecnico','Técnico')])
    class Meta:
        model=m.User
        fields=('username','first_name','last_name','email','requested_role')
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        for field in self.fields.values():field.widget.attrs['class']='form-control'

@login_required
def qr(request):
    if request.user.role!='administrador' or not request.user.organization_id:raise PermissionDenied
    from cmms.views import access
    access(request,'ingresos_equipo')
    from django.urls import reverse
    import qrcode
    from qrcode.image.svg import SvgPathImage
    token=signing.dumps({'org':request.user.organization_id,'issuer':request.user.pk},salt=SALT)
    uri=request.build_absolute_uri(reverse('team-join',args=[token]))
    picture=qrcode.make(uri,image_factory=SvgPathImage);output=io.BytesIO();picture.save(output)
    return HttpResponse(output.getvalue(),content_type='image/svg+xml')

def join(request,token):
    try:
        payload=signing.loads(token,salt=SALT,max_age=7*24*3600)
        org=m.Organization.objects.get(pk=payload['org'])
        if not org.enabled_modules.get('ingresos_equipo',True):raise ValueError()
        if not m.User.objects.filter(pk=payload['issuer'],organization=org,role='administrador',is_active=True).exists():raise ValueError()
    except (signing.BadSignature,KeyError,ValueError,m.Organization.DoesNotExist):return render(request,'registration/join_request.html',{'invalid':True},status=410)
    form=RequestForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        prospective=form.save(commit=False);prospective.set_password(form.cleaned_data['password1'])
        m.TeamJoinRequest.objects.create(organization=org,username=prospective.username,email=form.cleaned_data['email'],first_name=prospective.first_name,last_name=prospective.last_name,
            password_hash=prospective.password,requested_role=form.cleaned_data['requested_role'])
        return render(request,'registration/join_request.html',{'sent':True})
    return render(request,'registration/join_request.html',{'form':form})

@transaction.atomic
def decide(user,key,pk,status,notes):
    if user.role!='administrador':raise PermissionDenied
    if status not in ('aprobada','rechazada') or not notes.strip():raise ValidationError('Registra la decisión y la verificación de identidad.')
    model=m.TeamJoinRequest if key=='ingresos_equipo' else m.ReactivationRequest
    obj=model.objects.select_for_update().get(pk=pk,organization=user.organization)
    if obj.status!='pendiente':return obj
    if status=='aprobada':
        if key=='ingresos_equipo':
            if obj.requested_role not in ('conductor','tecnico'):raise ValidationError('Rol solicitado no admitido.')
            account=m.User(organization=obj.organization,username=obj.username,email=obj.email,first_name=obj.first_name,last_name=obj.last_name,role=obj.requested_role,password=obj.password_hash)
            account.full_clean(exclude=['password'])
            try:account.save()
            except IntegrityError:raise ValidationError('El usuario ya está registrado. Revisa la solicitud antes de aprobar.')
        else:
            account=m.User.objects.select_for_update().get(pk=obj.user_id,organization=obj.organization)
            account.is_active=True;account.save(update_fields=['is_active'])
    obj.status=status;obj.reviewed_by=user;obj.review_notes=notes
    if key=='ingresos_equipo':obj.password_hash=''
    obj.save()
    from cmms.services import audit
    audit(user,'Ingreso revisado' if key=='ingresos_equipo' else 'Reactivación revisada',obj,{'estado':status})
    return obj

def reactivation(request):
    class ReactivationForm(forms.Form):
        email=forms.EmailField(label='Correo de la cuenta')
        reason=forms.CharField(label='Motivo',max_length=1000,widget=forms.Textarea)
    form=ReactivationForm(request.POST or None)
    for field in form.fields.values():field.widget.attrs['class']='form-control'
    if request.method=='POST' and form.is_valid():
        for account in m.User.objects.filter(email__iexact=form.cleaned_data['email'],is_active=False,organization__isnull=False)[:10]:
            m.ReactivationRequest.objects.get_or_create(user=account,organization=account.organization,status='pendiente',defaults={'reason':form.cleaned_data['reason']})
        return render(request,'registration/join_request.html',{'reactivation':True,'sent':True})
    return render(request,'registration/join_request.html',{'form':form,'reactivation':True})
