from django.db.models import Sum
from .models import Transacao
from objetivos.models import MetaDiaria

def atualizar_progresso_objetivo(instance):
    '''
    Sempre que uma transação atrelada a um objetivo for salva e efetivada,
    atualizamos o progresso na MetaDiaria correspondente.
    '''
    # Só processa se a transação estiver vinculada a um objetivo e já tiver saído da conta
    if instance.objetivo_vinculado and instance.efetivada:
        
        data_alvo = instance.data_pagamento or instance.data_vencimento
        
        # Busca ou cria o registro no calendário de metas para aquele dia
        meta, was_created = MetaDiaria.objects.get_or_create(
            objetivo=instance.objetivo_vinculado,
            data=data_alvo,
            defaults={
                'realizado': False,
                'valor_atingido': 0
            }
        )
        
        # Recalcula tudo o que foi aportado neste objetivo específico no dia alvo
        total_aportado_no_dia = Transacao.objects.filter(
            objetivo_vinculado=instance.objetivo_vinculado,
            data_pagamento=data_alvo,
            efetivada=True
        ).aggregate(total=Sum('valor'))['total'] or 0
        
        # Atualiza o modelo de Objetivos
        meta.valor_atingido = total_aportado_no_dia
        
        # Se houver uma meta de valor definida, verifica se já foi batida
        if meta.valor_meta and meta.valor_atingido >= meta.valor_meta:
            meta.realizado = True
            
        meta.save()

def estornar_progresso_objetivo(instance):
    '''
    Se o usuário deletar a transação financeira, o progresso do objetivo deve cair.
    '''
    if instance.objetivo_vinculado and instance.efetivada:
        data_alvo = instance.data_pagamento or instance.data_vencimento
        
        try:
            meta = MetaDiaria.objects.get(
                objetivo=instance.objetivo_vinculado, 
                data=data_alvo
            )
            # Recalcula subtraindo o valor da transação deletada
            novo_total = meta.valor_atingido - instance.valor
            meta.valor_atingido = novo_total if novo_total > 0 else 0
            meta.realizado = False # Remove o check de conclusão por segurança
            meta.save()
        except MetaDiaria.DoesNotExist:
            pass