from dataclasses import dataclass
from . import models as m

MANAGERS = ('administrador','supervisor')
ALL = MANAGERS + ('tecnico','conductor')

@dataclass
class Module:
    key: str
    label: str
    singular: str
    section: str
    model: object
    fields: tuple
    columns: tuple
    read: tuple = ALL
    create: tuple = MANAGERS
    edit: tuple = MANAGERS
    search: tuple = ('title',)
    route: str = ''


def buses_for(user):
    buses = m.Bus.objects.filter(organization_id=user.organization_id)
    if user.role == 'conductor':
        buses = buses.filter(driver=user)
    elif user.role == 'tecnico':
        from django.db.models import Q
        buses = buses.filter(Q(workorder__assigned_to=user) | Q(inspectionreminder__assigned_to=user,inspectionreminder__active=True)).distinct()
    return buses


def scoped(module, user):
    if module.model is m.Organization: return m.Organization.objects.filter(pk=user.organization_id)
    qs = module.model.objects.filter(organization_id=user.organization_id)
    if module.model is m.Notification: return qs.filter(user=user)
    if module.model is m.Inspection and module.key=='informes_inspeccion': qs=qs.filter(kind='taller')
    if user.role in MANAGERS:
        return qs
    if module.model is m.Bus:
        return buses_for(user)
    if module.model is m.WorkOrder:
        return qs.filter(assigned_to=user)
    if module.model is m.BusPhoto: return qs.filter(bus__in=buses_for(user))
    if module.model is m.WorkOrderComment: return qs.filter(work_order__assigned_to=user)
    if module.model is m.MaintenanceRequest:
        return qs.filter(reported_by=user)
    if module.model is m.Inspection:
        qs=qs.filter(inspector=user)
        return qs.filter(kind='taller') if module.key=='informes_inspeccion' else qs
    if module.model is m.FuelEntry:
        return qs.filter(driver=user)
    if module.model in (m.PreventivePlan,m.Tire):
        return qs.filter(bus__in=buses_for(user))
    if module.model is m.Document:
        from django.db.models import Q
        return qs.filter(Q(user=user)|Q(user__isnull=True,work_order__isnull=True)&(Q(bus__in=buses_for(user))|Q(bus__isnull=True))|Q(user__isnull=True,work_order__assigned_to=user))
    if module.model in (m.ShiftLog,m.TripLog): return qs.filter(driver=user)
    if module.model in (m.TelemetryDevice,m.TelemetryReading,m.PredictiveAssessment,m.PredictionRecommendation,m.Recall):
        return qs.filter(bus__in=buses_for(user))
    if module.model is m.InspectionReminder: return qs.filter(assigned_to=user)
    if module.model is m.Notification: return qs.filter(user=user)
    if module.model is m.ComplianceRequirement: return qs.filter(responsible=user)
    if module.model is m.SafetyIncident: return qs.filter(reported_by=user)
    if module.model is m.DocumentAnalysis:
        from .registry import REGISTRY
        return qs.filter(document__in=scoped(REGISTRY['documentos'],user))
    if module.model is m.CameraObservation: return qs.filter(reported_by=user)
    if module.model is m.WorkOrderTask: return qs.filter(work_order__assigned_to=user)
    return qs


def enabled(user,key):
    if not user.organization_id: return False
    if key in ('visibilidad','personal','organizacion','comenzar'): return True
    flags=user.organization.enabled_modules
    return isinstance(flags,dict) and flags.get(key,True)
