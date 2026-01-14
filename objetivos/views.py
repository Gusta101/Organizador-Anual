from django.shortcuts import render, redirect, reverse
from .models import ObjetivoMacro
from .forms import ObjetivoMacroForm

# Importe os formulários dos outros apps conforme for criando
from estudos.forms import AssuntoForm
# from financeiro.forms import MetaFinanceiraForm (Exemplo futuro)

# CONFIGURAÇÃO CENTRAL: Mapeia 'Opção do Choice' -> 'Classe do Form'
FORM_MAPPING = {
    'ESTUDOS': {
        'form_class': AssuntoForm,
        'prefix': 'estudos',
        'related_name': 'assuntos' # Nome do campo foreign key reverso se precisar
    },
    # Futuramente:
    # 'FINANCEIRO': {'form_class': MetaFinanceiraForm, 'prefix': 'financas'},
}

def criar_objetivo_unificado(request, modulo_origem=None):
    modulo_inicial = modulo_origem.upper() if modulo_origem else None
    
    extra_forms = {}

    if request.method == 'POST':
        objetivo_form = ObjetivoMacroForm(request.POST, request.FILES, prefix='main')
        
        # Instancia TODOS os forms extras com os dados do POST para validação
        for key, config in FORM_MAPPING.items():
            extra_forms[key] = config['form_class'](request.POST, request.FILES, prefix=config['prefix'])

        if objetivo_form.is_valid():
            # 1. Verifica qual módulo o usuário REALMENTE selecionou no dropdown
            # (Pode ser diferente do modulo_origem se ele mudou na hora)
            modulo_selecionado = objetivo_form.cleaned_data['modulo']
            
            # 2. Salva o objetivo pai primeiro
            objetivo = objetivo_form.save(commit=False)
            
            # Verifica se existe configuração para esse módulo escolhido
            if modulo_selecionado in FORM_MAPPING:
                specific_form = extra_forms[modulo_selecionado]
                
                if specific_form.is_valid():
                    objetivo.save() # Salva o pai
                    
                    # Salva o filho vinculado
                    child = specific_form.save(commit=False)
                    child.objetivo = objetivo
                    child.save()
                    
                    # Redirecionamento Dinâmico:
                    # Se tiver uma rota com o nome do módulo (ex: 'estudos'), vai pra lá.
                    # Senão, vai para o dashboard geral.
                    try:
                        return redirect(modulo_selecionado.lower() + ":home") 
                    except:
                        return redirect('home')
                else:
                    # Erro no form específico (ex: esqueceu o PDF)
                    pass 
            else:
                # É um módulo simples sem formulário extra (ex: 'OUTROS')
                objetivo.save()
                return redirect('home')

    else:
        # GET Request
        objetivo_form = ObjetivoMacroForm(prefix='main', initial={'modulo': modulo_inicial})
        
        # Inicializa todos os forms extras vazios
        for key, config in FORM_MAPPING.items():
            extra_forms[key] = config['form_class'](prefix=config['prefix'])

    return render(request, 'objetivos/formulario.html', {
        'objetivo_form': objetivo_form,
        'extra_forms': extra_forms, # Passamos o dicionário inteiro
        'modulo_inicial': modulo_inicial # Para o JS saber qual abrir de cara
    })