from django.urls import path
from . import views

app_name = 'financeiro'

urlpatterns = [
    path('sincronizar/', views.forcar_sincronizacao, name='sincronizar'),
]