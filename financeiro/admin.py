from django.contrib import admin
from .models import (
    Conta, CategoriaFinanceira, OrcamentoMensal, Transacao,
    FaturaCartao, TransacaoCartao, RegraAporteAutomatico
)

@admin.register(Conta)
class ContaAdmin(admin.ModelAdmin):
    # saldo_atual é uma @property, o Django consegue exibi-la na lista!
    list_display = ('nome', 'tipo', 'saldo_inicial', 'saldo_atual', 'ativa', 'data_criacao')
    list_filter = ('tipo', 'ativa')
    search_fields = ('nome',)
    list_editable = ('ativa',) # Permite ativar/desativar direto na lista

@admin.register(CategoriaFinanceira)
class CategoriaFinanceiraAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'tipo', 'cor', 'icone')
    list_editable = ('nome', 'cor', 'icone') 
    list_display_links = ('id',)
    list_filter = ('tipo',)
    search_fields = ('nome',)

@admin.register(OrcamentoMensal)
class OrcamentoMensalAdmin(admin.ModelAdmin):
    list_display = ('categoria', 'mes', 'ano', 'valor_limite')
    list_filter = ('ano', 'mes', 'categoria')
    
@admin.register(Transacao)
class TransacaoAdmin(admin.ModelAdmin):
    list_display = ('descricao', 'tipo', 'valor', 'data_vencimento', 'conta', 'efetivada')
    list_filter = ('tipo', 'efetivada', 'conta', 'categoria', 'data_vencimento')
    search_fields = ('descricao',)
    date_hierarchy = 'data_vencimento' # Cria uma navegação por datas no topo
    list_editable = ('efetivada',) # Botão rápido para marcar como pago

# --- Configuração Avançada para Cartões de Crédito ---

# TabularInline permite adicionar transações DENTRO da tela da Fatura
class TransacaoCartaoInline(admin.TabularInline):
    model = TransacaoCartao
    extra = 1 # Quantas linhas em branco aparecem por padrão

@admin.register(FaturaCartao)
class FaturaCartaoAdmin(admin.ModelAdmin):
    list_display = ('nome_cartao', 'mes', 'ano', 'data_vencimento', 'data_fechamento', 'paga')
    list_filter = ('nome_cartao', 'paga', 'ano', 'mes')
    inlines = [TransacaoCartaoInline] # Adiciona as transações aqui dentro!
    list_editable = ('paga',)

@admin.register(TransacaoCartao)
class TransacaoCartaoAdmin(admin.ModelAdmin):
    list_display = ('descricao', 'fatura', 'categoria', 'valor', 'data_compra')
    list_filter = ('fatura__nome_cartao', 'categoria', 'data_compra')
    search_fields = ('descricao',)

@admin.register(RegraAporteAutomatico)
class RegraAporteAutomaticoAdmin(admin.ModelAdmin):
    list_display = ('objetivo', 'conta_origem', 'valor_fixo', 'ativa', 'ultimo_mes_processado')
    list_filter = ('ativa', 'conta_origem')
    search_fields = ('objetivo__titulo',)