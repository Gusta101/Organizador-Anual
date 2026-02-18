from django.apps import AppConfig

class FinanceiroConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'financeiro' # O nome exato da pasta do seu app

    def ready(self):
        '''
        Este método roda assim que o app é carregado pelo Django.
        É o local correto para importar os signals e ativá-los.
        '''
        import financeiro.signals