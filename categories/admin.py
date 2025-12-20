from django.contrib import admin
from .models import Category
from tenancy.admin_mixins import CompanyScopedAdmin

@admin.register(Category)
class CategoryAdmin(CompanyScopedAdmin):
    list_display = ('name',)
