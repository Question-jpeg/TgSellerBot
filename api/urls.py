from django.urls import path, include
from .views import tbot

urlpatterns = [
    path('e915ea40-a31a-4859-a7ac-b4ecc75bc27b/', tbot, name='bot')
]