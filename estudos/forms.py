from django import forms
from .models import Assunto

class AssuntoForm(forms.ModelForm):
    class Meta:
        model = Assunto
        fields = ['links', 'pdf']
        widgets = {
            'links': forms.Textarea(attrs={'rows': 2, 'class': 'form-control m-3', 'placeholder': 'Separe os links por vírgula, como em: link1, link2'}),
            'pdf': forms.FileInput(attrs={'class': 'form-control m-3', 'accept': 'application/pdf'}),
        }