from django.urls import path
from . import views

app_name = 'financeiro'

urlpatterns = [
    path('', views.dashboard_financeiro, name='home'),
    path('cartoes/nova-fatura/', views.nova_fatura, name='nova_fatura'),
    path('cartoes/pagar/<int:fatura_id>/', views.pagar_fatura, name='pagar_fatura'),
    path('cartoes/compra/<int:fatura_id>/', views.adicionar_compra_cartao, name='adicionar_compra_cartao'),
    path('orcamentos/', views.painel_orcamentos, name='painel_orcamentos'),
    path('orcamentos/novo/', views.novo_orcamento, name='novo_orcamento'),
    path('objetivos/', views.painel_objetivos, name='painel_objetivos'),
    path('objetivos/aporte/', views.novo_aporte, name='novo_aporte'),
    path('objetivos/regra-nova/', views.nova_regra_aporte, name='nova_regra_aporte'),
    path('conta/nova/', views.nova_conta, name='nova_conta'),
    path('categoria/nova/', views.nova_categoria, name='nova_categoria'),
    path('cron/aportes-automaticos/', views.cron_processar_aportes, name='cron_aportes'),
    path('api/detalhes-dia/', views.detalhes_dia_api, name='detalhes_dia_api'),
]