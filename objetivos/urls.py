from django.urls import path
from . import views

app_name = 'objetivos'

urlpatterns = [
    path('novo/', views.criar_objetivo_unificado, name='criar_objetivo_geral'),
    
    path('novo/<str:modulo_origem>/', views.criar_objetivo_unificado, name='criar_objetivo_modulo'),
]