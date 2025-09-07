from django.db import models
from django.utils import timezone


class Location(models.Model):
    address = models.CharField(
        'название',
        max_length=50,
        null=False,
        unique=True,
        db_index=True,
    )
    lon = models.DecimalField('Долгота', max_digits=9, decimal_places=6, null=True)
    lat = models.DecimalField('Широта', max_digits=9, decimal_places=6, null=True)
    created_at = models.DateTimeField(
        'Создано',
        null=True,
        db_index=True,
        blank=True,
    )

    class Meta:
        verbose_name = 'Локация'
        verbose_name_plural = 'Локации'

    def __str__(self):
        return self.address
