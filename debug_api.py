import os
import requests
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
CLIENT_ID = os.getenv('PLUGGY_CLIENT_ID')
SECRET = os.getenv('PLUGGY_CLIENT_SECRET')
ACCOUNT_CREDITO = os.getenv('ACCOUNT_ID_CREDITO')
BASE_URL = "https://api.pluggy.ai"

print("1. Autenticando...")
response = requests.post(f"{BASE_URL}/auth", json={"clientId": CLIENT_ID, "clientSecret": SECRET})
token = response.json().get('apiKey')

print("2. Puxando histórico completo do cartão...")
headers = {"accept": "application/json", "X-API-KEY": token}
# pageSize 500 garante que pegamos o máximo de dados de uma vez
res = requests.get(f"{BASE_URL}/transactions", headers=headers, params={"accountId": ACCOUNT_CREDITO, "pageSize": 500})
transacoes = res.json().get('results', [])

print(f"Total de registros encontrados: {len(transacoes)}\n")

compras_marco = []
total_marco = 0.0

for t in transacoes:
    amount = float(t.get('amount', 0))
    
    # Ignora pagamentos e estornos
    if amount <= 0: 
        continue 

    data_str = t.get('date')
    if data_str:
        data_compra = datetime.fromisoformat(data_str.replace('Z', '+00:00'))

        # A nossa Regra de Fechamento (Dia 2)
        if data_compra.day <= 2:
            mes = data_compra.month
            ano = data_compra.year
        else:
            mes = data_compra.month + 1
            ano = data_compra.year
            if mes > 12: 
                mes = 1
                ano += 1

        # Filtra estritamente as compras que caíram em Março de 2026
        if mes == 3 and ano == 2026:
            compras_marco.append({
                'data_raw': data_compra,
                'data_formatada': data_compra.strftime('%d/%m/%Y'),
                'valor': amount,
                'desc': t.get('description')[:30]
            })
            total_marco += amount

# Imprime em ordem cronológica
compras_marco.sort(key=lambda x: x['data_raw'])

print("=== COMPRAS COMPUTADAS PARA A FATURA DE MARÇO ===")
for c in compras_marco:
    print(f"{c['data_formatada']} | R$ {c['valor']:>6.2f} | {c['desc']}")

print("-" * 50)
print(f"TOTAL SOMADO: R$ {total_marco:.2f}")
print("=" * 50)