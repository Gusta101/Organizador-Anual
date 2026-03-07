from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.db.models import Sum, Q
from django.utils import timezone
from django.contrib import messages

from objetivos.models import ObjetivoMacro
from .models import OrcamentoMensal, RegraAporteAutomatico, Transacao, Conta, FaturaCartao, CategoriaFinanceira, TransacaoCartao

import json
from datetime import date
import calendar

from .pluggy_service import ACCOUNT_ID_CORRENTE, buscar_saldo_real_api, obter_token_pluggy, sincronizar_conta_corrente, sincronizar_cartao_credito

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
    nome_mes_seguinte = nomes_meses[mes_seguinte]

    # ==========================================
    # 1. RECEITAS E DESPESAS (Corrente)
    # ==========================================
    total_receitas = Transacao.objects.filter(tipo='RECEITA', data_vencimento__month=mes_atual, data_vencimento__year=ano_atual).aggregate(total=Sum('valor'))['total'] or 0
    despesas_normais = Transacao.objects.filter(tipo='DESPESA', data_vencimento__month=mes_atual, data_vencimento__year=ano_atual).aggregate(total=Sum('valor'))['total'] or 0
    
    # ==========================================
    # 2. SEPARAÇÃO DAS FATURAS (Apenas Alertas e Previsão)
    # ==========================================
    # A) A Fatura deste mês (a que vence agora)
    faturas_atual = FaturaCartao.objects.filter(mes=mes_selecionado, ano=ano_selecionado)
    total_fatura_atual_pendente = 0
    faturas_pendentes_alerta = []

    for f in faturas_atual:
        gasto_total = float(f.compras.aggregate(t=Sum('valor'))['t'] or 0)
        valor_ja_pago = float(f.valor_pago)
        
        if not f.paga:
            # O sistema agora só desconta da sua previsão de saldo o que falta pagar!
            restante = gasto_total - valor_ja_pago
            total_fatura_atual_pendente += restante 
            faturas_pendentes_alerta.append({
                'id': f.id, 'nome': f.nome_cartao, 
                'valor_total': gasto_total, 'valor_pago': valor_ja_pago, 'restante': restante
            })

    # B) A Fatura em Andamento (A que vence o mês que vem)
    faturas_andamento = FaturaCartao.objects.filter(mes=mes_seguinte, ano=ano_seguinte)
    total_fatura_andamento = sum(float(f.compras.aggregate(t=Sum('valor'))['t'] or 0) for f in faturas_andamento)

    # ==========================================
    # SALDOS FINAIS: REGIME DE CAIXA (O QUE SAIU ESTE MÊS)
    # ==========================================
    # Busca APENAS as transferências deste mês que são pagamentos de fatura
    pagamentos_fatura_mes = Transacao.objects.filter(
        tipo='TRANSFERENCIA',
        data_vencimento__month=mes_selecionado, 
        data_vencimento__year=ano_selecionado,
        efetivada=True
    ).filter(
        Q(descricao__icontains='fatura') | 
        Q(descricao__icontains='pagamento cartão') |
        Q(descricao__icontains='pagamento crédito')
    ).aggregate(total=Sum('valor'))['total'] or 0

    # Despesas do Card = Dinheiro gasto na conta (PIX/Débito) + Pagamentos de fatura FEITOS NESTE MÊS
    total_despesas = float(despesas_normais) + float(pagamentos_fatura_mes)

    # === FORÇAR O SALDO EXATO DA API ===
    token_temp = obter_token_pluggy()
    # Pega o saldo fresco e em tempo real direto do banco
    saldo_geral = buscar_saldo_real_api(ACCOUNT_ID_CORRENTE, token_temp) if token_temp else 0

    # Previsão = Saldo Real - O que deve da fatura de agora - O que já gastou na do mês que vem
    saldo_projetado = float(saldo_geral) - total_fatura_atual_pendente - total_fatura_andamento
    
    # ==========================================
    # (GRÁFICOS E HEATMAP MANTIDOS IGUAIS)
    # ==========================================
    gastos_transacoes = Transacao.objects.filter(
        tipo='DESPESA', data_vencimento__month=mes_selecionado, data_vencimento__year=ano_selecionado, efetivada=True
    ).values('categoria__nome', 'categoria__cor').annotate(total=Sum('valor'))

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

    meses_labels, receitas_data, despesas_data = [], [], []
    for i in range(5, -1, -1):
        mes_calc = hoje.month - i
        ano_calc = hoje.year
        if mes_calc <= 0:
            mes_calc += 12; ano_calc -= 1
        meses_labels.append(f'{nomes_meses[mes_calc]}/{str(ano_calc)[2:]}')
        rec = Transacao.objects.filter(tipo='RECEITA', data_vencimento__month=mes_calc, data_vencimento__year=ano_calc, efetivada=True).aggregate(total=Sum('valor'))['total'] or 0
        receitas_data.append(float(rec))
        desp_t = Transacao.objects.filter(tipo='DESPESA', data_vencimento__month=mes_calc, data_vencimento__year=ano_calc, efetivada=True).aggregate(total=Sum('valor'))['total'] or 0
        desp_c = TransacaoCartao.objects.filter(data_compra__month=mes_calc, data_compra__year=ano_calc).aggregate(total=Sum('valor'))['total'] or 0
        despesas_data.append(float(desp_t) + float(desp_c))

    gastos_diarios = {}
    despesas_cal = Transacao.objects.filter(tipo='DESPESA', data_vencimento__month=mes_selecionado, data_vencimento__year=ano_selecionado).values('data_vencimento').annotate(total=Sum('valor'))
    for d in despesas_cal: gastos_diarios[d['data_vencimento'].day] = gastos_diarios.get(d['data_vencimento'].day, 0) + float(d['total'])
    cartao_cal = TransacaoCartao.objects.filter(data_compra__month=mes_selecionado, data_compra__year=ano_selecionado).values('data_compra').annotate(total=Sum('valor'))
    for c in cartao_cal: gastos_diarios[c['data_compra'].day] = gastos_diarios.get(c['data_compra'].day, 0) + float(c['total'])
    maior_gasto_diario = max(gastos_diarios.values()) if gastos_diarios else 0

    transacoes_recentes = Transacao.objects.all().select_related('categoria', 'conta').order_by('-data_vencimento', '-id')[:10]
    
    transacoes_pendentes = Transacao.objects.filter(revisada=False).order_by('-data_vencimento')[:20]
    todas_categorias = CategoriaFinanceira.objects.all().order_by('nome')

    context = {
        'mes_selecionado': mes_selecionado, 'ano_selecionado': ano_selecionado, 'nome_mes_selecionado': nome_mes_selecionado,
        
        'nome_mes_seguinte': nome_mes_seguinte,
        
        'mes_anterior': mes_anterior, 'ano_anterior': ano_anterior, 'mes_seguinte': mes_seguinte, 'ano_seguinte': ano_seguinte,
        
        'total_receitas': total_receitas, 'total_despesas': total_despesas, 'saldo': saldo_geral, 
        
        'saldo_projetado': saldo_projetado, 
        
        'total_fatura_andamento': total_fatura_andamento, 
        'faturas_pendentes_alerta': faturas_pendentes_alerta,
        
        'transacoes': transacoes_recentes,
        'transacoes_pendentes': transacoes_pendentes,
        'todas_categorias': todas_categorias,
        
        'labels_grafico': json.dumps(labels_grafico), 'valores_grafico': json.dumps(valores_grafico), 'cores_grafico': json.dumps(cores_grafico),
        
        'meses_labels': json.dumps(meses_labels), 'receitas_data': json.dumps(receitas_data), 'despesas_data': json.dumps(despesas_data),
        
        'gastos_diarios': gastos_diarios, 'maior_gasto_diario': maior_gasto_diario,
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

def forcar_sincronizacao(request):
    res_cartao = sincronizar_cartao_credito("Meu Cartão")
    print(res_cartao)
    
    conta = Conta.objects.filter(ativa=True).first()
    if conta:
        res_conta = sincronizar_conta_corrente(conta.id)
        print(res_conta)
        
    return redirect('financeiro:home')

def marcar_fatura_paga(request, fatura_id):
    """Função rápida para o utilizador avisar o sistema que já pagou o cartão"""
    fatura = get_object_or_404(FaturaCartao, id=fatura_id)
    fatura.paga = True
    fatura.save()
    return redirect('financeiro:home')

def revisar_transacao(request, transacao_id):
    if request.method == 'POST':
        transacao = get_object_or_404(Transacao, id=transacao_id)
        
        # Pega as escolhas que você fez no select do HTML
        novo_tipo = request.POST.get('tipo')
        nova_categoria_id = request.POST.get('categoria')
        
        if novo_tipo:
            transacao.tipo = novo_tipo
            
        if nova_categoria_id:
            categoria = get_object_or_404(CategoriaFinanceira, id=nova_categoria_id)
            transacao.categoria = categoria
            
        # Marca como aprovada!
        transacao.revisada = True
        transacao.save()
        
    return redirect('financeiro:home')
