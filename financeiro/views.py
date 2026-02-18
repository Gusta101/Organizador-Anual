from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum
from django.utils import timezone
from .models import Transacao, Conta, FaturaCartao
from .forms import TransacaoForm

def dashboard_financeiro(request):
    # --- Lógica de Gravação do Formulário ---
    if request.method == 'POST':
        form = TransacaoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('financeiro:index')
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

    context = {
        'total_receitas': total_receitas,
        'total_despesas': total_despesas,
        'saldo': saldo_geral,
        'transacoes': transacoes_recentes,
        'form': form, # <-- Formulário enviado para o template
    }

    return render(request, 'financeiro/dashboard.html', context)

def painel_cartoes(request):
    # Busca faturas abertas e calcula o total gasto em cada uma
    faturas_abertas = FaturaCartao.objects.filter(paga=False).order_by('data_vencimento')
    
    faturas_dados = []
    for fatura in faturas_abertas:
        total_gasto = fatura.compras.aggregate(total=Sum('valor'))['total'] or 0
        faturas_dados.append({
            'fatura': fatura,
            'total_gasto': total_gasto,
            'compras': fatura.compras.all().order_by('-data_compra')
        })

    # Precisamos das contas ativas para o modal de pagamento (para saber de onde o dinheiro vai sair)
    contas_ativas = Conta.objects.filter(ativa=True)

    context = {
        'faturas_dados': faturas_dados,
        'contas_ativas': contas_ativas,
    }
    return render(request, 'financeiro/cartoes.html', context)

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