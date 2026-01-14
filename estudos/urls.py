from django.urls import path
from . import views

app_name = 'estudos'

urlpatterns = [
    path('', views.dashboard_estudos, name='home'),
    path('assunto/<int:assunto_id>/', views.detalhes_assunto, name='detalhes_assunto'),
    path('registrar_progresso/<int:meta_id>/', views.registrar_progresso, name='registrar_progresso'),
]