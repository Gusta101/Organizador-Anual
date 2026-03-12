from django.db import models
from django.utils import timezone
from django.db.models import Sum

from objetivos.models import ObjetivoMacro

class Conta(models.Model):
    '''
    Dimensão Conta (dConta no Power BI)
    Representa os locais onde o utilizador tem saldo físico, digital ou crédito.
    '''
    TIPOS_CONTA = [
        ('CORRENTE', 'Conta Corrente'),
        ('POUPANCA', 'Poupança'),
        ('DINHEIRO', 'Dinheiro Físico'),
        ('BENEFICIO', 'Vale Alimentação/Refeição'),
        ('INVESTIMENTO', 'Corretora/Investimentos'),
        ('CARTAO_CREDITO', 'Cartão de Crédito'), # ADICIONADO PARA O BI
    ]
    
    nome_proprietario = models.CharField(max_length=100, help_text='Nome do titular da conta (ex: João Silva)')
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=50, choices=TIPOS_CONTA, default='CORRENTE')
    
    sincronizada_api = models.BooleanField(default=False, help_text='Marque se esta conta é atualizada pelo Pluggy')
    saldo_banco = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, help_text='Saldo absoluto retornado pela API')
    
    saldo_inicial = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    data_criacao = models.DateTimeField(auto_now_add=True)
    ativa = models.BooleanField(default=True)
    
    def gerar_list_nome(self):
        return [p.lower() for p in self.nome.split() if p.lower() not in ['da', 'de', 'do', 'das', 'dos']]
    
    @property
    def saldo_atual(self):
        if self.sincronizada_api:
            return self.saldo_banco
            
        receitas = self.transacoes.filter(tipo='RECEITA', efetivada=True).aggregate(total=Sum('valor'))['total'] or 0
        despesas = self.transacoes.filter(tipo='DESPESA', efetivada=True).aggregate(total=Sum('valor'))['total'] or 0
        aportes_objetivos = self.transacoes.filter(tipo='TRANSFERENCIA', efetivada=True, objetivo_vinculado__isnull=False).aggregate(total=Sum('valor'))['total'] or 0

        return self.saldo_inicial + receitas - despesas - aportes_objetivos

    def __str__(self):
        status_sync = ' [SYNC]' if self.sincronizada_api else ''
        return f'{self.nome} ({self.get_tipo_display()}){status_sync}'

class CategoriaFinanceira(models.Model):
    '''
    Dimensão Categoria (dCategoria no Power BI)
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
    Tabela Fato Principal (fTransacoes no Power BI)
    '''
    TIPOS_TRANSACAO = [
        ('RECEITA', 'Receita'),
        ('DESPESA', 'Despesa'),
        ('TRANSFERENCIA', 'Transferência'),
        ('PAGAMENTO FATURA', 'Pagamento de Fatura'),
    ]

    descricao = models.CharField(max_length=255)
    tipo = models.CharField(max_length=50, choices=TIPOS_TRANSACAO)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    data_vencimento = models.DateField(default=timezone.now)
    data_pagamento = models.DateField(null=True, blank=True)
    
    conta = models.ForeignKey(Conta, on_delete=models.PROTECT, related_name='transacoes')
    categoria = models.ForeignKey(CategoriaFinanceira, on_delete=models.SET_NULL, null=True, blank=True)
    
    efetivada = models.BooleanField(default=False, help_text='Marca se o dinheiro já saiu/entrou na conta de fato')
    revisada = models.BooleanField(default=True)
    id_api = models.CharField(max_length=255, unique=True, null=True, blank=True)
    
    metodo_pagamento = models.CharField(max_length=50, default='OTHER', blank=True, null=True)

    objetivo_vinculado = models.ForeignKey(
        ObjetivoMacro, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        limit_choices_to={'modulo': 'FINANCEIRO'},
        help_text='Se for um aporte para uma meta, selecione o objetivo.'
    )

    transacao_pai = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='parcelas')
    numero_parcela = models.IntegerField(default=1)
    total_parcelas = models.IntegerField(default=1)

    class Meta:
        ordering = ['-data_vencimento']

    def __str__(self):
        status = 'Pago' if self.efetivada else 'Pendente'
        return f'{self.descricao} | R$ {self.valor} ({status})'

class FaturaCartao(models.Model):
    # LIGAÇÃO CRUCIAL PARA O BI: A fatura agora pertence a uma Conta Dimensão
    conta_cartao = models.ForeignKey(Conta, on_delete=models.CASCADE, limit_choices_to={'tipo': 'CARTAO_CREDITO'}, null=True, blank=True)
    
    mes = models.IntegerField()
    ano = models.IntegerField()
    data_fechamento = models.DateField()
    data_vencimento = models.DateField()
    paga = models.BooleanField(default=False)
    id_fatura_banco = models.CharField(max_length=255, null=True, blank=True)
    valor_pago = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def __str__(self):
        nome = self.conta_cartao.nome if self.conta_cartao else 'Cartão Desconhecido'
        return f'Fatura {nome} - {self.mes}/{self.ano}'

class TransacaoCartao(models.Model):
    '''
    Tabela Fato Secundária.
    Adicionados campos "tipo" e "efetivada" para permitir um Append perfeito no Power Query com a Transacao.
    '''
    fatura = models.ForeignKey(FaturaCartao, on_delete=models.CASCADE, related_name='compras')
    descricao = models.CharField(max_length=255)
    categoria = models.ForeignKey(CategoriaFinanceira, on_delete=models.SET_NULL, null=True, blank=True)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data_compra = models.DateField(default=timezone.now)
    
    # CAMPOS ESPELHADOS PARA O BI:
    tipo = models.CharField(max_length=50, default='DESPESA')
    efetivada = models.BooleanField(default=True)
    
    revisada = models.BooleanField(default=False)
    id_api = models.CharField(max_length=255, unique=True, null=True, blank=True)
    
    def __str__(self):
        return f'{self.descricao} - R$ {self.valor}'

class RegraAporteAutomatico(models.Model):
    objetivo = models.ForeignKey(ObjetivoMacro, on_delete=models.CASCADE, related_name='regras_aporte')
    conta_origem = models.ForeignKey(Conta, on_delete=models.CASCADE)
    valor_fixo = models.DecimalField(max_digits=10, decimal_places=2, help_text='Valor a ser transferido mensalmente')
    ativa = models.BooleanField(default=True)
    ultimo_mes_processado = models.CharField(max_length=7, blank=True, null=True)

    def __str__(self):
        return f'Regra Mensal: R$ {self.valor_fixo} para {self.objetivo.titulo}'