from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import redirect
from cmms import models as m
from cmms.registry import REGISTRY,MODULES
from cmms.views import access
from cmms.modules.ui import page

@login_required
def organization(request):
    access(request,'organizacion')
    org=request.user.organization
    return page(request,'organizacion','cmms/modules/organization.html',org=org,
        members=m.User.objects.filter(organization=org,is_active=True).count(),buses=m.Bus.objects.filter(organization=org).count())

@login_required
def visibility(request):
    access(request,'visibilidad')
    locked={'visibilidad','personal','organizacion','comenzar'}
    if request.method=='POST':
        selected=set(request.POST.getlist('modulos'))|locked
        with transaction.atomic():
            org=m.Organization.objects.select_for_update().get(pk=request.user.organization_id)
            org.enabled_modules={item.key:item.key in selected for item in MODULES}
            org.save(update_fields=['enabled_modules'])
            from cmms.services import audit
            audit(request.user,'Módulos actualizados',org,{'habilitados':sorted(selected&set(REGISTRY))})
        messages.success(request,'Módulos actualizados. Los roles mantienen sus restricciones.')
        return redirect('administration:visibility')
    flags=request.user.organization.enabled_modules
    rows=[{'module':item,'active':flags.get(item.key,True),'locked':item.key in locked} for item in MODULES]
    return page(request,'visibilidad','cmms/modules/visibility.html',rows=rows)

@login_required
def finance(request):
    access(request,'facturacion')
    invoices=m.Invoice.objects.filter(organization=request.user.organization)
    budgets=[]
    for budget in m.Budget.objects.filter(organization=request.user.organization):
        committed=invoices.filter(budget=budget).exclude(status='anulada').aggregate(total=Sum('amount'))['total'] or 0
        paid=invoices.filter(budget=budget,status='pagada').aggregate(total=Sum('amount'))['total'] or 0
        budgets.append({'obj':budget,'committed':committed,'paid':paid,'balance':budget.amount-committed})
    return page(request,'facturacion','cmms/modules/finance.html',budgets=budgets,invoices=invoices.select_related('supplier')[:30],
        stats=[{'label':'Comprobantes registrados','value':invoices.count()},
               {'label':'Pendiente de pago (Bs)','value':str(invoices.filter(status='pendiente').aggregate(total=Sum('amount'))['total'] or 0)},
               {'label':'Pagado (Bs)','value':str(invoices.filter(status='pagada').aggregate(total=Sum('amount'))['total'] or 0)},
               {'label':'Presupuestos','value':len(budgets)}])
