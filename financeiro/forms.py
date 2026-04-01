from django import forms
from .models import TransacaoPrevista, TransacaoRecorrente

class TransacaoPrevistaForm(forms.ModelForm):
    class Meta:
        model = TransacaoPrevista
        fields = ['descricao', 'valor_previsto', 'data_prevista', 'categoria', 'tipo', 'cartao_credito', 'total_parcelas']
        widgets = {
            'data_prevista': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control'}),
            'valor_previsto': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'cartao_credito': forms.Select(attrs={'class': 'form-select'}),
            'total_parcelas': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
        }

class TransacaoRecorrenteForm(forms.ModelForm):
    class Meta:
        model = TransacaoRecorrente
        fields = ['descricao', 'valor', 'dia_vencimento', 'categoria', 'tipo']
        widgets = {
            'descricao': forms.TextInput(attrs={'class': 'form-control'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'dia_vencimento': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '31'}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
        }
