from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import ObjetivoMacro
from .services import gera_metas_futuras # Importe a função acima

@receiver(post_save, sender=ObjetivoMacro)
def trigger_geracao_metas(sender, instance, created, **kwargs):
    # Executa sempre que salva. Se for update, a função 'gera_metas_futuras'
    # é inteligente o suficiente para começar apenas após a última data existente.
    gera_metas_futuras(instance.id)