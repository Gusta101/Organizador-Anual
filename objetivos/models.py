from django.db import models

class ObjetivoMacro(models.Model):
    OPCOES_UNIDADE = [
        ('PAGINAS', 'Páginas'),
        ('REAIS', 'Reais (R$)'),
        ('MINUTOS', 'Minutos'),
        ('HORAS', 'Horas')
    ]
    
    # Tipos de visualização e comportamento
    TIPO = [
        ('CHECKLIST', 'Checklist (Sim/Não)'), # Ex: Skin care, Ir ao médico
        ('PROGRESSO', 'Progresso (Acumulativo)'), # Ex: Ler páginas, Juntar dinheiro, Estudar horas
    ]
    
    MODULO = [
        ('FINANCEIRO', 'Financeiro'),
        ('ESTUDOS', 'Estudos'),
        ('SAUDE', 'Saúde'),
        ('TRABALHO', 'Trabalho'),
        ('HOBBIES', 'Hobbies'),
        ('AUTOCUIDADO', 'Autocuidado'),
    ]

    # Frequência para gerar as metas no calendário
    FREQUENCIA = [
        ('UNICA', 'Única'),
        ('DIARIA', 'Diária'),
        ('SEMANAL', 'Semanal'),
        ('MENSAL', 'Mensal'),
    ]

    titulo = models.CharField(max_length=200)
    descricao = models.TextField(blank=True, null=True)
    modulo = models.CharField(max_length=50, choices=MODULO)
    tipo = models.CharField(max_length=50, choices=TIPO, default='CHECKLIST')
    
    # Configuração de Recorrência
    frequencia = models.CharField(max_length=50, choices=FREQUENCIA, default='UNICA')
    # Ex: dias da semana '0,2,4' (seg, qua, sex) para filtrar a criação
    dias_especificos = models.CharField(max_length=50, blank=True, null=True) 
    
    # Para metas de Progresso (flexibilidade total de unidade)
    meta_valor_total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    unidade_medida = models.CharField(max_length=50, choices=OPCOES_UNIDADE, blank=True, null=True) # Ex: 'Páginas', 'R$', 'Minutos', 'Litros'

    data_inicio = models.DateTimeField(auto_now_add=True)
    data_limite = models.DateTimeField(null=True, blank=True)
    arquivado = models.BooleanField(default=False) # Para esconder objetivos antigos sem deletar

    def __str__(self):
        return f"{self.titulo} ({self.get_modulo_display()})"

# ---------------------------------------------------------
# AS METAS QUE VÃO PARA O CALENDÁRIO
# ---------------------------------------------------------

class MetaDiaria(models.Model):
    """
    Tabela unificada para itens que aparecem no calendário.
    Representa UMA instância de esforço (um dia específico ou uma semana específica).
    """
    objetivo = models.ForeignKey(ObjetivoMacro, on_delete=models.CASCADE, related_name='historico_metas')
    data = models.DateField() # A data que isso aparece no calendário
    
    # Se for CHECKLIST (Skin care, Remedio)
    realizado = models.BooleanField(default=False)
    
    # Se for PROGRESSO (Leitura, Dinheiro, Horas)
    valor_meta = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True) # Quanto eu devia fazer hoje/nessa semana?
    valor_atingido = models.DecimalField(max_digits=10, decimal_places=2, default=0) # Quanto eu realmente fiz?
    
    observacoes = models.TextField(blank=True, null=True) # "Não consegui ler pq tive dor de cabeça"
    
    class Meta:
        ordering = ['data']

    @property
    def percentual(self):
        """Calcula progresso para barras de carregamento"""
        if self.objetivo.tipo == 'CHECKLIST':
            return 100 if self.realizado else 0
        
        if not self.valor_meta or self.valor_meta == 0:
            return 0
        return (self.valor_atingido / self.valor_meta) * 100

    def __str__(self):
        return f"{self.objetivo.titulo} - {self.data}"