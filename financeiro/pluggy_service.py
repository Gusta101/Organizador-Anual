import os
import requests
import time
from dotenv import load_dotenv
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from datetime import date
from django.db.models import Sum

from .models import Transacao, Conta, CategoriaFinanceira, TransacaoCartao, FaturaCartao

load_dotenv()

PLUGGY_CLIENT_ID = os.getenv('PLUGGY_CLIENT_ID')
PLUGGY_CLIENT_SECRET = os.getenv('PLUGGY_CLIENT_SECRET')
ACCOUNT_ID_CORRENTE = os.getenv('ACCOUNT_ID_CORRENTE')
ACCOUNT_ID_CREDITO = os.getenv('ACCOUNT_ID_CREDITO')
BASE_URL = 'https://api.pluggy.ai'

def obter_token_pluggy():
    url = f'{BASE_URL}/auth'
    response = requests.post(url, json={'clientId': PLUGGY_CLIENT_ID, 'clientSecret': PLUGGY_CLIENT_SECRET})
    if response.status_code == 200: return response.json().get('apiKey')
    return None

def forcar_atualizacao_pluggy(account_id, token):
    res_acc = requests.get(f'{BASE_URL}/accounts/{account_id}', headers={'accept': 'application/json', 'X-API-KEY': token})
    if res_acc.status_code != 200: return False
    
    item_id = res_acc.json().get('itemId')
    if not item_id: return False

    url_item = f'{BASE_URL}/items/{item_id}'
    requests.patch(url_item, headers={'accept': 'application/json', 'X-API-KEY': token})

    tentativas = 0
    while tentativas < 5:
        time.sleep(3)
        res_item = requests.get(url_item, headers={'accept': 'application/json', 'X-API-KEY': token})
        status = res_item.json().get('status')
        print(f'Atualizando banco (Item {item_id[:5]})... Estado: {status}')
        if status not in ['UPDATING', 'WAITING_USER_INPUT', 'LOGIN_IN_PROGRESS']:
            break
        tentativas += 1
    return True

def buscar_transacoes_api(account_id, token):
    if not token or not account_id: return []
    # AQUI ESTAVA O VILÃO: Removi o "from" para o Pluggy não esconder as compras pendentes de ontem!
    url = f'{BASE_URL}/transactions'
    response = requests.get(url, headers={'accept': 'application/json', 'X-API-KEY': token}, params={'accountId': account_id})
    if response.status_code == 200: return response.json().get('results', [])
    return []

def buscar_saldo_real_api(account_id, token):
    url = f'{BASE_URL}/accounts/{account_id}'
    response = requests.get(url, headers={'accept': 'application/json', 'X-API-KEY': token})
    if response.status_code == 200: return response.json().get('balance', 0)
    return 0

def sincronizar_conta_corrente(conta_django_id):
    token = obter_token_pluggy()
    if not token: return 'Falha.'
    
    forcar_atualizacao_pluggy(ACCOUNT_ID_CORRENTE, token)
    transacoes_api = buscar_transacoes_api(ACCOUNT_ID_CORRENTE, token)
    saldo_real = buscar_saldo_real_api(ACCOUNT_ID_CORRENTE, token)
    
    try: conta_destino = Conta.objects.get(id=conta_django_id)
    except Conta.DoesNotExist: return 'Conta não encontrada.'

    movimentacoes_django = Transacao.objects.filter(conta=conta_destino, efetivada=True)
    receitas_dj = movimentacoes_django.filter(tipo='RECEITA').aggregate(t=Sum('valor'))['t'] or 0
    despesas_dj = movimentacoes_django.filter(tipo='DESPESA').aggregate(t=Sum('valor'))['t'] or 0
    conta_destino.saldo_inicial = float(saldo_real) - float(receitas_dj) + float(despesas_dj)
    conta_destino.save()

    for t in transacoes_api:
        id_api = t.get('id')
        if not id_api: continue
        descricao, amount, categoria_api = t.get('description', ''), float(t.get('amount', 0)), t.get('category', '')
        
        desc_lower, cat_lower = descricao.lower(), categoria_api.lower() if categoria_api else ''
        palavras_transferencia = ['caixinha', 'resgate', 'investimento', 'aplicação', 'transfer', 'pagamento de fatura']
        
        if any(p in desc_lower for p in palavras_transferencia) or cat_lower == 'transfers':
            tipo, valor = 'TRANSFERENCIA', abs(amount)
        elif amount < 0:
            tipo, valor = 'DESPESA', abs(amount)
        else:
            tipo, valor = 'RECEITA', amount

        data_alvo = parse_datetime(t.get('date')).date() if t.get('date') else timezone.now().date()
        efetivada = True if t.get('status') == 'POSTED' else False

        categoria, _ = CategoriaFinanceira.objects.get_or_create(nome=categoria_api or 'Outros', defaults={'tipo': 'DESPESA', 'cor': '#95a5a6'})

        Transacao.objects.update_or_create(id_api=id_api, defaults={'descricao': descricao, 'tipo': tipo, 'valor': valor, 'data_vencimento': data_alvo, 'data_pagamento': data_alvo if efetivada else None, 'conta': conta_destino, 'categoria': categoria, 'efetivada': efetivada})
    return 'Conta Atualizada.'


def sincronizar_cartao_credito(nome_cartao='Meu Cartão'):
    token = obter_token_pluggy()
    if not token: return 'Falha.'
    
    forcar_atualizacao_pluggy(ACCOUNT_ID_CREDITO, token)
    transacoes_api = buscar_transacoes_api(ACCOUNT_ID_CREDITO, token)
    hoje = timezone.now().date()

    print(f"\n=== DEBUG CARTÃO: Lendo {len(transacoes_api)} transações ===")

    for t in transacoes_api:
        id_api = t.get('id')
        if not id_api: continue
        
        amount = float(t.get('amount', 0))
        if amount <= 0: continue 
        
        valor = abs(amount)
        data_str = t.get('date')
        data_alvo = parse_datetime(data_str).date() if data_str else hoje
        
        if data_alvo.day <= 2:
            mes_fatura = data_alvo.month
            ano_fatura = data_alvo.year
        else:
            mes_fatura = data_alvo.month + 1
            ano_fatura = data_alvo.year
            if mes_fatura > 12:
                mes_fatura = 1
                ano_fatura += 1
                
        ja_foi_paga = True if (ano_fatura < hoje.year or (ano_fatura == hoje.year and mes_fatura < hoje.month)) else False
        
        # Cria a Fatura se não existir
        fatura, created_fatura = FaturaCartao.objects.get_or_create(
            nome_cartao=nome_cartao, mes=mes_fatura, ano=ano_fatura, 
            defaults={'data_fechamento': date(ano_fatura, mes_fatura, 2), 'data_vencimento': date(ano_fatura, mes_fatura, 10), 'paga': ja_foi_paga}
        )
        
        categoria, _ = CategoriaFinanceira.objects.get_or_create(nome=t.get('category') or 'Outros', defaults={'tipo': 'DESPESA', 'cor': '#95a5a6'})
        
        # Guarda a Transação
        transacao_obj, created_trans = TransacaoCartao.objects.update_or_create(
            id_api=id_api, 
            defaults={'fatura': fatura, 'descricao': t.get('description', 'Compra'), 'valor': valor, 'data_compra': data_alvo, 'categoria': categoria}
        )

        # Print para vermos as compras de Março e Abril no terminal!
        if data_alvo.month >= 3 and data_alvo.year == 2026:
            acao = "NOVA" if created_trans else "EXISTENTE"
            print(f"[{acao}] {data_alvo.strftime('%d/%m')} | R$ {valor:>6.2f} | Fatura: {mes_fatura:02d}/{ano_fatura} | {t.get('description')[:20]}")

    print("==============================================================\n")
    return 'Cartão Atualizado.'