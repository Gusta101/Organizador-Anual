from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from objetivos.models import ObjetivoMacro, MetaDiaria

def dashboard_estudos(request):
    hoje = timezone.now().date()
    
    metas_hoje = MetaDiaria.objects.filter(
        data=hoje,
        objetivo__modulo='ESTUDOS'
    )
    
    assuntos = ObjetivoMacro.objects.filter(
        modulo='ESTUDOS',
        arquivado=False
    )
    
    return render(request, 'estudos/dashboard.html', {
        'metas_hoje': metas_hoje,
        'assuntos': assuntos,
        'data_atual': hoje,
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

def detalhes_assunto(request, assunto_id):
    hoje = timezone.now().date()
    assunto = get_object_or_404(ObjetivoMacro, id=assunto_id, modulo='ESTUDOS')
    metas = MetaDiaria.objects.filter(objetivo=assunto, data__year=hoje.year, data__month=hoje.month).order_by('-data')
    return render(request, 'estudos/detalhes_assunto.html', {
        'assunto': assunto,
        'metas': metas
    })
    