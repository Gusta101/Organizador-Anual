from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db.models import Sum, Q
from django.utils import timezone

from objetivos.models import ObjetivoMacro
from .models import OrcamentoMensal, RegraAporteAutomatico, Transacao, Conta, FaturaCartao, CategoriaFinanceira, TransacaoCartao
from .forms import CategoriaForm, ContaForm, TransacaoForm

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
    if request.method == 'POST':
        form = TransacaoForm(request.POST)
        if form.is_valid():
            transacao = form.save(commit=False)
            
            if transacao.efetivada and not hasattr(transacao, 'data_pagamento') or not transacao.data_pagamento:
                transacao.data_pagamento = transacao.data_vencimento

            recorrente = form.cleaned_data.get('recorrente')
            parcelas = form.cleaned_data.get('parcelas') or 1
            
            if recorrente and parcelas > 1:
                transacao.total_parcelas = parcelas
                transacao.numero_parcela = 1
                transacao.save() 
                
                for i in range(1, parcelas):
                    nova_data = adicionar_meses(transacao.data_vencimento, i)
                    Transacao.objects.create(
                        descricao=f'{transacao.descricao} ({i+1}/{parcelas})',
                        tipo=transacao.tipo,
                        valor=transacao.valor,
                        data_vencimento=nova_data,
                        conta=transacao.conta,
                        categoria=transacao.categoria,
                        efetivada=False,
                        transacao_pai=transacao,
                        numero_parcela=i+1,
                        total_parcelas=parcelas
                    )
            else:
                transacao.save()

            return redirect('financeiro:home')
        else:
            print("\n" + "!"*40)
            print("ERRO DE VALIDAÇÃO NO FORMULÁRIO DE TRANSAÇÃO:")
            print(form.errors)
            print("!"*40 + "\n")
            
    else:
        form = TransacaoForm()
        
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

    # Descobre qual é o último dia do mês que o utilizador selecionou
    ultimo_dia = calendar.monthrange(ano_selecionado, mes_selecionado)[1]
    data_limite_projecao = date(ano_selecionado, mes_selecionado, ultimo_dia)

    # Pega tudo que NÃO FOI PAGO DE HOJE ATÉ O FIM DO MÊS SELECIONADO
    receitas_pendentes = Transacao.objects.filter(
        tipo='RECEITA', efetivada=False, data_vencimento__lte=data_limite_projecao
    ).aggregate(total=Sum('valor'))['total'] or 0

    despesas_pendentes = Transacao.objects.filter(
        tipo='DESPESA', efetivada=False, data_vencimento__lte=data_limite_projecao
    ).exclude(descricao__startswith='Pagamento Fatura').aggregate(total=Sum('valor'))['total'] or 0

    # Pega todas as faturas abertas do passado até o mês selecionado
    faturas_pendentes = FaturaCartao.objects.filter(paga=False).filter(
        Q(ano__lt=ano_selecionado) | Q(ano=ano_selecionado, mes__lte=mes_selecionado)
    )
    total_faturas_projecao = sum([float(f.compras.aggregate(t=Sum('valor'))['t'] or 0) for f in faturas_pendentes])

    # Saldo Mágico: O seu dinheiro de hoje + o que vai entrar - o que vai sair
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
        fatura__mes=mes_selecionado, fatura__ano=ano_selecionado # CORREÇÃO AQUI TAMBÉM
    ).values('categoria__nome', 'categoria__cor').annotate(total=Sum('valor'))

    categorias_dict = {}
    
    # Soma as despesas normais
    for g in gastos_transacoes:
        nome = g['categoria__nome'] or 'Outros'
        cor = g['categoria__cor'] or '#95a5a6'
        categorias_dict[nome] = {'cor': cor, 'total': float(g['total'])}

    # Soma as despesas do cartão nas mesmas categorias
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
    # 5. GRÁFICO DE BARRAS (Últimos 6 meses integrados)
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

    # Categorias para o modal de compra no cartão
    categorias_gerais = CategoriaFinanceira.objects.all()

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
        
        'contas_ativas': contas_ativas,
        'categorias': categorias_gerais,
        'transacoes': transacoes_recentes,
        
        'form': form,
        'conta_form': ContaForm(),
        'categoria_form': CategoriaForm(),
        
        'labels_grafico': json.dumps(labels_grafico),
        'valores_grafico': json.dumps(valores_grafico),
        'cores_grafico': json.dumps(cores_grafico),
        'meses_labels': json.dumps(meses_labels),
        'receitas_data': json.dumps(receitas_data),
        'despesas_data': json.dumps(despesas_data),
    }

    return render(request, 'financeiro/dashboard.html', context)

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
        
    return redirect('financeiro:home')

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
        
    return redirect('financeiro:home')

def adicionar_compra_cartao(request, fatura_id):
    if request.method == 'POST':
        fatura_atual = get_object_or_404(FaturaCartao, id=fatura_id)
        descricao = request.POST.get('descricao')
        # Precisamos de converter a vírgula para ponto caso o utilizador digite "50,00"
        valor_str = request.POST.get('valor').replace(',', '.')
        valor = float(valor_str)
        data_compra = request.POST.get('data_compra')
        categoria_id = request.POST.get('categoria')
        
        # Novos campos do formulário para o parcelamento
        recorrente = request.POST.get('recorrente_cartao') == 'on'
        parcelas = int(request.POST.get('parcelas_cartao') or 1)

        categoria = None
        if categoria_id:
            categoria = get_object_or_404(CategoriaFinanceira, id=categoria_id)

        if recorrente and parcelas > 1:
            for i in range(parcelas):
                # 1. Calcula qual será o mês e o ano da parcela atual do laço
                mes_futuro = (fatura_atual.mes - 1 + i) % 12 + 1
                ano_futuro = fatura_atual.ano + (fatura_atual.mes - 1 + i) // 12
                
                # 2. Busca a fatura desse mês futuro. Se não existir, cria uma nova!
                fatura_destino, criada = FaturaCartao.objects.get_or_create(
                    nome_cartao=fatura_atual.nome_cartao,
                    mes=mes_futuro,
                    ano=ano_futuro,
                    defaults={
                        # Calcula os dias de fechamento e vencimento futuros
                        'data_fechamento': adicionar_meses(fatura_atual.data_fechamento, i),
                        'data_vencimento': adicionar_meses(fatura_atual.data_vencimento, i),
                        'paga': False
                    }
                )
                
                # 3. Adiciona a compra dentro dessa fatura (Ex: "iPhone (1/12)")
                TransacaoCartao.objects.create(
                    fatura=fatura_destino,
                    descricao=f'{descricao} ({i+1}/{parcelas})',
                    valor=valor, # Valor DE CADA parcela
                    data_compra=data_compra,
                    categoria=categoria
                )
        else:
            # Compra normal à vista no crédito
            TransacaoCartao.objects.create(
                fatura=fatura_atual,
                descricao=descricao,
                valor=valor,
                data_compra=data_compra,
                categoria=categoria
            )
            
    return redirect('financeiro:home')

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