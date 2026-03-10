import os
import requests
import time
from dotenv import load_dotenv
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from datetime import date, timedelta
from django.db.models import Sum

from .models import Transacao, Conta, CategoriaFinanceira, TransacaoCartao, FaturaCartao

load_dotenv()

PLUGGY_CLIENT_ID = os.getenv('PLUGGY_CLIENT_ID')
PLUGGY_CLIENT_SECRET = os.getenv('PLUGGY_CLIENT_SECRET')
ACCOUNT_ID_CORRENTE = os.getenv('ACCOUNT_ID_CORRENTE')
ACCOUNT_ID_CREDITO = os.getenv('ACCOUNT_ID_CREDITO')
BASE_URL = 'https://api.pluggy.ai'

# Esta função faz a autenticação na API da Pluggy usando as credenciais do ambiente.
# Ela retorna um token (apiKey) válido para ser usado nas próximas requisições.
def obter_token_pluggy():
    url = f'{BASE_URL}/auth'
    response = requests.post(url, json={'clientId': PLUGGY_CLIENT_ID, 'clientSecret': PLUGGY_CLIENT_SECRET})
    if response.status_code == 200: return response.json().get('apiKey')
    return None

# Esta função força a API da Pluggy a buscar os dados mais recentes diretamente no banco.
# Ela descobre a qual "Item" (conexão bancária) a conta pertence, pede uma atualização via PATCH,
# e faz um loop (polling) verificando a cada 3 segundos se a atualização terminou, com um limite de 5 tentativas.
def forcar_atualizacao_pluggy(account_id, token):
    res_acc = requests.get(f'{BASE_URL}/accounts/{account_id}', headers={'accept': 'application/json', 'X-API-KEY': token})
    if res_acc.status_code != 200: return False
    
    item_id = res_acc.json().get('itemId')
    if not item_id: return False

    url_item = f'{BASE_URL}/items/{item_id}'
    requests.patch(url_item, headers={'accept': 'application/json', 'X-API-KEY': token})

    tentativas = 0
    while tentativas < 20:
        time.sleep(3)
        res_item = requests.get(url_item, headers={'accept': 'application/json', 'X-API-KEY': token})
        status = res_item.json().get('status')
        print(f'Atualizando banco (Item {item_id[:5]})... Estado: {status}')
        if status not in ['UPDATING', 'WAITING_USER_INPUT', 'LOGIN_IN_PROGRESS']:
            break
        tentativas += 1
    return True

# Esta função busca a lista de transações de uma conta específica na API da Pluggy.
# Retorna uma lista de dicionários contendo os dados brutos de cada movimentação.
def buscar_transacoes_api(account_id, token):
    if not token or not account_id: return []
    url = f'{BASE_URL}/transactions'
    response = requests.get(url, headers={'accept': 'application/json', 'X-API-KEY': token}, params={'accountId': account_id})
    if response.status_code == 200: return response.json().get('results', [])
    return []

# Esta função consulta o saldo atual e real da conta lá no banco via Pluggy.
def buscar_saldo_real_api(account_id, token):
    if not token or not account_id: return 0
    url = f'{BASE_URL}/accounts/{account_id}'
    response = requests.get(url, headers={'accept': 'application/json', 'X-API-KEY': token})
    if response.status_code == 200: return response.json().get('balance', 0)
    return 0

# Função principal para sincronizar uma CONTA CORRENTE.
# Ela realiza os seguintes passos:
# 1. Pega o token, atualiza o banco e baixa transações e saldo real.
# 2. Ajusta o "saldo_inicial" da conta no banco de dados local (Django) para que, 
#    somado às transações cadastradas, reflita o saldo real atual da conta.
# 3. Varre as transações trazidas da API, descobre se são RECEITAS, DESPESAS ou TRANSFERÊNCIAS 
#    com base em palavras-chave e valores.
# 4. Salva ou atualiza as categorias e transações no banco de dados local do seu app.
def sincronizar_conta_corrente(conta_django_id):
    token = obter_token_pluggy()
    if not token: return 'Falha.'
    
    forcar_atualizacao_pluggy(ACCOUNT_ID_CORRENTE, token)
    transacoes_api = buscar_transacoes_api(ACCOUNT_ID_CORRENTE, token)
    saldo_real = buscar_saldo_real_api(ACCOUNT_ID_CORRENTE, token)
    
    try: 
        conta_destino = Conta.objects.get(id=conta_django_id)
    except Conta.DoesNotExist: 
        return 'Conta não encontrada.'

    # Ajuste milimétrico do saldo inicial
    movimentacoes_django = Transacao.objects.filter(conta=conta_destino, efetivada=True)
    receitas_dj = movimentacoes_django.filter(tipo='RECEITA').aggregate(t=Sum('valor'))['t'] or 0
    despesas_dj = movimentacoes_django.filter(tipo='DESPESA').aggregate(t=Sum('valor'))['t'] or 0
    conta_destino.saldo_inicial = float(saldo_real) - float(receitas_dj) + float(despesas_dj)
    conta_destino.save()

    for t in transacoes_api:
        id_api = t.get('id')
        if not id_api: continue
        
        # =======================================================
        # 1. EXTRAÇÃO DOS DADOS (O JSON Limpo)
        # =======================================================
        descricao = t.get('description', '')
        amount = float(t.get('amount', 0))
        categoria_api = t.get('category', '')
        date_str = t.get('date')
        status = t.get('status')
        
        # Mergulhando nos Dados Bancários (O JSON do PIX/Boleto)
        payment_data = t.get('paymentData') or {}
        metodo_pagamento = payment_data.get('paymentMethod') or 'OTHER' # PIX, TED, BOLETO, OTHER
        
        desc_lower = descricao.lower()
        is_saida = amount < 0
        valor = abs(amount)
        
        # =======================================================
        # 2. A ÁRVORE DE DECISÃO (A Lógica de Classificação)
        # =======================================================
        tipo_final = 'DESPESA' if is_saida else 'RECEITA'
        pagamento_fatura = False
        
        # REGRA A: Pagamento de Fatura do Cartão (Dá baixa automática)
        palavras_fatura = ['fatura', 'pagamento cartão', 'fatura nubank']
        if is_saida and any(p in desc_lower for p in palavras_fatura):
            tipo_final = 'TRANSFERENCIA' # Neutro para não inflar as despesas
            pagamento_fatura = True
            
        # REGRA B: Caixinhas e Investimentos
        elif any(p in desc_lower for p in ['caixinha', 'resgate', 'investimento', 'aplicação']):
            tipo_final = 'TRANSFERENCIA'
            
        # REGRA C: Transações PIX
        elif metodo_pagamento == 'PIX':
            # Vai para a área de "Revisão" que criámos antes para si
            tipo_final = 'DESPESA' if is_saida else 'RECEITA'
            
        # REGRA D: Boletos e outros pagamentos
        elif metodo_pagamento == 'BOLETO':
            tipo_final = 'DESPESA'
            
        # =======================================================
        # 3. GRAVAR NO BANCO DE DADOS
        # =======================================================
        data_alvo = parse_datetime(date_str).date() if date_str else timezone.now().date()
        efetivada = True if status == 'POSTED' else False

        categoria, _ = CategoriaFinanceira.objects.get_or_create(
            nome=categoria_api or 'Outros', 
            defaults={'tipo': 'DESPESA', 'cor': '#95a5a6'}
        )

        # Usamos update_or_create para nunca duplicar
        transacao_obj, created = Transacao.objects.update_or_create(
            id_api=id_api, 
            defaults={
                'descricao': descricao, 
                'tipo': tipo_final, 
                'valor': valor, 
                'data_vencimento': data_alvo, 
                'data_pagamento': data_alvo if efetivada else None, 
                'conta': conta_destino, 
                'categoria': categoria, 
                'efetivada': efetivada,
                'revisada': False
            }
        )
        
        # =======================================================
        # 4. A MAGIA: DANDO BAIXA NA FATURA DO CARTÃO!
        # =======================================================
        if created and pagamento_fatura:
            print(f"🔥 Pagamento de Fatura detetado no dia {data_alvo.strftime('%d/%m')}: R$ {valor}")
            
            # Procura a fatura mais antiga em aberto para dar baixa
            # Ex: Se você pagou em Março, ele caça a fatura de Março que está "paga=False"
            fatura_pendente = FaturaCartao.objects.filter(
                paga=False, 
                data_vencimento__lte=data_alvo + timedelta(days=20)
            ).order_by('data_vencimento').first()
            
            if fatura_pendente:
                fatura_pendente.paga = True
                fatura_pendente.save()
                print(f"✅ Fatura {fatura_pendente.mes:02d}/{fatura_pendente.ano} marcada como PAGA automaticamente!")

    return 'Conta Atualizada.'

# Função principal para sincronizar um CARTÃO DE CRÉDITO.
# Ela realiza os seguintes passos:
# 1. Autentica e força a atualização das faturas na API.
# 2. Ignora valores positivos ou zerados (focando apenas nos gastos, que muitas vezes vêm negativos na API, mas que viram "valor absoluto" aqui).
# 3. Possui uma lógica de fechamento de fatura: se a compra foi até o dia 2, entra na fatura do mês atual. 
#    Se foi após o dia 2, joga para a fatura do mês seguinte (tratando a virada de ano).
# 4. Cria a Fatura se não existir, e atrela cada transação a ela no banco do Django.
# 5. Imprime um log no terminal detalhando se a transação é nova ou não, especialmente focado em faturas a partir de março de 2026.
def sincronizar_cartao_credito(nome_cartao='Meu Cartão'):
    token = obter_token_pluggy()
    if not token: return 'Falha.'
    
    forcar_atualizacao_pluggy(ACCOUNT_ID_CREDITO, token)
    transacoes_api = buscar_transacoes_api(ACCOUNT_ID_CREDITO, token)
    hoje = timezone.now().date()

    for t in transacoes_api:
        id_api = t.get('id')
        if not id_api: continue
        
        amount = float(t.get('amount', 0))
        if amount <= 0: continue 
        
        valor = amount
        descricao = t.get('description', 'Compra Cartão')
        categoria_api = t.get('category', '')
        date_str = t.get('date')
        
        data_alvo = parse_datetime(date_str) if date_str else timezone.now()
        data_compra = data_alvo.date()
        
        # =======================================================
        # A MAGIA DO CAMINHO A: BUSCAR O ID EXATO DA FATURA
        # =======================================================
        credit_data = t.get('creditCardMetadata') or {}
        bill_id = credit_data.get('billId')
        
        # Estimativa visual de mês/ano apenas para dar um nome bonito à fatura no Dashboard
        if data_compra.day <= 10:
            mes_fatura = data_compra.month
            ano_fatura = data_compra.year
        else:
            mes_fatura = data_compra.month + 1
            ano_fatura = data_compra.year
            if mes_fatura > 12:
                mes_fatura = 1
                ano_fatura += 1

        ja_foi_paga = True if (ano_fatura < hoje.year or (ano_fatura == hoje.year and mes_fatura < hoje.month)) else False

        # Se o Nubank mandou o ID da fatura, usamos como âncora!
        if bill_id:
            fatura, _ = FaturaCartao.objects.get_or_create(
                id_fatura_banco=bill_id,
                defaults={
                    'nome_cartao': nome_cartao,
                    'mes': mes_fatura,
                    'ano': ano_fatura,
                    'data_fechamento': date(ano_fatura, mes_fatura, 2),
                    'data_vencimento': date(ano_fatura, mes_fatura, 10),
                    'paga': ja_foi_paga
                }
            )
        else:
            # Fallback: Compras feitas HOJE podem ainda não ter billId gerado pelo banco
            fatura, _ = FaturaCartao.objects.get_or_create(
                nome_cartao=nome_cartao,
                mes=mes_fatura,
                ano=ano_fatura,
                defaults={
                    'data_fechamento': date(ano_fatura, mes_fatura, 2),
                    'data_vencimento': date(ano_fatura, mes_fatura, 10),
                    'paga': ja_foi_paga
                }
            )
            
        categoria, _ = CategoriaFinanceira.objects.get_or_create(
            nome=categoria_api or 'Outros', 
            defaults={'tipo': 'DESPESA', 'cor': '#95a5a6'}
        )
        
        TransacaoCartao.objects.update_or_create(
            id_api=id_api, 
            defaults={
                'fatura': fatura, 
                'descricao': descricao, 
                'valor': valor, 
                'data_compra': data_compra, 
                'categoria': categoria
            }
        )
        
    return 'Cartão Atualizado.'
