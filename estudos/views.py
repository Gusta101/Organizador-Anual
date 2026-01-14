import os
from django.http import FileResponse, Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from objetivos.models import ObjetivoMacro, MetaDiaria
from .models import Assunto

def dashboard_estudos(request):
    hoje = timezone.now().date()
    
    metas_hoje = MetaDiaria.objects.filter(
        data=hoje,
        objetivo__modulo='ESTUDOS'
    )
    
    assuntos = Assunto.objects.filter(
        objetivo__modulo='ESTUDOS',
        objetivo__arquivado=False
    )
    
    return render(request, 'estudos/dashboard.html', {
        'metas_hoje': metas_hoje,
        'assuntos': assuntos,
        'data_atual': hoje,
    })

def detalhes_assunto(request, assunto_id):
    hoje = timezone.now().date()
    assunto = get_object_or_404(Assunto, id=assunto_id)
    metas = MetaDiaria.objects.filter(objetivo=assunto.objetivo, data__year=hoje.year, data__month=hoje.month).order_by('-data')
    return render(request, 'estudos/detalhes_assunto.html', {
        'assunto': assunto,
        'metas': metas
    })

def registrar_progresso(request, meta_id):
    if request.method == 'POST':
        meta = get_object_or_404(MetaDiaria, id=meta_id)
        
        if meta.objetivo.tipo == 'CHECKLIST':
            meta.realizado = not meta.realizado
        elif meta.objetivo.tipo == 'PROGRESSO':
            incremento = float(request.POST.get('valor', 0))
            meta.valor_atingido += incremento
        meta.save()    
    return redirect('estudos:estudos')

def visualizar_pdf(request, assunto_id):
    assunto = get_object_or_404(Assunto, id=assunto_id)
    try:
        caminho_arquivo = assunto.pdf.path
        nome_arquivo = os.path.basename(caminho_arquivo)
        
        arquivo = open(caminho_arquivo, 'rb')
        response = FileResponse(arquivo, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{nome_arquivo}"'
        
        return response
    except:
        raise Http404("Erro ao abrir arquivo")