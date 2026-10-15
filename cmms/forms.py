from django import forms
import json
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from . import models as m
from .registry import buses_for


class RecordForm(forms.ModelForm):
    def __init__(self, *args, user, module, **kwargs):
        self.user, self.module = user, module
        super().__init__(*args, **kwargs)
        self.instance.organization_id = user.organization_id
        for name, field in self.fields.items():
            if hasattr(field,'queryset'):
                model = field.queryset.model
                field.queryset = field.queryset.filter(organization_id=user.organization_id)
                if model is m.Bus:
                    field.queryset = buses_for(user).exclude(status='baja')
                elif model is m.User:
                    field.queryset = field.queryset.filter(is_active=True)
                    if name=='driver': field.queryset=field.queryset.filter(role='conductor')
                    elif name=='assigned_to' and module.model is m.WorkOrder: field.queryset=field.queryset.filter(role__in=('tecnico','supervisor','administrador'))
                    if user.role=='conductor' and name=='driver': field.queryset=field.queryset.filter(pk=user.pk)
                elif model is m.WorkOrder:
                    field.queryset = field.queryset.exclude(status='cerrada')
                    if user.role=='tecnico': field.queryset=field.queryset.filter(assigned_to=user)
                elif model is m.Document:
                    from .registry import REGISTRY, scoped
                    field.queryset=scoped(REGISTRY['documentos'],user)
                elif model in (m.Checklist,m.ServiceProgram,m.ServiceTask):
                    field.queryset = field.queryset.filter(active=True)
                elif model is m.FailureType:
                    from django.db.models import Q
                    field.queryset=field.queryset.filter(Q(active=True)|Q(pk=getattr(self.instance,'failure_type_id',None)))
                    field.widget.attrs['data-failure-options']=json.dumps({str(row.pk):{'name':row.name,'system':row.system,'description':row.description} for row in field.queryset},ensure_ascii=False)
            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs['rows'] = 4
            if isinstance(field, forms.DateField) and not isinstance(field,forms.DateTimeField):
                field.widget = forms.DateInput(format='%Y-%m-%d',attrs={'type':'date'})
                field.input_formats = ['%Y-%m-%d']
            elif isinstance(field, forms.DateTimeField):
                field.widget = forms.DateTimeInput(format='%Y-%m-%dT%H:%M',attrs={'type':'datetime-local'})
                field.input_formats = ['%Y-%m-%dT%H:%M']
            field.widget.attrs['class'] = 'form-check-input' if isinstance(field.widget,forms.CheckboxInput) else 'form-select' if isinstance(field.widget,forms.Select) else 'form-control'
        if module.model is m.Part:
            self.fields['category'].widget.attrs['list']='partCategoryOptions'
            self.category_options=list(m.PartCategory.objects.filter(organization=user.organization,active=True).values_list('name',flat=True))
            self.fields['application_notes'].help_text='Confirma número OEM, medida y compatibilidad con el modelo antes de comprar o montar.'
        if module.model is m.WorkOrder and user.role == 'tecnico':
            for name in tuple(self.fields):
                if name not in ('resolution',):
                    del self.fields[name]
        elif module.model is m.WorkOrder and not self.instance.pk:
            self.fields['task_templates']=forms.ModelMultipleChoiceField(label='Tareas de la biblioteca',queryset=m.ServiceTask.objects.filter(organization=user.organization,active=True),required=False,widget=forms.SelectMultiple(attrs={'class':'form-select'}))
            self.fields['additional_tasks']=forms.CharField(label='Tareas adicionales (una por línea)',required=False,max_length=3000,widget=forms.Textarea(attrs={'class':'form-control','rows':4}))
        if module.model is m.User:
            self.fields['password'] = forms.CharField(label='Contraseña' if not self.instance.pk else 'Nueva contraseña (opcional)',required=not self.instance.pk,widget=forms.PasswordInput(attrs={'class':'form-control'}))
        if module.model is m.Inspection:
            if module.key=='informes_inspeccion':
                self.fields['kind'].choices=[('taller','Taller')]
                self.initial['kind']='taller'
            selected = self.data.get('checklist') if self.is_bound else self.initial.get('checklist')
            template = self.fields['checklist'].queryset.filter(pk=selected).first() if str(selected or '').isdigit() else self.fields['checklist'].queryset.first()
            if template:
                if not self.initial.get('checklist'): self.initial['checklist']=template.pk
                self.template = template
                for i, item in enumerate(template.items.splitlines()):
                    if item.strip():
                        self.fields[f'item_{i}'] = forms.ChoiceField(label=item.strip(),choices=[('','Selecciona resultado'),('aprobado','Conforme'),('defecto','Defecto menor'),('critico','Defecto crítico')],widget=forms.Select(attrs={'class':'form-select'}))
            self.fields['confirm'] = forms.BooleanField(label='Confirmo que realicé la inspección y los resultados son correctos.',widget=forms.CheckboxInput(attrs={'class':'form-check-input'}))

    def clean_password(self):
        return self.cleaned_data.get('password')

    def _post_clean(self):
        super()._post_clean()
        # Comparar la clave con el usuario ya construido por el ModelForm.
        password=self.cleaned_data.get('password')
        if password:
            try: validate_password(password,self.instance)
            except ValidationError as exc: self.add_error('password',exc)

    def clean(self):
        data = super().clean()
        for field in self.instance._meta.fields:
            if field.name in self.fields and field.blank and not field.null and field.has_default() and data.get(field.name) in (None,''):
                if not isinstance(field,m.models.BooleanField): data[field.name]=field.get_default()
        if self.module.model is m.WorkOrder and len((data.get('additional_tasks') or '').splitlines())>20:
            self.add_error('additional_tasks','Máximo veinte tareas adicionales.')
        if self.module.model is m.WorkOrder and data.get('failure_type'):
            data['failure_category']=data['failure_type'].system
        if self.module.model in (m.ShiftLog,m.TripLog) and self.user.role=='conductor':
            self.instance.driver=self.user
            if data.get('driver') and data['driver'].pk!=self.user.pk:
                self.add_error('driver','Solo puedes registrar tu propia actividad.')
        if self.module.model is m.PreventivePlan and data.get('program'):
            program=data['program']
            data['tasks']=data.get('tasks') or program.tasks
            data['interval_days']=data.get('interval_days') or program.interval_days
            data['interval_km']=data.get('interval_km') or program.interval_km
            data['interval_hours']=data.get('interval_hours') or program.interval_hours
        if self.module.model is m.User and self.instance.pk == self.user.pk:
            if data.get('role') != 'administrador' or not data.get('is_active'):
                raise ValidationError('No puedes quitarte el rol administrador ni desactivar tu propia cuenta.')
        if self.module.model is m.Inspection:
            template = data.get('checklist')
            if not template or not template.items.strip():
                raise ValidationError('Selecciona una plantilla activa con puntos de inspección.')
            answers = [{'punto':field.label,'resultado':data.get(name)} for name,field in self.fields.items() if name.startswith('item_')]
            if template and getattr(self,'template',None) and template.pk != self.template.pk:
                raise ValidationError('Recarga el formulario con la plantilla seleccionada.')
            results = {a['resultado'] for a in answers}
            self.instance.result = 'critico' if 'critico' in results else 'defecto' if 'defecto' in results else 'aprobado'
            self.instance.snapshot = {'plantilla':template.name,'version':template.version,'respuestas':answers}
            self.instance.inspector = self.user
            if self.instance.result != 'aprobado' and not data.get('findings','').strip():
                self.add_error('findings','Describe los defectos encontrados.')
        return data


def form_class(module):
    return forms.modelform_factory(module.model,form=RecordForm,fields=module.fields)
