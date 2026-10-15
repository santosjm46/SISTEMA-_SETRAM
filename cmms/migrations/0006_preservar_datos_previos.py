from django.db import migrations
from django.db.models import F

def preserve(apps,schema_editor):
    Purchase=apps.get_model('cmms','PurchaseOrder')
    Purchase.objects.filter(status='recibido',received_quantity=0).update(received_quantity=F('quantity'))
    Key=apps.get_model('cmms','IntegrationKey')
    for key in Key.objects.filter(scopes=[]).iterator():
        key.scopes=['telemetria'];key.save(update_fields=['scopes'])

class Migration(migrations.Migration):
    dependencies=[('cmms','0005_busphoto_catalogimport_departmentshift_and_more')]
    operations=[migrations.RunPython(preserve,migrations.RunPython.noop)]
