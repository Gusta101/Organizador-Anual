from django.contrib import admin
from .models import (
    Conta, CartaoCredito, Categoria, RegraCategorizacao, 
    TransacaoRecorrente, TransacaoPrevista, TransacaoEfetivada, TransferenciaInterna
)

admin.site.register(Conta)
admin.site.register(CartaoCredito)
admin.site.register(Categoria)
admin.site.register(RegraCategorizacao)
admin.site.register(TransacaoRecorrente)
admin.site.register(TransacaoPrevista)
admin.site.register(TransferenciaInterna)

@admin.register(TransacaoEfetivada)
class TransacaoEfetivadaAdmin(admin.ModelAdmin):
    list_display = ('descricao_banco', 'valor', 'data_efetivacao', 'tipo', 'conta', 'categoria')
    list_filter = ('tipo', 'data_efetivacao', 'conta')
    search_fields = ('descricao_banco', 'descricao_customizada')