from django.core.management.base import BaseCommand
from objetivos.models import ObjetivoMacro
from objetivos.services import gera_metas_futuras

class Command(BaseCommand):
    help = 'Verifica todos os objetivos ativos e gera metas para os próximos 3 meses'

    def handle(self, *args, **kwargs):
        # Pega apenas objetivos não arquivados e que (opcionalmente) não venceram a data limite final
        objetivos_ativos = ObjetivoMacro.objects.filter(arquivado=False)
        
        count = 0
        for objetivo in objetivos_ativos:
            gera_metas_futuras(objetivo.id)
            count += 1
            
        self.stdout.write(self.style.SUCCESS(f'Processo finalizado. {count} objetivos verificados.'))