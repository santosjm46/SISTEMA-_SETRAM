from .core_models import *
from .modules.telemetria.models import TelemetryDevice, TelemetryReading, IntegrationKey
from .modules.predictivo.models import PredictiveAssessment, PredictionRecommendation
from .modules.operacion.models import ServiceRoute, ShiftLog, TripLog, OperatingPolicy
from .modules.inspecciones.models import InspectionReminder, Notification
from .modules.seguridad.models import ComplianceRequirement, Recall, SafetyIncident
from .modules.documentos.models import DocumentAnalysis, Camera, CameraObservation
from .modules.administracion.models import Budget, Contract, Invoice,DepartmentShift,ScheduledReport,ReportRun,CatalogImport
from .modules.mantenimiento.models import ServiceTask, WorkOrderTask,WorkOrderComment,FailureType
from .modules.personal.models import TeamInvitation,TeamJoinRequest,ReactivationRequest
from .modules.flota.models import BusPhoto
from .modules.inventario.models import PurchaseLine,PurchaseReceipt,PurchaseDemand,PartCategory
from .modules.documentos.vision_models import VisionFrame,VisionDetection
