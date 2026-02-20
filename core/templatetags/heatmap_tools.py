# core/templatetags/heatmap_tools.py
from django import template
from django.utils import timezone
import calendar

register = template.Library()

@register.inclusion_tag('includes/heatmap_component.html')
def render_heatmap(queryset, date_field='data', value_field='percentual'):
    MESES_PT = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
        5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
        9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }
    
    DIAS_SEMANA_PT = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb']
    
    # ... (Lógica de pegar ano/mes igual ao anterior) ...
    if queryset.exists():
        primeira_data = getattr(queryset.first(), date_field)
        ano, mes = primeira_data.year, primeira_data.month
    else:
        hoje = timezone.now()
        ano, mes = hoje.year, hoje.month

    # monthrange retorna: (dia_semana_inicio, total_dias)
    # dia_semana_inicio: 0=Segunda, 6=Domingo (Padrão Python)
    dia_semana_inicio, num_dias = calendar.monthrange(ano, mes)

    # Ajuste para calendário começar no DOMINGO:
    # Se Python diz 0 (Segunda), precisamos de 1 espaço (Domingo).
    # Se Python diz 6 (Domingo), precisamos de 0 espaços.
    dias_offset = (dia_semana_inicio + 1) % 7

    dados_map = {getattr(obj, date_field).day: obj for obj in queryset}
    
    grid = []

    # 1. Adiciona os dias vazios (Padding) do mês anterior
    for _ in range(dias_offset):
        grid.append({'dia': '', 'cor': 'transparent', 'is_padding': True})

    # 2. Adiciona os dias reais do mês
    for dia in range(1, num_dias + 1):
        obj = dados_map.get(dia)
        
        if obj:
            valor = getattr(obj, value_field, 0)
            valor = max(0, min(100, valor))
            tem_dado = True
            if valor == 0:
                cor = "#767676"
            else:
                alpha = max(0.2, valor / 100)
                cor = f"rgba(40, 167, 69, {alpha})"
        else:
            valor = 0
            cor = "#ebedf0" # Cinza claro para dia válido mas sem meta
            tem_dado = False

        grid.append({
            'dia': dia,
            'valor': valor,
            'cor': cor,
            'tem_dado': tem_dado,
            'is_padding': False
        })

    return {
        'grid': grid,
        'mes_nome': MESES_PT[mes],
        'ano': ano,
        'dias_semana': DIAS_SEMANA_PT
    }

@register.inclusion_tag('includes/heatmap_component.html')
def render_calendario_gastos(mes, ano, gastos_diarios_dict, max_valor):
    MESES_PT = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
        5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
        9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }
    DIAS_SEMANA_PT = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb']

    dia_semana_inicio, num_dias = calendar.monthrange(ano, mes)
    dias_offset = (dia_semana_inicio + 1) % 7

    grid = []

    # 1. Adiciona os dias vazios do mês anterior
    for _ in range(dias_offset):
        grid.append({'dia': '', 'cor': 'transparent', 'is_padding': True})

    # 2. Adiciona os dias reais do mês
    for dia in range(1, num_dias + 1):
        valor = gastos_diarios_dict.get(dia, 0)
        
        if valor > 0:
            tem_dado = True
            # Calcula a intensidade da cor vermelha baseada no maior gasto do mês
            # Usamos min/max para garantir que o alpha fica entre 0.2 (claro) e 1.0 (forte)
            intensidade = valor / max_valor if max_valor > 0 else 0
            alpha = max(0.2, min(1.0, intensidade))
            
            # Cor vermelha (rgb: 231, 76, 60 - a mesma do seu gráfico de barras)
            cor = f"rgba(231, 76, 60, {alpha})"
        else:
            tem_dado = False
            cor = "#ebedf0" # Dia sem gastos (cinza claro)

        grid.append({
            'dia': dia,
            'valor': f"R$ {valor:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.'), # Formata R$ 1.000,00
            'cor': cor,
            'tem_dado': tem_dado,
            'is_padding': False
        })

    return {
        'grid': grid,
        'mes_nome': MESES_PT[mes],
        'mes_num': mes,
        'ano': ano,
        'dias_semana': DIAS_SEMANA_PT,
        'is_financeiro': True # Uma flag para o HTML saber se coloca o símbolo de % ou de R$
    }
