from ofxparse import OfxParser
from decimal import Decimal
from .models import TransacaoEfetivada, RegraCategorizacao

def importar_extrato_ofx(arquivo_ofx, conta_id=None, cartao_id=None):
    """
    Lê um arquivo OFX, classifica as transações e salva no banco de dados.
    Retorna um dicionário com o resumo da operação.
    """
    ofx = OfxParser.parse(arquivo_ofx)
    
    # Busca todas as regras de uma vez para não bater no banco a cada iteração
    regras_ativas = RegraCategorizacao.objects.select_related('categoria_destino').all()
    
    transacoes_para_criar = []
    ignoradas_por_duplicidade = 0

    # O ofxparse guarda as transações dentro do 'statement'
    for transacao_ofx in ofx.account.statement.transactions:
        identificador = transacao_ofx.id
        
        # 1. Verifica duplicidade pelo identificador único do banco
        if TransacaoEfetivada.objects.filter(identificador_banco=identificador).exists():
            ignoradas_por_duplicidade += 1
            continue

        # 2. Prepara os valores e o tipo (Receita/Despesa)
        valor_original = Decimal(str(transacao_ofx.amount))
        tipo = 'RECEITA' if valor_original > 0 else 'DESPESA'
        valor_absoluto = abs(valor_original)
        descricao = transacao_ofx.memo

        # 3. Tenta aplicar as regras de categorização automática
        categoria_encontrada = None
        for regra in regras_ativas:
            if regra.palavra_chave.upper() in descricao.upper():
                categoria_encontrada = regra.categoria_destino
                break

        # 4. Instancia o objeto (ainda sem salvar no banco)
        nova_transacao = TransacaoEfetivada(
            identificador_banco=identificador,
            descricao_banco=descricao,
            valor=valor_absoluto,
            data_efetivacao=transacao_ofx.date.date(),
            tipo=tipo,
            conta_id=conta_id,
            cartao_credito_id=cartao_id,
            categoria=categoria_encontrada
        )
        transacoes_para_criar.append(nova_transacao)

    # 5. Salva todas as novas transações no banco em uma única query (Bulk Create)
    if transacoes_para_criar:
        TransacaoEfetivada.objects.bulk_create(transacoes_para_criar)

    return {
        "importadas": len(transacoes_para_criar),
        "ignoradas": ignoradas_por_duplicidade
    }
