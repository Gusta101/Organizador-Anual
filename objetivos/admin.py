from django.contrib import admin
from django.contrib import messages
from .models import ObjetivoMacro, MetaDiaria
from .services import gera_metas_futuras

# Ação personalizada para rodar a lógica manualmente
@admin.action(description='Gerar Metas Futuras (Próx. 3 meses)')
def acao_gerar_metas(modeladmin, request, queryset):
    count = 0
    for objetivo in queryset:
        gera_metas_futuras(objetivo.id)
        count += 1
    
    modeladmin.message_user(
        request, 
        f"Processo finalizado! Metas geradas para {count} objetivo(s).", 
        messages.SUCCESS
    )

# Configuração visual das Metas Diárias dentro do Objetivo
class MetaDiariaInline(admin.TabularInline):
    model = MetaDiaria
    extra = 0
    # Campos que serão apenas leitura para evitar edição acidental em massa
    readonly_fields = ('data', 'valor_meta', 'realizado', 'valor_atingido')
    can_delete = False
    
    def has_add_permission(self, request, obj):
        return False # Evita criar meta manual solta pelo admin (opcional)

@admin.register(ObjetivoMacro)
class ObjetivoMacroAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'modulo', 'frequencia', 'tipo')
    list_filter = ('modulo', 'frequencia')
    actions = [acao_gerar_metas] # <--- AQUI LIGAMOS O BOTÃO/AÇÃO
    inlines = [MetaDiariaInline] # <--- AQUI MOSTRAMOS AS METAS DENTRO DO OBJETIVO

@admin.register(MetaDiaria)
class MetaDiariaAdmin(admin.ModelAdmin):
    list_display = ('objetivo', 'data', 'realizado', 'percentual_formatado')
    list_filter = ('data', 'realizado', 'objetivo__modulo')
    
    # Pequeno truque para mostrar o percentual bonito na lista
    @admin.display(description='% Concluído')
    def percentual_formatado(self, obj):
        return f"{obj.percentual:.1f}%"