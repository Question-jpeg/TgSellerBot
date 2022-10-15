from django.contrib import admin
from . import models

@admin.register(models.Category)
class CategoryAdmin(admin.ModelAdmin):
    pass

class ProductSizeInline(admin.TabularInline):
    model = models.ProductSize
    extra = 1

@admin.register(models.Product)
class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductSizeInline]

@admin.register(models.UserInfo)
class UserInfoAdmin(admin.ModelAdmin):
    pass

@admin.register(models.Config)
class ConfigAdmin(admin.ModelAdmin):
    pass

