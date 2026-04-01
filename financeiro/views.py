from django.shortcuts import render, redirect
from django.db.models import Sum
from django.contrib import messages
from django.utils import timezone

from .models import *
from .forms import *
import datetime
from dateutil.relativedelta import relativedelta
from .services import importar_extrato_ofx


def importar_extrato(request):
    if request.method == 'POST':
        arquivo = request.FILES.get('arquivo_extrato')
        tipo_destino = request.POST.get('tipo_destino')
        destino_id = request.POST.get('destino_id')

        if not arquivo or not arquivo.name.endswith('.ofx'):
            messages.error(request, "Por favor, envie um arquivo .ofx válido.")
            return redirect('financeiro:importar_extrato')

        try:
            conta_id = destino_id if tipo_destino == 'conta' else None
            cartao_id = destino_id if tipo_destino == 'cartao' else None

            resultado = importar_extrato_ofx(arquivo, conta_id=conta_id, cartao_id=cartao_id)
            
            messages.success(
                request, 
                f"Sucesso! {resultado['importadas']} transações importadas e {resultado['ignoradas']} ignoradas (já existiam)."
            )
        except Exception as e:
            messages.error(request, f"Erro ao processar o arquivo: {str(e)}")
            
        return redirect('financeiro:importar_extrato')

    contas = Conta.objects.all()
    cartoes = CartaoCredito.objects.all()
    
    return render(request, 'financeiro/importar.html', {
        'contas': contas,
        'cartoes': cartoes
    })

def dashboard(request):
    hoje = timezone.localtime(timezone.now()).date()
    mes_sel = int(request.GET.get('mes', hoje.month))
    ano_sel = int(request.GET.get('ano', hoje.year))
    data_ref = datetime.date(ano_sel, mes_sel, 1)

    data_anterior = data_ref - relativedelta(months=1)
    data_proxima = data_ref + relativedelta(months=1)

    # Saldo Real Atual (Ponto de Partida)
    saldo_atual_real = 0
    for conta in Conta.objects.all():
        rec = TransacaoEfetivada.objects.filter(conta=conta, tipo='RECEITA', data_efetivacao__gte=conta.data_saldo_inicial).aggregate(Sum('valor'))['valor__sum'] or 0
        desp = TransacaoEfetivada.objects.filter(conta=conta, tipo='DESPESA', data_efetivacao__gte=conta.data_saldo_inicial).aggregate(Sum('valor'))['valor__sum'] or 0
        saldo_atual_real += (conta.saldo_inicial + rec - desp)

    is_futuro = data_ref > hoje.replace(day=1)

    # Lógica para criar os dados temporais
    if is_futuro:
        ultimo_dia_mes_alvo = data_ref + relativedelta(day=31)
        
        # Inicia a lista com as transações previstas pontuais
        transacoes_lista = list(TransacaoPrevista.objects.filter(data_prevista__month=mes_sel, data_prevista__year=ano_sel))
        receitas_cards = sum(t.valor_previsto for t in transacoes_lista if t.tipo == 'RECEITA')
        despesas_cards = sum(t.valor_previsto for t in transacoes_lista if t.tipo == 'DESPESA')
        
        rec_total_receita = 0
        rec_total_despesa = 0
        
        # Processa as recorrências ativas mês a mês
        recorrentes = TransacaoRecorrente.objects.filter(is_ativa=True)
        for rec in recorrentes:
            data_iter = hoje + relativedelta(days=1) # Conta a partir de amanhã
            
            while data_iter <= ultimo_dia_mes_alvo:
                # Garante que meses com 28/30 dias não quebrem se o vencimento for 31
                dia_venc = min(rec.dia_vencimento, (data_iter + relativedelta(day=31)).day)
                data_ocorrencia = datetime.date(data_iter.year, data_iter.month, dia_venc)
                
                if hoje < data_ocorrencia <= ultimo_dia_mes_alvo:
                    # Soma para a projeção de saldo a longo prazo
                    if rec.tipo == 'RECEITA':
                        rec_total_receita += rec.valor
                    else:
                        rec_total_despesa += rec.valor
                    
                    # Se a ocorrência for exatamente no mês que está na tela, adiciona aos cards e à lista
                    if data_ocorrencia.month == mes_sel and data_ocorrencia.year == ano_sel:
                        if rec.tipo == 'RECEITA':
                            receitas_cards += rec.valor
                        else:
                            despesas_cards += rec.valor
                        
                        # Mock do objeto para o HTML ler corretamente
                        rec_mock = TransacaoRecorrente(descricao=f"{rec.descricao} (Recorrente)", valor=rec.valor, tipo=rec.tipo, categoria=rec.categoria)
                        rec_mock.data_prevista = data_ocorrencia
                        rec_mock.valor_previsto = rec.valor
                        transacoes_lista.append(rec_mock)

                # Avança para o próximo mês
                data_iter = (data_iter + relativedelta(months=1)).replace(day=1)

        # Projeção Total do Saldo no Mês Alvo
        prev_rec = TransacaoPrevista.objects.filter(data_prevista__gt=hoje, data_prevista__lte=ultimo_dia_mes_alvo, tipo='RECEITA').aggregate(Sum('valor_previsto'))['valor_previsto__sum'] or 0
        prev_desp = TransacaoPrevista.objects.filter(data_prevista__gt=hoje, data_prevista__lte=ultimo_dia_mes_alvo, tipo='DESPESA').aggregate(Sum('valor_previsto'))['valor_previsto__sum'] or 0
        
        saldo_no_mes = saldo_atual_real + prev_rec + rec_total_receita - prev_desp - rec_total_despesa
        
        # Ordena a lista final por data
        transacoes_lista.sort(key=lambda x: x.data_prevista)

    else:
        # Lógica para Mês Atual/Passado com cálculo prospectivo e retrospectivo
        ultimo_dia_mes = data_ref + relativedelta(day=31)
        saldo_no_mes = 0

        for c in Conta.objects.all():
            if ultimo_dia_mes >= c.data_saldo_inicial:
                # Calcula do marco inicial para a frente
                rec_hist = TransacaoEfetivada.objects.filter(
                    conta=c, 
                    data_efetivacao__gte=c.data_saldo_inicial, 
                    data_efetivacao__lte=ultimo_dia_mes, 
                    tipo='RECEITA'
                ).aggregate(Sum('valor'))['valor__sum'] or 0

                desp_hist = TransacaoEfetivada.objects.filter(
                    conta=c, 
                    data_efetivacao__gte=c.data_saldo_inicial, 
                    data_efetivacao__lte=ultimo_dia_mes, 
                    tipo='DESPESA'
                ).aggregate(Sum('valor'))['valor__sum'] or 0
                
                saldo_no_mes += (c.saldo_inicial + rec_hist - desp_hist)
            else:
                # Cálculo reverso: do mês alvo (passado) até o marco inicial
                rec_reverso = TransacaoEfetivada.objects.filter(
                    conta=c,
                    data_efetivacao__gt=ultimo_dia_mes,
                    data_efetivacao__lte=c.data_saldo_inicial,
                    tipo='RECEITA'
                ).aggregate(Sum('valor'))['valor__sum'] or 0
                
                desp_reverso = TransacaoEfetivada.objects.filter(
                    conta=c,
                    data_efetivacao__gt=ultimo_dia_mes,
                    data_efetivacao__lte=c.data_saldo_inicial,
                    tipo='DESPESA'
                ).aggregate(Sum('valor'))['valor__sum'] or 0
                
                # Inverte a matemática: Subtrai receitas e soma despesas que ocorreram depois do mês passado
                saldo_no_mes += (c.saldo_inicial - rec_reverso + desp_reverso)

        receitas_cards = TransacaoEfetivada.objects.filter(data_efetivacao__month=mes_sel, data_efetivacao__year=ano_sel, tipo='RECEITA').aggregate(Sum('valor'))['valor__sum'] or 0
        despesas_cards = TransacaoEfetivada.objects.filter(data_efetivacao__month=mes_sel, data_efetivacao__year=ano_sel, tipo='DESPESA').aggregate(Sum('valor'))['valor__sum'] or 0
        transacoes_lista = TransacaoEfetivada.objects.filter(data_efetivacao__month=mes_sel, data_efetivacao__year=ano_sel).order_by('-data_efetivacao')

    # Orçamentos (Budgeting)
    lista_orcamentos = []
    for cat in Categoria.objects.filter(orcamento_mensal_teto__isnull=False):
        gasto = TransacaoEfetivada.objects.filter(categoria=cat, data_efetivacao__month=mes_sel, data_efetivacao__year=ano_sel, tipo='DESPESA').aggregate(Sum('valor'))['valor__sum'] or 0
        teto = cat.orcamento_mensal_teto
        lista_orcamentos.append({
            'nome': cat.nome, 'gasto': gasto, 'teto': teto,
            'percentual': min((gasto / teto * 100), 100) if teto > 0 else 0,
            'estourou': gasto > teto
        })
    
    # Gráfico de analise mensal
    labels_grafico = []
    receitas_grafico = []
    despesas_grafico = []

    for i in range(-3, 3):
        mes_foco = data_ref + relativedelta(months=i)
        labels_grafico.append(mes_foco.strftime('%b/%y').upper())
        
        # Se o mês é passado ou o atual (Baseado em hoje)
        if mes_foco <= hoje.replace(day=1):
            r = TransacaoEfetivada.objects.filter(data_efetivacao__month=mes_foco.month, data_efetivacao__year=mes_foco.year, tipo='RECEITA').aggregate(Sum('valor'))['valor__sum'] or 0
            d = TransacaoEfetivada.objects.filter(data_efetivacao__month=mes_foco.month, data_efetivacao__year=mes_foco.year, tipo='DESPESA').aggregate(Sum('valor'))['valor__sum'] or 0
        else:
            # Se o mês é futuro (Previstas + Recorrentes)
            r_prev = TransacaoPrevista.objects.filter(data_prevista__month=mes_foco.month, data_prevista__year=mes_foco.year, tipo='RECEITA').aggregate(Sum('valor_previsto'))['valor_previsto__sum'] or 0
            d_prev = TransacaoPrevista.objects.filter(data_prevista__month=mes_foco.month, data_prevista__year=mes_foco.year, tipo='DESPESA').aggregate(Sum('valor_previsto'))['valor_previsto__sum'] or 0
            
            # Soma as recorrentes ativas para aquele mês futuro
            r_rec = sum(rec.valor for rec in TransacaoRecorrente.objects.filter(is_ativa=True, tipo='RECEITA'))
            d_rec = sum(rec.valor for rec in TransacaoRecorrente.objects.filter(is_ativa=True, tipo='DESPESA'))
            
            r = r_prev + r_rec
            d = d_prev + d_rec
        
        receitas_grafico.append(float(r))
        despesas_grafico.append(float(d))

    context = {
        'data_ref': data_ref,
        'mes_anterior': data_anterior,
        'mes_proximo': data_proxima,
        'receitas_mes': receitas_cards,
        'despesas_mes': despesas_cards,
        'saldo_no_mes': saldo_no_mes,
        'transacoes': transacoes_lista,
        'lista_orcamentos': lista_orcamentos,
        'is_futuro': is_futuro,
        
        'labels_grafico': labels_grafico,
        'receitas_grafico': receitas_grafico,
        'despesas_grafico': despesas_grafico,
        
        'form_prevista': TransacaoPrevistaForm(),
        'form_recorrente': TransacaoRecorrenteForm(),
    }
    
    return render(request, 'financeiro/dashboard.html', context)

def criar_transacao_prevista(request):
    if request.method == 'POST':
        form = TransacaoPrevistaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Transação prevista criada com sucesso!')
        else:
            messages.error(request, 'Erro ao criar transação prevista. Verifique os dados.')
    return redirect('financeiro:home')

def criar_transacao_recorrente(request):
    if request.method == 'POST':
        form = TransacaoRecorrenteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Transação recorrente (mensal) criada com sucesso!')
        else:
            messages.error(request, 'Erro ao criar transação recorrente. Verifique os dados.')
    return redirect('financeiro:home')
