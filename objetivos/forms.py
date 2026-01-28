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
            'data_semana_especifica',
            'data_especifica',
            'data_limite',
            'ignorar_feriados',
        ]
        
        widgets = {
            'titulo': forms.TextInput(attrs={}),
            'descricao': forms.Textarea(attrs={'rows': 3, 'class': 'form-control m-3 h-auto'}),
            'modulo': forms.Select(attrs={}),
            'tipo': forms.Select(attrs={
                'data-toggle-group': 'tipo',
                }),
            'unidade_medida': forms.Select(attrs={
                'data-group': 'tipo', 
                'data-show-on': 'PROGRESSO', 
                'data-use-parent': 'true', 
                }),
            'meta_valor_total': forms.NumberInput(attrs={
                'data-group': 'tipo', 
                'data-show-on': 'PROGRESSO', 
                'data-use-parent': 'true', 
                }),
            'meta_valor_elementar': forms.NumberInput(attrs={
                'data-group': 'tipo', 
                'data-show-on': 'PROGRESSO', 
                'data-use-parent': 'true', 
                }),
            'frequencia': forms.Select(attrs={
                'data-toggle-group': 'frequencia',
                }),
            'dias_especificos': forms.TextInput(attrs={
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
                'min': '0',
                'max': '6',
                'data-group': 'frequencia', 
                'data-show-on': 'SEMANAL', 
                'data-use-parent': 'true', 
                'placeholder': '0=Dom, 1=Seg, ..., 6=Sáb'
                }),
            'data_especifica': forms.DateInput(attrs={
                'type': 'date', 
                'data-group': 'frequencia', 
                'data-show-on': 'UNICA|MENSAL', 
                'data-use-parent': 'true'
                }),
            'data_limite': forms.DateInput(attrs={
                'type': 'date', 
                'data-group': 'frequencia', 
                'data-show-on': 'DIARIA|SEMANAL|MENSAL', 
                'data-use-parent': 'true'
                }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        for field_name, field in self.fields.items():
            if field_name not in ['descricao', 'ignorar_feriados']:
                field.widget.attrs.update({'class': 'form-control m-3'})
            
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
    
    @property
    def campos_frequencia(self):
        return [
            self['frequencia'],
            self['dias_especificos'],
            self['ignorar_feriados'],
            self['data_semana_especifica'],
            self['data_especifica'],
            self['data_limite'],
        ]
    
    @property
    def campos_tipo(self):
        return [
            self['tipo'],
            self['unidade_medida'],
            self['meta_valor_total'],
            self['meta_valor_elementar'],
        ]