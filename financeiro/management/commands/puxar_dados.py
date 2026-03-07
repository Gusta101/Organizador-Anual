from django.core.management.base import BaseCommand
from financeiro.pluggy_service import sincronizar_conta_corrente, sincronizar_cartao_credito
from financeiro.models import Conta

class Command(BaseCommand):
    help = 'Sincroniza os dados bancários com a API do Pluggy para alimentar o Power BI'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('\n⏳ Iniciando a extração de dados do Pluggy...'))
        
        # 1. Sincroniza o Cartão de Crédito
        self.stdout.write('-> Conectando ao Cartão de Crédito...')
        res_cartao = sincronizar_cartao_credito('Meu Cartão')
        self.stdout.write(self.style.SUCCESS(f'   [OK] {res_cartao}'))
        
        # 2. Sincroniza a Conta Corrente
        self.stdout.write('\n-> Conectando à Conta Corrente...')
        conta = Conta.objects.filter(ativa=True, tipo='CORRENTE').first()
        
        if conta:
            res_conta = sincronizar_conta_corrente(conta.id)
            self.stdout.write(self.style.SUCCESS(f'   [OK] {res_conta}'))
        else:
            self.stdout.write(self.style.ERROR('   [ERRO] Nenhuma Conta Corrente ativa encontrada no banco.'))
            
        self.stdout.write(self.style.WARNING('-' * 50))
        self.stdout.write(self.style.SUCCESS('✨ Extração concluída! O seu SQLite está pronto para o Power BI.\n'))