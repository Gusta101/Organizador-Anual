import json
import os
from django.db import models
from django.utils import timezone
from objetivos.models import ObjetivoMacro
import re

def gerar_caminho_arquivo(instance, nome_arquivo):
    if instance.objetivo:
        titulo_limpo = re.sub(r'[^\w\s\.-]', '', instance.objetivo.titulo)
        titulo_limpo = re.sub(r'\s+', '_', titulo_limpo).strip()
    else:
        titulo_limpo = 'sem_objetivo'

    # Retorna o caminho completo: estudos_pdfs/TITULO/arquivo.pdf
    return f'estudos_pdfs/{titulo_limpo}/{nome_arquivo}'

class Assunto(models.Model):
    objetivo = models.ForeignKey(ObjetivoMacro, on_delete=models.CASCADE, related_name='assuntos', default=None, null=True, blank=True)
    links = models.TextField(blank=True, null=True, default="[]")
    pdf = models.FileField(upload_to=gerar_caminho_arquivo, blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    
    @property
    def get_links(self):
        """
        Retorna a string JSON convertida para lista Python.
        Se der erro ou estiver vazio, retorna lista vazia para não quebrar o template.
        """
        if not self.links:
            return []
        
        try:
            return json.loads(self.links)
        except (json.JSONDecodeError, TypeError):
            return []
    
    @property
    def titulo(self):
        if self.objetivo:
            return self.objetivo.titulo
        return "Título Indefinido"
    
    @property
    def descricao(self):
        if self.objetivo:
            return self.objetivo.descricao
        return "Descrição Indefinida"

    @property
    def pdf_filename(self):
        if self.pdf:
            return os.path.basename(self.pdf.name)
        return "Nenhum PDF anexado"

    def __str__(self):
        if self.objetivo:
            return self.objetivo.titulo
        return "Assunto sem Objetivo"