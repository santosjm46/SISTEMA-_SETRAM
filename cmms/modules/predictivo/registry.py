from cmms.module import Module, MANAGERS, ALL
from cmms import models as m
MODULES=[
    Module('predictivo','Mantenimiento predictivo','Evaluación','Mantenimiento',m.PredictiveAssessment,(),(('bus','Bus'),('score','Riesgo'),('level','Nivel'),('created_at','Calculado')),create=(),edit=(),search=('level',),route='predictive:index'),
    Module('recomendaciones','Recomendaciones técnicas','Recomendación','Mantenimiento',m.PredictionRecommendation,('status','review_notes'),(('bus','Bus'),('title','Recomendación'),('status','Estado'),('created_at','Generada')),create=(),edit=MANAGERS,search=('title','explanation')),
]
MODULES[1].fields+=('estimated_cost','potential_savings','economic_basis')
