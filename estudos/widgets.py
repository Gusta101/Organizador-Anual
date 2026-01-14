import json
from django import forms

class MultiLinkWidget(forms.Widget):
    template_name = 'widgets/multi_link_widget.html'

    def format_value(self, value):
        if value is None or value == '':
            return '[]'
        return value