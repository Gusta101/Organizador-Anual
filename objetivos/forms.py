from django.utils import timezone
from django import forms
from .models import ObjetivoMacro

class ObjetivoMacroForm(forms.ModelForm):
    class Meta:
        model = ObjetivoMacro
        fields = ['titulo', 'descricao', 'tipo', 'modulo', 'frequencia', 'dias_especificos', 'meta_valor_elementar', 'meta_valor_total', 'unidade_medida', 'data_inicio', 'data_limite', 'ignorar_feriados']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control m-3'}),
            'descricao': forms.Textarea(attrs={'rows': 3, 'class': 'form-control m-3'}),
            'tipo': forms.Select(attrs={'class': 'form-control m-3'}),
            'modulo': forms.Select(attrs={'class': 'form-control m-3'}),
            'frequencia': forms.Select(attrs={'class': 'form-control m-3'}),
            'dias_especificos': forms.TextInput(attrs={'class': 'form-control m-3', 'placeholder': 'Ex: Segunda, Quarta, Sexta'}),
            'meta_valor_elementar': forms.NumberInput(attrs={'class': 'form-control m-3'}),
            'meta_valor_total': forms.NumberInput(attrs={'class': 'form-control m-3'}),
            'unidade_medida': forms.Select(attrs={'class': 'form-control m-3'}),
            'data_inicio': forms.DateInput(attrs={'type': 'date', 'class': 'form-control m-3'}),
            'data_limite': forms.DateInput(attrs={'type': 'date', 'class': 'form-control m-3'}),
            'ignorar_feriados': forms.CheckboxInput(attrs={'class': 'form-check-input m-3'}),
        }