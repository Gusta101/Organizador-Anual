from django.urls import path
from . import views

app_name = 'financeiro'

urlpatterns = [
    path('', views.dashboard_financeiro, name='home'),
    path('orcamentos/', views.painel_orcamentos, name='painel_orcamentos'),
    path('objetivos/', views.painel_objetivos, name='painel_objetivos'),
    path('cron/aportes-automaticos/', views.cron_processar_aportes, name='cron_aportes'),
    path('api/detalhes-dia/', views.detalhes_dia_api, name='detalhes_dia_api'),
]