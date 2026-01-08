from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_estudos, name='estudos'),
    path('registrar_progresso/<int:meta_id>/', views.registrar_progresso, name='registrar_progresso'),
]