from django.utils import timezone
from django import forms
from .models import ObjetivoMacro

class ObjetivoMacroForm(forms.ModelForm):
    class Meta:
        model = ObjetivoMacro
        
        fields = [
            'titulo',
            'descricao',
            'modulo',
            'tipo',
            'unidade_medida',
            'meta_valor_total',
            'meta_valor_elementar',
            'frequencia',
            'dias_especificos',
            'ignorar_feriados',
            'data_semana_especifica',
            'data_especifica',
            'data_limite',
        ]
        
        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': 'form-control m-3',
                }),
            'descricao': forms.Textarea(attrs={
                'rows': 3, 
                'class': 'form-control m-3',
                }),
            'modulo': forms.Select(attrs={
                'class': 'form-control m-3',
                }),
            'tipo': forms.Select(attrs={
                'class': 'form-control m-3',
                'data-toggle-group': 'tipo',
                }),
            'unidade_medida': forms.Select(attrs={
                'class': 'form-control m-3',
                'data-group': 'tipo', 
                'data-show-on': 'PROGRESSO', 
                'data-use-parent': 'true', 
                }),
            'meta_valor_total': forms.NumberInput(attrs={
                'class': 'form-control m-3',
                'data-group': 'tipo', 
                'data-show-on': 'PROGRESSO', 
                'data-use-parent': 'true', 
                }),
            'meta_valor_elementar': forms.NumberInput(attrs={
                'class': 'form-control m-3',
                'data-group': 'tipo', 
                'data-show-on': 'PROGRESSO', 
                'data-use-parent': 'true', 
                }),
            'frequencia': forms.Select(attrs={
                'class': 'form-control m-3',
                'data-toggle-group': 'frequencia',
                }),
            'dias_especificos': forms.TextInput(attrs={
                'class': 'form-control m-3', 
                'data-group': 'frequencia', 
                'data-show-on': 'DIARIA', 
                'data-use-parent': 'true', 
                'placeholder': 'Ex: Segunda, Quarta, Sexta'
                }),
            'ignorar_feriados': forms.CheckboxInput(attrs={
                'class': 'form-check-input m-3', 
                'data-group': 'frequencia', 
                'data-show-on': 'DIARIA', 
                'data-use-parent': 'true'
                }),
            'data_semana_especifica': forms.NumberInput(attrs={
                'class': 'form-control m-3', 
                'min': '0',
                'max': '6',
                'data-group': 'frequencia', 
                'data-show-on': 'SEMANAL', 
                'data-use-parent': 'true', 
                'placeholder': '0=Dom, 1=Seg, ..., 6=Sáb'
                }),
            'data_especifica': forms.DateInput(attrs={
                'type': 'date', 
                'class': 'form-control m-3', 
                'data-group': 'frequencia', 
                'data-show-on': 'UNICA|MENSAL', 
                'data-use-parent': 'true'
                }),
            'data_limite': forms.DateInput(attrs={
                'type': 'date', 
                'class': 'form-control m-3', 
                'data-group': 'frequencia', 
                'data-show-on': 'DIARIA|SEMANAL|MENSAL', 
                'data-use-parent': 'true'
                }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['titulo'].label = "Título"
        self.fields['descricao'].label = "Descrição"
        self.fields['modulo'].label = "Módulo Relacionado"
        self.fields['tipo'].label = "Tipo de Monitoramento"
        self.fields['unidade_medida'].label = "Unidade de Medida"
        self.fields['meta_valor_total'].label = "Meta Final"
        self.fields['meta_valor_elementar'].label = "Meta por Ciclo"
        self.fields['frequencia'].label = "Frequência"
        self.fields['dias_especificos'].label = "Dias da Semana"
        self.fields['ignorar_feriados'].label = "Ignorar Feriados?"
        self.fields['data_semana_especifica'].label = "Dia da Semana"
        self.fields['data_especifica'].label = "Data"
        self.fields['data_limite'].label = "Prazo Final"