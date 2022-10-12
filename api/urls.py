from django.urls import path, include
from .views import bot

urlpatterns = [
    path('cbbf15d8-0421-4512-12a6-5e5d977e3aef/', bot, name='bot')
]