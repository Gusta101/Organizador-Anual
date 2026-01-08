from django.db import models
from django.utils import timezone
from objetivos.models import ObjetivoMacro

class Assunto(models.Model):
    objetivo = models.ForeignKey(ObjetivoMacro, on_delete=models.CASCADE, related_name='assuntos')
    nome = models.CharField(max_length=200)
    descricao = models.TextField(blank=True, null=True)
    links = models.TextField(blank=True, null=True)
    pdf = models.FileField(upload_to='estudos_pdfs/', blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome