from django.urls import path
from . import views

app_name = 'financeiro'

urlpatterns = [
    path('', views.dashboard_financeiro, name='home'),
    path('orcamentos/', views.painel_orcamentos, name='painel_orcamentos'),
    path('objetivos/', views.painel_objetivos, name='painel_objetivos'),
    path('sincronizar/', views.forcar_sincronizacao, name='sincronizar'),
    path('fatura/<int:fatura_id>/pagar/', views.marcar_fatura_paga, name='marcar_fatura_paga'),
    path('transacao/<int:transacao_id>/revisar/', views.revisar_transacao, name='revisar_transacao'),
    path('cron/aportes-automaticos/', views.cron_processar_aportes, name='cron_aportes'),
    path('api/detalhes-dia/', views.detalhes_dia_api, name='detalhes_dia_api'),
]