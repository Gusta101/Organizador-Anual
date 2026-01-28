from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum
from .models import MetaDiaria, ObjetivoMacro

def gera_metas_futuras(objetivo_id):
    objetivo = ObjetivoMacro.objects.get(id=objetivo_id)
    
    hoje = timezone.now().date()
    data_limite_janela = hoje + timedelta(days=90)
    
    if objetivo.data_limite:
        data_final = min(objetivo.data_limite.date(), data_limite_janela)
    else:
        data_final = data_limite_janela

    ultima_meta = objetivo.historico_metas.order_by('-data').first()
    if ultima_meta:
        proxima_data = ultima_meta.data + timedelta(days=1)
    else:
        proxima_data = objetivo.data_criacao.date()

    # Se a próxima data já passou da janela ou da data limite do objetivo, paramos
    if proxima_data > data_final:
        return

    # 3. Lógica de Validação de Conclusão (Para não criar metas infinitas se já acabou)
    if objetivo.tipo == 'PROGRESSO' and objetivo.meta_valor_total:
        total_atingido = objetivo.historico_metas.aggregate(soma=Sum('valor_atingido'))['soma'] or 0
        if total_atingido >= objetivo.meta_valor_total:
            return # Meta já concluída, não cria novos dias

    # 4. Loop de Criação
    novas_metas = []
    
    while proxima_data <= data_final:
        criar_dia = False
        
        # Filtro de Frequência
        if objetivo.frequencia == 'DIARIA':
            # Filtro de Dias Específicos (Ex: "0,2,4")
            if objetivo.dias_especificos:
                dias_permitidos = [int(d) for d in objetivo.dias_especificos.split(',') if d.isdigit()]
                if proxima_data.weekday() in dias_permitidos:
                    criar_dia = True
                else:
                    criar_dia = False # Força falso se não for dia permitido
            else:
                criar_dia = True
        elif objetivo.frequencia == 'SEMANAL':
            # Exemplo: Cria apenas na Sábado (6) se não especificado
            if proxima_data.weekday() == 6: 
                criar_dia = True
        elif objetivo.frequencia == 'MENSAL':
            if proxima_data.day == objetivo.data_inicio.day:
                criar_dia = True
        elif objetivo.frequencia == 'UNICA':
            if proxima_data == objetivo.data_inicio.date():
                criar_dia = True
        
        
        if criar_dia:
            # Cálculo do valor diário (Estimativa simples)
            valor_sugerido = 0
            if objetivo.tipo == 'PROGRESSO' and objetivo.meta_valor_total:
                if objetivo.meta_valor_elementar and objetivo.meta_valor_elementar > 0:
                    valor_sugerido = objetivo.meta_valor_elementar
                    valor_acumulado = sum([m.valor_meta for m in novas_metas]) + valor_sugerido
                    if (valor_acumulado + valor_sugerido) > objetivo.meta_valor_total:
                        valor_sugerido = objetivo.meta_valor_total - valor_acumulado
                else:
                    valor_sugerido = objetivo.meta_valor_total / ((data_final - proxima_data).days + 1)

            meta = MetaDiaria(
                objetivo=objetivo,
                data=proxima_data,
                valor_meta=valor_sugerido if valor_sugerido > 0 else None
            )
            novas_metas.append(meta)
            
            if objetivo.tipo == 'PROGRESSO' and objetivo.meta_valor_total:
                total_gerado = sum(m.valor_meta for m in novas_metas if m.valor_meta)
                if total_gerado >= objetivo.meta_valor_total:
                    break

        # Avança o dia e verifica se deve parar (caso seja FREQUENCIA UNICA, para no primeiro)
        proxima_data += timedelta(days=1)
        if objetivo.frequencia == 'UNICA':
            break

    # Bulk create é muito mais rápido que salvar um por um
    if novas_metas:
        MetaDiaria.objects.bulk_create(novas_metas)