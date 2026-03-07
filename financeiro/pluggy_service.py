import os
import requests
import time
from dotenv import load_dotenv
from django.utils import timezone
from django.utils.timezone import localtime
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
# e faz um loop (polling) verificando a cada 3 segundos se a atualização terminou, com um timeout de 20 tentativas (1 minuto).
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
        if status not in ['UPDATING', 'WAITING_USER_INPUT', 'LOGIN_IN_PROGRESS']:
            break
        tentativas += 1
    return True

# Esta função busca a lista de transações de uma conta específica na API da Pluggy.
# Retorna uma lista de dicionários contendo os dados brutos de cada movimentação.
def buscar_transacoes_api(account_id, token):
    if not token or not account_id: return []
    url = f"{BASE_URL}/transactions"
    
    response = requests.get(url, headers={"accept": "application/json", "X-API-KEY": token}, params={"accountId": account_id, "pageSize": 500})
    
    if response.status_code == 200: return response.json().get('results', [])
    return []

# Esta função consulta o saldo atual e real da conta lá no banco via Pluggy.
def buscar_saldo_real_api(account_id, token):
    if not token or not account_id: return 0
    url = f'{BASE_URL}/accounts/{account_id}'
    response = requests.get(url, headers={'accept': 'application/json', 'X-API-KEY': token})
    if response.status_code == 200: return response.json().get('balance', 0)
    return 0

# Função principal para sincronizar uma CONTA CORRENTE
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

    conta_destino.saldo_banco = float(saldo_real)
    conta_destino.save()

    # Percorre todas as transações retornadas pela API
    for t in transacoes_api:
        id_api = t.get('id')
        if not id_api: continue
        
        # =======================================================
        # Extração dos dados
        # =======================================================
        descricao = t.get('description', '')
        amount = float(t.get('amount', 0))
        categoria_api = t.get('category', '')
        date_str = t.get('date')
        status = t.get('status')
        
        payment_data = t.get('paymentData') or {}
        metodo_pagamento = payment_data.get('paymentMethod') or 'OTHER' # PIX, TED, BOLETO, OTHER
        
        desc_lower = descricao.lower()
        is_saida = amount < 0
        valor = abs(amount)
        
        # =======================================================
        # Árvore de Decisão do Tipo de Transação
        # =======================================================
        tipo_final = 'DESPESA' if is_saida else 'RECEITA'
        pagamento_fatura = False
        
        # REGRA 1: Pagamento de Fatura do Cartão (Dá baixa automática)
        palavras_fatura = ['fatura', 'pagamento cartão', 'fatura nubank', 'pagamento crédito', 'fatura itau', 'pagamento de fatura', 'fatura santander']
        if is_saida and any(p in desc_lower for p in palavras_fatura):
            tipo_final = 'TRANSFERENCIA'
            pagamento_fatura = True
            
        # REGRA 2: Caixinhas e Investimentos
        elif any(p in desc_lower for p in ['caixinha', 'resgate', 'resgate rdb', 'investimento', 'aplicação', 'aplicação rdb']):
            tipo_final = 'TRANSFERENCIA'
            
        # REGRA 3: Transações PIX para mim mesmo
        elif metodo_pagamento == 'PIX' and any(p in desc_lower for p in conta_destino.gerar_list_nome()):
            tipo_final = 'TRANSFERENCIA'
            is_saida = False
            
        # REGRA 4: Boletos e outros pagamentos
        elif metodo_pagamento == 'BOLETO':
            tipo_final = 'DESPESA'
            
        # =======================================================
        # Define categorias e datas com base nos dados da API
        # =======================================================
        data_alvo = parse_datetime(date_str).date() if date_str else timezone.now().date()
        efetivada = True if status == 'POSTED' else False

        categoria, _ = CategoriaFinanceira.objects.get_or_create(
            nome=categoria_api or 'Outros', 
            defaults={'tipo': 'DESPESA', 'cor': '#95a5a6'}
        )
        
        # =======================================================
        # CONVERSÃO DE FUSO HORÁRIO (UTC -> LOCAL)
        # =======================================================
        if date_str:
            dt_utc = parse_datetime(date_str)
            data_alvo = localtime(dt_utc).date() 
        else:
            data_alvo = timezone.now().date()

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
                'revisada': True
            }
        )
        
        # =======================================================
        # Baixa automática e parcial de fatura (SEM LIMITE DE DIAS)
        # =======================================================
        if created and pagamento_fatura:
            print(f"🔥 Pagamento de Fatura detetado no dia {data_alvo.strftime('%d/%m')}: R$ {valor}")
            
            # Pega simplesmente a fatura mais antiga que ainda está com "paga=False"
            fatura_pendente = FaturaCartao.objects.filter(
                paga=False
            ).order_by('data_vencimento').first()
            
            if fatura_pendente:
                total_fatura = float(fatura_pendente.compras.aggregate(t=Sum('valor'))['t'] or 0)
                
                # Injeta o pagamento de agora no cofre da fatura
                fatura_pendente.valor_pago = float(fatura_pendente.valor_pago) + valor
                
                # Se o cofre encher, a fatura está quitada! (margem de 10 centavos para evitar bugs)
                if fatura_pendente.valor_pago >= (total_fatura - 0.10):
                    fatura_pendente.paga = True
                    print(f"✅ Fatura {fatura_pendente.mes:02d}/{fatura_pendente.ano} QUITADA 100%!")
                else:
                    print(f"⏳ Fatura amortizada. Restam R$ {(total_fatura - float(fatura_pendente.valor_pago)):.2f}")
                    
                fatura_pendente.save()
            else:
                print("⚠️ Nenhum fatura pendente encontrada para alocar este pagamento.")

    return 'Conta Atualizada.'

# Função principal para sincronizar um CARTÃO DE CRÉDITO
def sincronizar_cartao_credito(nome_cartao='Meu Cartão'):
    token = obter_token_pluggy()
    if not token: return 'Falha.'
    
    forcar_atualizacao_pluggy(ACCOUNT_ID_CREDITO, token)
    transacoes_api = buscar_transacoes_api(ACCOUNT_ID_CREDITO, token)
    hoje = timezone.now().date()

    # Percorre todas as transações retornadas pela API
    for t in transacoes_api:
        id_api = t.get('id')
        if not id_api: continue
        
        amount = float(t.get('amount', 0))
        
        if amount <= 0:
            continue
        
        valor = amount
        descricao = t.get('description', 'Compra Cartão')
        categoria_api = t.get('category', '')
        date_str = t.get('date')
        
        # =======================================================
        # CONVERSÃO DE FUSO HORÁRIO (UTC -> LOCAL)
        # =======================================================
        if date_str:
            dt_utc = parse_datetime(date_str)
            data_compra = localtime(dt_utc).date()
        else:
            data_compra = timezone.now().date()
        
        # =======================================================
        # Árvore de Decisão do tipo de transação
        # =======================================================
        credit_data = t.get('creditCardMetadata') or {}
        bill_id = credit_data.get('billId') # ID da fatura
        
        if data_compra.day <= 2:
            mes_fatura = data_compra.month
            ano_fatura = data_compra.year
        else:
            mes_fatura = data_compra.month + 1
            ano_fatura = data_compra.year
            if mes_fatura > 12:
                mes_fatura = 1
                ano_fatura += 1

        ja_foi_paga = True if (ano_fatura < hoje.year or (ano_fatura == hoje.year and mes_fatura < hoje.month)) else False

        fatura = None
        
        if bill_id:
            fatura = FaturaCartao.objects.filter(id_fatura_banco=bill_id).first()
            
        if not fatura:
            fatura = FaturaCartao.objects.filter(nome_cartao=nome_cartao, mes=mes_fatura, ano=ano_fatura).first()
            
        if not fatura:
            fatura = FaturaCartao.objects.create(
                id_fatura_banco=bill_id,
                nome_cartao=nome_cartao,
                mes=mes_fatura,
                ano=ano_fatura,
                data_fechamento=date(ano_fatura, mes_fatura, 2),
                data_vencimento=date(ano_fatura, mes_fatura, 10),
                paga=ja_foi_paga
            )
        elif bill_id and not fatura.id_fatura_banco:
            # Se a fatura já existia (criada pelo fallback), mas agora o banco mandou o ID, nós atualizamos!
            fatura.id_fatura_banco = bill_id
            fatura.save()
        
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
