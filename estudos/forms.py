import json
from django import forms
from .models import Assunto
from .widgets import MultiLinkWidget 

class AssuntoForm(forms.ModelForm):
    class Meta:
        model = Assunto
        fields = ['links', 'pdf']
        widgets = {
            'links': MultiLinkWidget(),
            'pdf': forms.FileInput(attrs={'class': 'form-control', 'accept': 'application/pdf'}),
        }

    def clean_links(self):
        data = self.cleaned_data.get('links')
        if not data:
            return json.dumps([])
        try:
            json_list = json.loads(data)
            if not isinstance(json_list, list):
                return json.dumps([])
            return data
        except:
            return json.dumps([])