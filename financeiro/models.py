from django.db import models
from django.utils import timezone
from django.db.models import Sum

class Conta(models.Model):
    TIPO_CHOICES = [
        ('CORRENTE', 'Conta Corrente'),
        ('POUPANCA', 'Poupança'),
        ('DINHEIRO', 'Dinheiro Físico'),
    ]
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='CORRENTE')
    saldo_inicial = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    data_saldo_inicial = models.DateField(default=timezone.now)
    
    @property
    def saldo_atual(self):
        # Substitua 'transacao_set' pelo related_name definido na sua ForeignKey, 
        # ou deixe assim se não definiu um (padrão do Django).
        
        receitas = self.transacao_set.filter(
            tipo='receita', # Substitua pelo valor exato que você usa para receita
            data__gte=self.data_saldo_inicial
        ).aggregate(total=Sum('valor'))['total'] or 0

        despesas = self.transacao_set.filter(
            tipo='despesa', # Substitua pelo valor exato que você usa para despesa
            data__gte=self.data_saldo_inicial
        ).aggregate(total=Sum('valor'))['total'] or 0

        return self.saldo_inicial + receitas - despesas

    def __str__(self):
        return self.nome

class CartaoCredito(models.Model):
    nome = models.CharField(max_length=100)
    limite_total = models.DecimalField(max_digits=12, decimal_places=2)
    dia_fechamento = models.IntegerField(help_text="Dia em que a fatura fecha (1 a 31)")
    dia_vencimento = models.IntegerField(help_text="Dia em que a fatura vence (1 a 31)")
    conta_padrao_pagamento = models.ForeignKey(
        Conta, on_delete=models.SET_NULL, null=True, blank=True, related_name='cartoes'
    )

    def __str__(self):
        return self.nome

class Categoria(models.Model):
    TIPO_CHOICES = [
        ('RECEITA', 'Receita'),
        ('DESPESA', 'Despesa'),
        ('TRANSFERENCIA', 'Transferência Interna'),
    ]
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    orcamento_mensal_teto = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True, help_text="Limite de gastos mensais para a função de Budgeting"
    )
    is_sistema = models.BooleanField(default=False, help_text="Impede que o usuário delete categorias nativas do app")

    def __str__(self):
        return f"{self.nome} ({self.get_tipo_display()})"

class RegraCategorizacao(models.Model):
    palavra_chave = models.CharField(max_length=100, unique=True, help_text="Trecho de texto esperado no extrato (ex: IFOOD)")
    categoria_destino = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name='regras')

    def __str__(self):
        return f"Se contiver '{self.palavra_chave}' -> {self.categoria_destino.nome}"

class TransacaoRecorrente(models.Model):
    TIPO_CHOICES = [
        ('RECEITA', 'Receita'),
        ('DESPESA', 'Despesa'),
    ]
    descricao = models.CharField(max_length=255)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name='recorrentes')
    dia_vencimento = models.IntegerField(help_text="Dia do mês (1 a 31) que costuma ocorrer")
    is_ativa = models.BooleanField(default=True, help_text="Permite pausar sem deletar do histórico")

    def __str__(self):
        return self.descricao

class TransacaoPrevista(models.Model):
    TIPO_CHOICES = [
        ('RECEITA', 'Receita'),
        ('DESPESA', 'Despesa'),
    ]
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('EFETIVADA_PARCIAL', 'Efetivada Parcialmente'),
        ('CONCLUIDA', 'Concluída'),
    ]
    descricao = models.CharField(max_length=255)
    valor_previsto = models.DecimalField(max_digits=12, decimal_places=2)
    data_prevista = models.DateField()
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name='previstas')
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    
    # Para lidar com parcelamentos de cartão ou de crediário
    parcela_atual = models.IntegerField(default=1)
    total_parcelas = models.IntegerField(default=1)
    cartao_credito = models.ForeignKey(CartaoCredito, on_delete=models.SET_NULL, null=True, blank=True, related_name='previstas')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE')

    def __str__(self):
        if self.total_parcelas > 1:
            return f"{self.descricao} ({self.parcela_atual}/{self.total_parcelas})"
        return self.descricao

class TransacaoEfetivada(models.Model):
    """
    Esta tabela será alimentada pelos CSVs e OFX.
    O saldo das contas e as faturas são a soma das linhas desta tabela.
    """
    TIPO_CHOICES = [
        ('RECEITA', 'Receita'),
        ('DESPESA', 'Despesa'),
    ]
    identificador_banco = models.CharField(
        max_length=255, null=True, blank=True, unique=True, 
        help_text="UUID da conta corrente do Nubank, ou Hash gerado no script de importação do Cartão"
    )
    descricao_banco = models.CharField(max_length=255, help_text="Descrição original que veio no extrato")
    descricao_customizada = models.CharField(max_length=255, null=True, blank=True, help_text="Nome editado pelo usuário")
    valor = models.DecimalField(max_digits=12, decimal_places=2, help_text="Sempre absoluto. O 'tipo' dita a matemática.")
    data_efetivacao = models.DateField()
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    
    # Relações que indicam ONDE a transação ocorreu (deve ter conta OU cartao preenchido)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, null=True, blank=True, related_name='efetivadas')
    conta = models.ForeignKey(Conta, on_delete=models.PROTECT, null=True, blank=True, related_name='efetivadas')
    cartao_credito = models.ForeignKey(CartaoCredito, on_delete=models.PROTECT, null=True, blank=True, related_name='efetivadas')
    
    # Conciliação: Liga a realidade (extrato) à expectativa (prevista/recorrente)
    match_prevista = models.ForeignKey(TransacaoPrevista, on_delete=models.SET_NULL, null=True, blank=True, related_name='matches_efetivados')
    match_recorrente = models.ForeignKey(TransacaoRecorrente, on_delete=models.SET_NULL, null=True, blank=True, related_name='matches_efetivados')

    def __str__(self):
        nome = self.descricao_customizada or self.descricao_banco
        return f"{nome} - R$ {self.valor}"

class TransferenciaInterna(models.Model):
    """
    Para movimentações que não alteram o patrimônio (ex: Pagamento da fatura do cartão, ou CC -> Poupança).
    """
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    data = models.DateField()
    conta_origem = models.ForeignKey(Conta, on_delete=models.PROTECT, related_name='transferencias_origem')
    conta_destino = models.ForeignKey(Conta, on_delete=models.PROTECT, null=True, blank=True, related_name='transferencias_destino')
    cartao_destino = models.ForeignKey(CartaoCredito, on_delete=models.PROTECT, null=True, blank=True, related_name='pagamentos_fatura')

    def __str__(self):
        return f"Transferência R$ {self.valor} em {self.data}"
