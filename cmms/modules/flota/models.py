from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from cmms.core_models import Record,Bus,User

class BusPhoto(Record):
    bus=models.ForeignKey(Bus,on_delete=models.PROTECT,verbose_name='Bus')
    caption=models.CharField('Descripción de la foto',max_length=160,blank=True)
    image=models.FileField('Foto',upload_to='flota/%Y/%m/',validators=[FileExtensionValidator(['jpg','jpeg','png'])])
    uploaded_by=models.ForeignKey(User,on_delete=models.PROTECT,editable=False)
    def __str__(self): return self.caption or str(self.bus)
    def clean(self):
        super().clean()
        if self.image:
            if self.image.size>10*1024*1024: raise ValidationError({'image':'Máximo 10 MB.'})
            header=self.image.read(8); self.image.seek(0)
            if not (header.startswith(b'\xff\xd8\xff') or header==b'\x89PNG\r\n\x1a\n'): raise ValidationError({'image':'Selecciona una imagen JPEG o PNG.'})
        if self.bus_id and BusPhoto.objects.filter(bus=self.bus).exclude(pk=self.pk).count()>=5:
            raise ValidationError('El bus ya tiene cinco fotografías.')
