from django.db import models
from assets.models import AssetCategory

class Category(AssetCategory):
    class Meta:
        proxy = True
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
