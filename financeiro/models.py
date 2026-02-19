from django.db import models
from django.utils import timezone
from django.db.models import Sum

from objetivos.models import ObjetivoMacro

class Conta(models.Model):
    '''
    Fase 1: Registro (Múltiplas Carteiras)
    Representa os locais onde o usuário tem saldo físico ou digital.
    '''
    TIPOS_CONTA = [
        ('CORRENTE', 'Conta Corrente'),
        ('POUPANCA', 'Poupança'),
        ('DINHEIRO', 'Dinheiro Físico'),
        ('BENEFICIO', 'Vale Alimentação/Refeição'),
        ('INVESTIMENTO', 'Corretora/Investimentos'),
    ]

    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=50, choices=TIPOS_CONTA, default='CORRENTE')
    saldo_inicial = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    data_criacao = models.DateTimeField(auto_now_add=True)
    ativa = models.BooleanField(default=True)
    
    @property
    def saldo_atual(self):
        # Calcula o saldo atual somando o saldo inicial com as transações efetivadas
        receitas = self.transacoes.filter(tipo='RECEITA', efetivada=True).aggregate(total=Sum('valor'))['total'] or 0
        
        despesas = self.transacoes.filter(tipo='DESPESA', efetivada=True).aggregate(total=Sum('valor'))['total'] or 0
        
        aportes_objetivos = self.transacoes.filter(tipo='TRANSFERENCIA', efetivada=True, objetivo_vinculado__isnull=False).aggregate(total=Sum('valor'))['total'] or 0

        return self.saldo_inicial + receitas - despesas - aportes_objetivos

    def __str__(self):
        return f'{self.nome} ({self.get_tipo_display()})'

class CategoriaFinanceira(models.Model):
    '''
    Fase 1 e 4: Registro e Análise
    Essencial para os gráficos de fluxo de caixa e tetos de gastos.
    '''
    TIPOS_CATEGORIA = [
        ('RECEITA', 'Receita / Ganho'),
        ('DESPESA', 'Despesa / Gasto'),
    ]

    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=50, choices=TIPOS_CATEGORIA)
    cor = models.CharField(max_length=7, default='#000000', help_text='Cor HEX para gráficos')
    icone = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f'{self.nome} - {self.get_tipo_display()}'

class OrcamentoMensal(models.Model):
    '''
    Fase 2: Planejamento
    Define o limite de gastos para uma categoria em um mês específico.
    '''
    categoria = models.ForeignKey(CategoriaFinanceira, on_delete=models.CASCADE, limit_choices_to={'tipo': 'DESPESA'})
    mes = models.IntegerField(help_text='Mês (1-12)')
    ano = models.IntegerField()
    valor_limite = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        unique_together = ['categoria', 'mes', 'ano']

    def __str__(self):
        return f'Orçamento: {self.categoria.nome} - {self.mes}/{self.ano}'

class Transacao(models.Model):
    '''
    Fase 1 e 3: Registro e Crescimento
    A espinha dorsal do app. Pode ser uma despesa, receita ou um aporte em um Objetivo.
    '''
    TIPOS_TRANSACAO = [
        ('RECEITA', 'Receita'),
        ('DESPESA', 'Despesa'),
        ('TRANSFERENCIA', 'Transferência'),
    ]

    descricao = models.CharField(max_length=255)
    tipo = models.CharField(max_length=50, choices=TIPOS_TRANSACAO)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    data_vencimento = models.DateField(default=timezone.now)
    data_pagamento = models.DateField(null=True, blank=True)
    
    conta = models.ForeignKey(Conta, on_delete=models.PROTECT, related_name='transacoes')
    categoria = models.ForeignKey(CategoriaFinanceira, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Status de Efetivação
    efetivada = models.BooleanField(default=False, help_text='Marca se o dinheiro já saiu/entrou na conta de fato')

    # Integração com os Objetivos Macro (Fase 3: Crescimento)
    # Se a transação for um "depósito" para o Carro 2026, vinculamos aqui.
    objetivo_vinculado = models.ForeignKey(
        ObjetivoMacro, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        limit_choices_to={'modulo': 'FINANCEIRO'},
        help_text='Se for um aporte para uma meta, selecione o objetivo.'
    )

    # Para lidar com parcelamentos de forma simples (Pai e Filhos)
    transacao_pai = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='parcelas')
    numero_parcela = models.IntegerField(default=1)
    total_parcelas = models.IntegerField(default=1)

    class Meta:
        ordering = ['-data_vencimento']

    def __str__(self):
        status = 'Pago' if self.efetivada else 'Pendente'
        return f'{self.descricao} | R$ {self.valor} ({status})'

class FaturaCartao(models.Model):
    '''
    Módulo adicional para Fase 1 (Cartão de Crédito)
    Isola os gastos do cartão do saldo da conta até o dia do pagamento.
    '''
    nome_cartao = models.CharField(max_length=100)
    mes = models.IntegerField()
    ano = models.IntegerField()
    data_fechamento = models.DateField()
    data_vencimento = models.DateField()
    paga = models.BooleanField(default=False)

    def __str__(self):
        return f'Fatura {self.nome_cartao} - {self.mes}/{self.ano}'

class TransacaoCartao(models.Model):
    fatura = models.ForeignKey(FaturaCartao, on_delete=models.CASCADE, related_name='compras')
    descricao = models.CharField(max_length=255)
    categoria = models.ForeignKey(CategoriaFinanceira, on_delete=models.SET_NULL, null=True, blank=True)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data_compra = models.DateField(default=timezone.now)
    
    def __str__(self):
        return f'{self.descricao} - R$ {self.valor}'

class RegraAporteAutomatico(models.Model):
    '''
    Fase 3: Distribuição Automática
    Gera aportes em cofres no primeiro dia do mês via Cron Job.
    '''
    objetivo = models.ForeignKey(ObjetivoMacro, on_delete=models.CASCADE, related_name='regras_aporte')
    conta_origem = models.ForeignKey(Conta, on_delete=models.CASCADE)
    valor_fixo = models.DecimalField(max_digits=10, decimal_places=2, help_text='Valor a ser transferido mensalmente')
    
    ativa = models.BooleanField(default=True)
    
    # Campo crucial para evitar duplicidade! Formato esperado: '02-2026'
    ultimo_mes_processado = models.CharField(max_length=7, blank=True, null=True)

    def __str__(self):
        return f'Regra Mensal: R$ {self.valor_fixo} para {self.objetivo.titulo}'
