from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db.models import Sum
from django.utils import timezone

from objetivos.models import ObjetivoMacro
from .models import OrcamentoMensal, RegraAporteAutomatico, Transacao, Conta, FaturaCartao, CategoriaFinanceira, TransacaoCartao
from .forms import CategoriaForm, ContaForm, TransacaoForm

import json

def dashboard_financeiro(request):
    # --- Lógica de Gravação do Formulário ---
    if request.method == 'POST':
        form = TransacaoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('financeiro:home')
    else:
        form = TransacaoForm()

    # --- Lógica de Exibição (Mesma de antes) ---
    hoje = timezone.now()
    mes_atual = hoje.month
    ano_atual = hoje.year

    total_receitas = Transacao.objects.filter(
        tipo='RECEITA', 
        data_vencimento__month=mes_atual, 
        data_vencimento__year=ano_atual,
        efetivada=True
    ).aggregate(total=Sum('valor'))['total'] or 0

    total_despesas = Transacao.objects.filter(
        tipo='DESPESA', 
        data_vencimento__month=mes_atual, 
        data_vencimento__year=ano_atual,
        efetivada=True
    ).aggregate(total=Sum('valor'))['total'] or 0

    contas_ativas = Conta.objects.filter(ativa=True)
    saldo_geral = sum([conta.saldo_atual for conta in contas_ativas])

    transacoes_recentes = Transacao.objects.all().select_related(
        'categoria', 'conta'
    ).order_by('-data_vencimento', '-id')[:10]
    
    # ========================================================
    # Preparação dos dados para o gráfico de gastos por categoria
    # ========================================================
    gastos_por_categoria = Transacao.objects.filter(
        tipo='DESPESA',
        data_vencimento__month=mes_atual,
        data_vencimento__year=ano_atual,
        efetivada=True
    ).values('categoria__nome', 'categoria__cor').annotate(total=Sum('valor')).order_by('-total')

    labels_grafico = []
    valores_grafico = []
    cores_grafico = []

    for gasto in gastos_por_categoria:
        nome = gasto['categoria__nome'] or 'Outros'
        # Usa a cor definida no modelo ou um cinzento padrão se estiver vazio
        cor = gasto['categoria__cor'] or '#95a5a6' 
        
        labels_grafico.append(nome)
        valores_grafico.append(float(gasto['total']))
        cores_grafico.append(cor)
    
    # =========================================================
    # Dados para o gráfico de evolução mensal (últimos 6 meses)
    # =========================================================
    meses_labels = []
    receitas_data = []
    despesas_data = []

    nomes_meses = ['', 'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

    # Vamos iterar de 5 até 0 (para os últimos 6 meses, incluindo o atual)
    for i in range(5, -1, -1):
        mes_calc = hoje.month - i
        ano_calc = hoje.year
        
        # Ajuste matemático para quando recuamos para o ano anterior
        if mes_calc <= 0:
            mes_calc += 12
            ano_calc -= 1
            
        meses_labels.append(f'{nomes_meses[mes_calc]}/{str(ano_calc)[2:]}')
        
        # Query de Receitas do mês/ano específico
        rec = Transacao.objects.filter(
            tipo='RECEITA',
            data_vencimento__month=mes_calc,
            data_vencimento__year=ano_calc,
            efetivada=True
        ).aggregate(total=Sum('valor'))['total'] or 0
        receitas_data.append(float(rec))
        
        # Query de Despesas do mês/ano específico
        desp = Transacao.objects.filter(
            tipo='DESPESA',
            data_vencimento__month=mes_calc,
            data_vencimento__year=ano_calc,
            efetivada=True
        ).aggregate(total=Sum('valor'))['total'] or 0
        despesas_data.append(float(desp))
    
    conta_form = ContaForm()
    categoria_form = CategoriaForm()

    context = {
        'total_receitas': total_receitas,
        'total_despesas': total_despesas,
        'saldo': saldo_geral,
        'transacoes': transacoes_recentes,
        
        'form': form,
        'conta_form': conta_form,
        'categoria_form': categoria_form,
        
        # Gráfico de Gastos por Categoria
        'labels_grafico': json.dumps(labels_grafico),
        'valores_grafico': json.dumps(valores_grafico),
        'cores_grafico': json.dumps(cores_grafico),
        
        # Gráfico de Evolução Mensal
        'meses_labels': json.dumps(meses_labels),
        'receitas_data': json.dumps(receitas_data),
        'despesas_data': json.dumps(despesas_data),
    }

    return render(request, 'financeiro/dashboard.html', context)

def painel_cartoes(request):
    faturas_abertas = FaturaCartao.objects.filter(paga=False).order_by('data_vencimento')
    
    faturas_dados = []
    for fatura in faturas_abertas:
        total_gasto = fatura.compras.aggregate(total=Sum('valor'))['total'] or 0
        faturas_dados.append({
            'fatura': fatura,
            'total_gasto': total_gasto,
            'compras': fatura.compras.all().order_by('-data_compra')
        })

    contas_ativas = Conta.objects.filter(ativa=True)
    categorias = CategoriaFinanceira.objects.all() # <-- Novo: para o formulário de compras

    context = {
        'faturas_dados': faturas_dados,
        'contas_ativas': contas_ativas,
        'categorias': categorias, # <-- Novo
    }
    return render(request, 'financeiro/cartoes.html', context)

def nova_fatura(request):
    if request.method == 'POST':
        nome_cartao = request.POST.get('nome_cartao')
        mes = request.POST.get('mes')
        ano = request.POST.get('ano')
        data_fechamento = request.POST.get('data_fechamento')
        data_vencimento = request.POST.get('data_vencimento')

        # Cria a nova fatura no banco de dados (por padrão, paga=False)
        FaturaCartao.objects.create(
            nome_cartao=nome_cartao,
            mes=mes,
            ano=ano,
            data_fechamento=data_fechamento,
            data_vencimento=data_vencimento
        )
        
    return redirect('financeiro:painel_cartoes')

def pagar_fatura(request, fatura_id):
    if request.method == 'POST':
        fatura = get_object_or_404(FaturaCartao, id=fatura_id)
        conta_id = request.POST.get('conta_pagamento')
        valor_pagamento = request.POST.get('valor_pagamento')
        
        conta = get_object_or_404(Conta, id=conta_id)
        
        # 1. Marca a fatura como paga
        fatura.paga = True
        fatura.save()

        # 2. Cria a transação de débito na conta selecionada para atualizar o saldo
        Transacao.objects.create(
            descricao=f'Pagamento Fatura {fatura.nome_cartao} - {fatura.mes}/{fatura.ano}',
            tipo='DESPESA',
            valor=valor_pagamento,
            data_vencimento=timezone.now(), # Usa a data de hoje (pagamento antecipado)
            data_pagamento=timezone.now(),
            conta=conta,
            efetivada=True
        )
        
    return redirect('financeiro:painel_cartoes')

def adicionar_compra_cartao(request, fatura_id):
    if request.method == 'POST':
        fatura = get_object_or_404(FaturaCartao, id=fatura_id)
        descricao = request.POST.get('descricao')
        valor = request.POST.get('valor')
        data_compra = request.POST.get('data_compra')
        categoria_id = request.POST.get('categoria')

        categoria = None
        if categoria_id:
            categoria = get_object_or_404(CategoriaFinanceira, id=categoria_id)

        # Regista a nova compra vinculada a esta fatura
        TransacaoCartao.objects.create(
            fatura=fatura,
            descricao=descricao,
            valor=valor,
            data_compra=data_compra,
            categoria=categoria
        )
        
    return redirect('financeiro:painel_cartoes')

def painel_orcamentos(request):
    hoje = timezone.now()
    mes_atual = hoje.month
    ano_atual = hoje.year

    # Vai buscar os tetos de gastos definidos para este mês
    orcamentos = OrcamentoMensal.objects.filter(mes=mes_atual, ano=ano_atual)
    
    dados_orcamento = []
    
    for orc in orcamentos:
        # Soma todas as despesas efetivadas desta categoria no mês atual
        gasto = Transacao.objects.filter(
            categoria=orc.categoria,
            tipo='DESPESA',
            data_vencimento__month=mes_atual,
            data_vencimento__year=ano_atual,
            efetivada=True
        ).aggregate(total=Sum('valor'))['total'] or 0

        # Matemática para a barra de progresso
        valor_limite = float(orc.valor_limite)
        gasto_float = float(gasto)
        percentual = (gasto_float / valor_limite * 100) if valor_limite > 0 else 0
        
        # Define as cores com base no consumo (Alerta aos 80%)
        cor_barra = 'bg-success' # Verde (Tranquilo)
        alerta = False
        
        if percentual >= 100:
            cor_barra = 'bg-danger' # Vermelho (Estourou)
            alerta = True
        elif percentual >= 80:
            cor_barra = 'bg-warning' # Amarelo (Atenção)
            alerta = True

        dados_orcamento.append({
            'orcamento': orc,
            'gasto': gasto,
            'restante': valor_limite - gasto_float,
            'percentual_real': percentual,
            'percentual_barra': min(percentual, 100), # Limita a barra a 100% visualmente
            'cor_barra': cor_barra,
            'alerta': alerta
        })

    # Para o formulário de novo orçamento (apenas categorias de despesa)
    categorias_despesa = CategoriaFinanceira.objects.filter(tipo='DESPESA')

    # NOVO: Calcular o Saldo Geral para o Simulador "E se?"
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

def novo_orcamento(request):
    if request.method == 'POST':
        categoria_id = request.POST.get('categoria')
        valor_limite = request.POST.get('valor_limite')
        
        hoje = timezone.now()
        categoria = get_object_or_404(CategoriaFinanceira, id=categoria_id)
        
        # Tenta criar o orçamento ou atualiza se já existir para este mês/ano
        OrcamentoMensal.objects.update_or_create(
            categoria=categoria,
            mes=hoje.month,
            ano=hoje.year,
            defaults={'valor_limite': valor_limite}
        )
        
    return redirect('financeiro:painel_orcamentos')

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

def novo_aporte(request):
    if request.method == 'POST':
        objetivo_id = request.POST.get('objetivo_id')
        conta_id = request.POST.get('conta_origem')
        valor_aporte = request.POST.get('valor_aporte')
        data_aporte = request.POST.get('data_aporte')
        
        objetivo = get_object_or_404(ObjetivoMacro, id=objetivo_id)
        conta = get_object_or_404(Conta, id=conta_id)
        
        # Cria a transação de "Transferência" e usa o 'titulo' do seu modelo
        Transacao.objects.create(
            descricao=f'Aporte: {objetivo.titulo}', 
            tipo='TRANSFERENCIA',
            valor=valor_aporte,
            data_vencimento=data_aporte,
            data_pagamento=data_aporte,
            conta=conta,
            objetivo_vinculado=objetivo,
            efetivada=True
        )
        
    return redirect('financeiro:painel_objetivos')

def nova_regra_aporte(request):
    if request.method == 'POST':
        objetivo_id = request.POST.get('objetivo')
        conta_id = request.POST.get('conta_origem')
        valor_fixo = request.POST.get('valor_fixo')

        objetivo = get_object_or_404(ObjetivoMacro, id=objetivo_id)
        conta = get_object_or_404(Conta, id=conta_id)

        RegraAporteAutomatico.objects.create(
            objetivo=objetivo,
            conta_origem=conta,
            valor_fixo=valor_fixo
        )
        
    return redirect('financeiro:painel_objetivos')

def nova_conta(request):
    if request.method == 'POST':
        form = ContaForm(request.POST)
        if form.is_valid():
            form.save()
    return redirect('financeiro:home')

def nova_categoria(request):
    if request.method == 'POST':
        form = CategoriaForm(request.POST)
        if form.is_valid():
            form.save()
    return redirect('financeiro:home')

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
    
    # Formata o mês e ano atual, ex: '02-2026'
    mes_ano_atual = hoje.strftime('%m-%Y')

    # Se você quiser que rode ESTRITAMENTE no dia 10 de cada mês:
    # if hoje.day != 10:
    #     return JsonResponse({'status': 'Ignorado', 'motivo': 'Não é o primeiro dia do mês'})

    # Busca regras ativas que AINDA NÃO rodaram neste mês
    regras_pendentes = RegraAporteAutomatico.objects.filter(ativa=True).exclude(ultimo_mes_processado=mes_ano_atual)
    aportes_gerados = 0

    for regra in regras_pendentes:
        # 1. Cria a transação de "Transferência" que retira o dinheiro do saldo
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
        
        # 2. Marca a regra como processada neste mês para não duplicar se a URL for acionada novamente
        regra.ultimo_mes_processado = mes_ano_atual
        regra.save()
        
        aportes_gerados += 1

    return JsonResponse({
        'status': 'Sucesso',
        'mes_referencia': mes_ano_atual,
        'aportes_gerados': aportes_gerados
    })