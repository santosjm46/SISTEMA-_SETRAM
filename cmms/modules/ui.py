from django.shortcuts import render
from cmms.registry import REGISTRY

def page(request,key,template,**context):
    module=REGISTRY[key]
    context.update({'module':module,'page_title':module.label,'extended_workspace':True})
    return render(request,template,context)
