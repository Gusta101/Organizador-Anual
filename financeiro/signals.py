from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.db.models import Sum

from .models import Transacao
from .services import atualizar_progresso_objetivo, estornar_progresso_objetivo

@receiver(post_save, sender=Transacao)
def trigger_atualizar_progresso_objetivo(sender, instance, created, **kwargs):
    atualizar_progresso_objetivo(instance)

@receiver(post_delete, sender=Transacao)
def trigger_estornar_progresso_objetivo(sender, instance, **kwargs):
    estornar_progresso_objetivo(instance)