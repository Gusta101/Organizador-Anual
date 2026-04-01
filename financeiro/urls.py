from django.urls import path
from . import views

app_name = 'financeiro'

urlpatterns = [
    path('', views.dashboard, name='home'),
    path('nova-prevista/', views.criar_transacao_prevista, name='criar_prevista'),
    path('nova-recorrente/', views.criar_transacao_recorrente, name='criar_recorrente'),
    path('importar/', views.importar_extrato, name='importar_extrato'),
]