from django import forms
from .models import Transacao, Conta, CategoriaFinanceira, OrcamentoMensal

class TransacaoForm(forms.ModelForm):
    class Meta:
        model = Transacao
        fields = [
            'descricao', 'tipo', 'valor', 'data_vencimento', 
            'data_pagamento', 'conta', 'categoria', 'efetivada', 
            'objetivo_vinculado'
        ]
        widgets = {
            'descricao': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Ex: Pedágio Rio Claro - Piracicaba'
            }),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'valor': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '0.01', 
                'placeholder': '0.00'
            }),
            'data_vencimento': forms.DateInput(attrs={
                'class': 'form-control', 
                'type': 'date'
            }),
            'data_pagamento': forms.DateInput(attrs={
                'class': 'form-control', 
                'type': 'date'
            }),
            'conta': forms.Select(attrs={'class': 'form-control'}),
            'categoria': forms.Select(attrs={'class': 'form-control'}),
            'efetivada': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'objetivo_vinculado': forms.Select(attrs={'class': 'form-control'}),
        }

class ContaForm(forms.ModelForm):
    class Meta:
        model = Conta
        fields = ['nome', 'tipo', 'saldo_inicial', 'ativa']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Ex: Carteira Física'
            }),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'saldo_inicial': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '0.01'
            }),
            'ativa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class CategoriaForm(forms.ModelForm):
    class Meta:
        model = CategoriaFinanceira
        fields = ['nome', 'tipo', 'cor', 'icone']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Ex: Alimentação'
            }),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'cor': forms.TextInput(attrs={
                'class': 'form-control', 
                'type': 'color'
            }),
            'icone': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'fa-solid fa-utensils'
            }),
        }