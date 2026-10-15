from django import forms
from cmms.models import Organization,User
from cmms.modules.inspecciones.services import TOPICS

class OrganizationSettingsForm(forms.ModelForm):
    class Meta:
        model=Organization
        fields=('name','tax_id','address','contact_email','phone','default_labor_rate','notifications_enabled','kpi_alerts_enabled','minimum_availability','minimum_inspection_approval','minimum_tread_mm')
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        for field in self.fields.values():field.widget.attrs['class']='form-check-input' if isinstance(field.widget,forms.CheckboxInput) else 'form-control'
        matrix=self.instance.notification_matrix or {}
        self.role_groups=[]
        for role,title in User.ROLES:
            names=[]
            for kind,label in TOPICS:
                name=f'notice_{role}_{kind}';names.append(name)
                self.fields[name]=forms.BooleanField(label=label,required=False,initial=matrix.get(role,{}).get(kind,True),widget=forms.CheckboxInput(attrs={'class':'form-check-input'}))
            self.role_groups.append({'title':title,'fields':[self[name] for name in names]})
    def clean(self):
        data=super().clean()
        self.instance.notification_matrix={role:{kind:bool(data.get(f'notice_{role}_{kind}')) for kind,_ in TOPICS} for role,_ in User.ROLES}
        return data
