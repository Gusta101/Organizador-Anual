from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Sum, Q
from django.utils import timezone

from objetivos.models import ObjetivoMacro
from .models import OrcamentoMensal, RegraAporteAutomatico, Transacao, Conta, FaturaCartao, CategoriaFinanceira, TransacaoCartao

import json
from datetime import date
import calendar

def adicionar_meses(data_original, meses):
    if hasattr(data_original, 'date') and callable(data_original.date):
        data_original = data_original.date()
        
    mes = data_original.month - 1 + meses
    ano = data_original.year + mes // 12
    mes = mes % 12 + 1
    dia = min(data_original.day, calendar.monthrange(ano, mes)[1])
    
    return date(ano, mes, dia)

def dashboard_financeiro(request):
    
    hoje = timezone.now()
    mes_atual = hoje.month
    ano_atual = hoje.year
    
    try:
        mes_selecionado = int(request.GET.get('mes', hoje.month))
        ano_selecionado = int(request.GET.get('ano', hoje.year))
    except ValueError:
        mes_selecionado = hoje.month
        ano_selecionado = hoje.year
    
    mes_anterior = mes_selecionado - 1 if mes_selecionado > 1 else 12
    ano_anterior = ano_selecionado if mes_selecionado > 1 else ano_selecionado - 1
    mes_seguinte = mes_selecionado + 1 if mes_selecionado < 12 else 1
    ano_seguinte = ano_selecionado if mes_selecionado < 12 else ano_selecionado + 1
    
    nomes_meses = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
    nome_mes_selecionado = nomes_meses[mes_selecionado]

    # ==========================================
    # 1. SALDO ATUAL E PROJETADO
    # ==========================================
    contas_ativas = Conta.objects.filter(ativa=True)
    saldo_geral = sum([conta.saldo_atual for conta in contas_ativas])

    ultimo_dia = calendar.monthrange(ano_selecionado, mes_selecionado)[1]
    data_limite_projecao = date(ano_selecionado, mes_selecionado, ultimo_dia)

    receitas_pendentes = Transacao.objects.filter(
        tipo='RECEITA', efetivada=False, data_vencimento__lte=data_limite_projecao
    ).aggregate(total=Sum('valor'))['total'] or 0

    despesas_pendentes = Transacao.objects.filter(
        tipo='DESPESA', efetivada=False, data_vencimento__lte=data_limite_projecao
    ).exclude(descricao__startswith='Pagamento Fatura').aggregate(total=Sum('valor'))['total'] or 0

    faturas_pendentes = FaturaCartao.objects.filter(paga=False).filter(
        Q(ano__lt=ano_selecionado) | Q(ano=ano_selecionado, mes__lte=mes_selecionado)
    )
    total_faturas_projecao = sum([float(f.compras.aggregate(t=Sum('valor'))['t'] or 0) for f in faturas_pendentes])

    saldo_projetado = float(saldo_geral) + float(receitas_pendentes) - float(despesas_pendentes) - total_faturas_projecao

    # ==========================================
    # 2. RECEITAS E DESPESAS DO MÊS SELECIONADO
    # ==========================================
    total_receitas = Transacao.objects.filter(
        tipo='RECEITA', data_vencimento__month=mes_selecionado, data_vencimento__year=ano_selecionado
    ).aggregate(total=Sum('valor'))['total'] or 0

    despesas_normais = Transacao.objects.filter(
        tipo='DESPESA', data_vencimento__month=mes_selecionado, data_vencimento__year=ano_selecionado
    ).exclude(descricao__startswith='Pagamento Fatura').aggregate(total=Sum('valor'))['total'] or 0
    
    despesas_cartao_mes = TransacaoCartao.objects.filter(
        fatura__mes=mes_selecionado, fatura__ano=ano_selecionado
    ).aggregate(total=Sum('valor'))['total'] or 0

    total_despesas = float(despesas_normais) + float(despesas_cartao_mes)
    
    # ==========================================
    # 3. FATURAS PARA A TELA (Atrasadas + Mês Atual + Mês Seguinte)
    # ==========================================
    faturas_abertas = FaturaCartao.objects.filter(paga=False).filter(
        Q(ano__lt=ano_seguinte) | Q(ano=ano_seguinte, mes__lte=mes_seguinte)
    ).order_by('data_vencimento')

    faturas_dados = []
    for fatura in faturas_abertas:
        gasto = fatura.compras.aggregate(total=Sum('valor'))['total'] or 0
        is_futura = (fatura.mes == mes_seguinte and fatura.ano == ano_seguinte)
        faturas_dados.append({
            'fatura': fatura,
            'total_gasto': gasto,
            'is_futura': is_futura,
        })

    # ==========================================
    # 4. GRÁFICO DE ROSCA (Juntando Conta + Cartão)
    # ==========================================
    gastos_transacoes = Transacao.objects.filter(
        tipo='DESPESA', data_vencimento__month=mes_selecionado, data_vencimento__year=ano_selecionado, efetivada=True
    ).exclude(descricao__startswith='Pagamento Fatura').values('categoria__nome', 'categoria__cor').annotate(total=Sum('valor'))

    gastos_cartao = TransacaoCartao.objects.filter(
        fatura__mes=mes_selecionado, fatura__ano=ano_selecionado
    ).values('categoria__nome', 'categoria__cor').annotate(total=Sum('valor'))

    categorias_dict = {}
    
    for g in gastos_transacoes:
        nome = g['categoria__nome'] or 'Outros'
        cor = g['categoria__cor'] or '#95a5a6'
        categorias_dict[nome] = {'cor': cor, 'total': float(g['total'])}

    for g in gastos_cartao:
        nome = g['categoria__nome'] or 'Outros'
        cor = g['categoria__cor'] or '#95a5a6'
        if nome in categorias_dict:
            categorias_dict[nome]['total'] += float(g['total'])
        else:
            categorias_dict[nome] = {'cor': cor, 'total': float(g['total'])}

    labels_grafico = list(categorias_dict.keys())
    valores_grafico = [d['total'] for d in categorias_dict.values()]
    cores_grafico = [d['cor'] for d in categorias_dict.values()]

    # ==========================================
    # 5. GRÁFICO DE BARRAS (ÚLTIMOS 6 MESES)
    # ==========================================
    meses_labels = []
    receitas_data = []
    despesas_data = []
    nomes_meses = ['', 'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

    for i in range(5, -1, -1):
        mes_calc = hoje.month - i
        ano_calc = hoje.year
        if mes_calc <= 0:
            mes_calc += 12
            ano_calc -= 1
            
        meses_labels.append(f'{nomes_meses[mes_calc]}/{str(ano_calc)[2:]}')
        
        rec = Transacao.objects.filter(
            tipo='RECEITA', data_vencimento__month=mes_calc, data_vencimento__year=ano_calc, efetivada=True
        ).aggregate(total=Sum('valor'))['total'] or 0
        receitas_data.append(float(rec))
        
        desp_t = Transacao.objects.filter(
            tipo='DESPESA', data_vencimento__month=mes_calc, data_vencimento__year=ano_calc, efetivada=True
        ).exclude(descricao__startswith='Pagamento Fatura').aggregate(total=Sum('valor'))['total'] or 0
        
        desp_c = TransacaoCartao.objects.filter(
            data_compra__month=mes_calc, data_compra__year=ano_calc
        ).aggregate(total=Sum('valor'))['total'] or 0
        
        despesas_data.append(float(desp_t) + float(desp_c))

    # Transações Recentes
    transacoes_recentes = Transacao.objects.all().select_related('categoria', 'conta').order_by('-data_vencimento', '-id')[:10]
    
    # ==========================================
    # 6. DADOS PARA O CALENDÁRIO HEATMAP
    # ==========================================
    gastos_diarios = {}
    
    despesas_cal = Transacao.objects.filter(
        tipo='DESPESA', data_vencimento__month=mes_selecionado, data_vencimento__year=ano_selecionado
    ).exclude(descricao__startswith='Pagamento Fatura').values('data_vencimento').annotate(total=Sum('valor'))
    
    for d in despesas_cal:
        dia = d['data_vencimento'].day
        gastos_diarios[dia] = gastos_diarios.get(dia, 0) + float(d['total'])

    cartao_cal = TransacaoCartao.objects.filter(
        data_compra__month=mes_selecionado, data_compra__year=ano_selecionado
    ).values('data_compra').annotate(total=Sum('valor'))
    
    for c in cartao_cal:
        dia = c['data_compra'].day
        gastos_diarios[dia] = gastos_diarios.get(dia, 0) + float(c['total'])

    maior_gasto_diario = max(gastos_diarios.values()) if gastos_diarios else 0

    context = {
        'mes_selecionado': mes_selecionado,
        'ano_selecionado': ano_selecionado,
        'nome_mes_selecionado': nome_mes_selecionado,
        'mes_anterior': mes_anterior,
        'ano_anterior': ano_anterior,
        'mes_seguinte': mes_seguinte,
        'ano_seguinte': ano_seguinte,
        
        'total_receitas': total_receitas,
        'total_despesas': total_despesas,
        'saldo': saldo_geral,
        'saldo_projetado': saldo_projetado,
        'faturas_dados': faturas_dados,
        
        'transacoes': transacoes_recentes,
        
        'labels_grafico': json.dumps(labels_grafico),
        'valores_grafico': json.dumps(valores_grafico),
        'cores_grafico': json.dumps(cores_grafico),
        'meses_labels': json.dumps(meses_labels),
        'receitas_data': json.dumps(receitas_data),
        'despesas_data': json.dumps(despesas_data),
        
        'gastos_diarios': gastos_diarios,
        'maior_gasto_diario': maior_gasto_diario,
    }

    return render(request, 'financeiro/dashboard.html', context)

def painel_orcamentos(request):
    hoje = timezone.now()
    mes_atual = hoje.month
    ano_atual = hoje.year

    orcamentos = OrcamentoMensal.objects.filter(mes=mes_atual, ano=ano_atual)
    dados_orcamento = []
    
    for orc in orcamentos:
        gasto = Transacao.objects.filter(
            categoria=orc.categoria,
            tipo='DESPESA',
            data_vencimento__month=mes_atual,
            data_vencimento__year=ano_atual,
            efetivada=True
        ).aggregate(total=Sum('valor'))['total'] or 0

        valor_limite = float(orc.valor_limite)
        gasto_float = float(gasto)
        percentual = (gasto_float / valor_limite * 100) if valor_limite > 0 else 0
        
        cor_barra = 'bg-success' 
        alerta = False
        
        if percentual >= 100:
            cor_barra = 'bg-danger' 
            alerta = True
        elif percentual >= 80:
            cor_barra = 'bg-warning' 
            alerta = True

        dados_orcamento.append({
            'orcamento': orc,
            'gasto': gasto,
            'restante': valor_limite - gasto_float,
            'percentual_real': percentual,
            'percentual_barra': min(percentual, 100), 
            'cor_barra': cor_barra,
            'alerta': alerta
        })

    categorias_despesa = CategoriaFinanceira.objects.filter(tipo='DESPESA')
    contas_ativas = Conta.objects.filter(ativa=True)
    saldo_geral = sum([conta.saldo_atual for conta in contas_ativas])

    context = {
        'dados_orcamento': dados_orcamento,
        'categorias': categorias_despesa,
        'mes_atual': mes_atual,
        'ano_atual': ano_atual,
        'saldo_geral': saldo_geral,
    }
    return render(request, 'financeiro/orcamentos.html', context)

def painel_objetivos(request):
    objetivos = ObjetivoMacro.objects.filter(modulo='FINANCEIRO')
    dados_objetivos = []
    
    for obj in objetivos:
        aportes = Transacao.objects.filter(
            objetivo_vinculado=obj,
            tipo='TRANSFERENCIA',
            efetivada=True
        ).aggregate(total=Sum('valor'))['total'] or 0

        valor_alvo = float(obj.meta_valor_total or 0)
        aportes_float = float(aportes)
        percentual = (aportes_float / valor_alvo * 100) if valor_alvo > 0 else 0
        
        dados_objetivos.append({
            'objetivo': obj,
            'guardado': aportes,
            'restante': valor_alvo - aportes_float if valor_alvo > 0 else 0,
            'percentual': min(percentual, 100),
            'concluido': percentual >= 100 and valor_alvo > 0
        })

    contas_ativas = Conta.objects.filter(ativa=True)
    regras_ativas = RegraAporteAutomatico.objects.filter(ativa=True)

    context = {
        'dados_objetivos': dados_objetivos,
        'contas_ativas': contas_ativas,
        'objetivos_lista': objetivos,
        'regras_ativas': regras_ativas,
    }
    return render(request, 'financeiro/objetivos.html', context)

def cron_processar_aportes(request):
    '''
    URL gatilho para ser chamada 1x por dia pelo Render/Cron-job.org.
    Pode adicionar um token na URL para segurança: /cron/aportes/?token=SEU_TOKEN_SECRETO
    '''
    # Medida de Segurança Básica (Opcional, mas recomendada no ambiente de produção)
    token = request.GET.get('token')
    if token != 'senha_super_secreta_123':
        return JsonResponse({'status': 'Erro', 'motivo': 'Acesso negado'}, status=403)

    hoje = timezone.now()
    mes_ano_atual = hoje.strftime('%m-%Y')

    regras_pendentes = RegraAporteAutomatico.objects.filter(ativa=True).exclude(ultimo_mes_processado=mes_ano_atual)
    aportes_gerados = 0

    for regra in regras_pendentes:
        Transacao.objects.create(
            descricao=f'Aporte Automático: {regra.objetivo.titulo}',
            tipo='TRANSFERENCIA',
            valor=regra.valor_fixo,
            data_vencimento=hoje.date(),
            data_pagamento=hoje.date(),
            conta=regra.conta_origem,
            objetivo_vinculado=regra.objetivo,
            efetivada=True
        )
        
        regra.ultimo_mes_processado = mes_ano_atual
        regra.save()
        aportes_gerados += 1

    return JsonResponse({
        'status': 'Sucesso',
        'mes_referencia': mes_ano_atual,
        'aportes_gerados': aportes_gerados
    })

def detalhes_dia_api(request):
    ano = request.GET.get('ano')
    mes = request.GET.get('mes')
    dia = request.GET.get('dia')

    if not (ano and mes and dia):
        return JsonResponse({'error': 'Parâmetros incompletos'}, status=400)

    data_alvo = date(int(ano), int(mes), int(dia))

    transacoes_dia = Transacao.objects.filter(
        data_vencimento=data_alvo
    ).exclude(descricao__startswith='Pagamento Fatura')

    cartoes_dia = TransacaoCartao.objects.filter(
        data_compra=data_alvo
    )

    lista_transacoes = []
    
    for t in transacoes_dia:
        lista_transacoes.append({
            'descricao': t.descricao,
            'valor': float(t.valor),
            'tipo': t.tipo, 
            'categoria': t.categoria.nome if t.categoria else 'Outros',
            'cor': t.categoria.cor if t.categoria else '#95a5a6',
            'conta': t.conta.nome
        })
        
    for c in cartoes_dia:
        lista_transacoes.append({
            'descricao': f"{c.descricao} (Cartão)",
            'valor': float(c.valor),
            'tipo': 'DESPESA',
            'categoria': c.categoria.nome if c.categoria else 'Outros',
            'cor': c.categoria.cor if c.categoria else '#95a5a6',
            'conta': c.fatura.nome_cartao
        })

    categorias_dict = {}
    for t in lista_transacoes:
        if t['tipo'] == 'DESPESA':
            cat = t['categoria']
            if cat not in categorias_dict:
                categorias_dict[cat] = {'cor': t['cor'], 'total': 0}
            categorias_dict[cat]['total'] += t['valor']

    return JsonResponse({
        'data_formatada': data_alvo.strftime('%d/%m/%Y'),
        'transacoes': lista_transacoes,
        'grafico': {
            'labels': list(categorias_dict.keys()),
            'valores': [d['total'] for d in categorias_dict.values()],
            'cores': [d['cor'] for d in categorias_dict.values()]
        }
    })
