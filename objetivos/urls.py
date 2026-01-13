from django.urls import path
from . import views

urlpatterns = [
    # Rota genérica (acessada pelo menu principal)
    path('novo/', views.criar_objetivo_unificado, name='criar_objetivo_geral'),
    
    # Rota contextual (acessada de dentro de um dashboard específico)
    # Ex: /objetivos/novo/ESTUDOS/
    path('novo/<str:modulo_origem>/', views.criar_objetivo_unificado, name='criar_objetivo_modulo'),
]