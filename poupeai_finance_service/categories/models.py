from poupeai_finance_service.core.models import TimeStampedModel
from poupeai_finance_service.users.models import Profile
from django.db import models

class Category(TimeStampedModel):
    CATEGORY_TYPES = (
        ('expense', 'Despesa'),
        ('income', 'Receita')
    )
    name = models.CharField(max_length=30, verbose_name="Category Name", 
                            blank=False, null=False)
    color_hex = models.CharField(max_length=7, verbose_name='Category Color', 
                                 default='#000000', null=False, blank=False)
    type = models.CharField(max_length=7, verbose_name="Category Type", choices=CATEGORY_TYPES)
    profile_id = models.ForeignKey(to=Profile, verbose_name='User', on_delete=models.CASCADE)
    
    def __str__(self):
        return self.name