from django.http import JsonResponse
from .pluggy_service import sincronizar_conta_corrente, sincronizar_cartao_credito
from .models import Conta

def forcar_sincronizacao(request):
    '''
    Gatilho da Pipeline de Dados. 
    Basta aceder a /financeiro/sincronizar/ para a magia acontecer.
    '''
    try:
        res_cartao = sincronizar_cartao_credito('Meu Cartão')
        
        res_conta = 'Nenhuma conta corrente ativa encontrada.'
        conta = Conta.objects.filter(ativa=True, tipo='CORRENTE').first()
        if conta:
            res_conta = sincronizar_conta_corrente(conta.id)
            
        return JsonResponse({
            'status': 'Sucesso',
            'log_cartao': res_cartao,
            'log_corrente': res_conta,
            'mensagem': 'Banco de dados atualizado. Pode atualizar o Power BI!'
        })
        
    except Exception as e:
        return JsonResponse({'status': 'Erro', 'detalhe': str(e)}, status=500)