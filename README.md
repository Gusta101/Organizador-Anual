# Planejador Anual (Idealização do projeto)
> Futuramente documentação de requisitos formal completa

ESSE É O MEU ANO!

Projeto pessoal que visa o desenvolvimento de uma aplicação web, para facilitar a organização pessoal ao longo do ano, em diversos âmbitos do desenvolvimento pessoal, como Estudos, Trabalho, Finanças, Hobbies, Saúde, e Autocuidados por exemplo.

## Instalação

Após baixar o repositório, cria um arquivo na raiz do proeto, chamado _.env_
Nesse arquivo ficarão suas variáveis de ambiente, e essas informações são secretas. Escreva nesse arquivo as seguintes variáveis:

    DEBUG=True
    ECRET_KEY='(exemplo-de-chave-secreta-pessoal-do-usuario)'
    ALLOWED_HOSTS=localhost,127.0.0.1

Agora, em um ambiente que tenha Python 3.12.1+ instalado - **Altamente recomendado o uso de um ambiente virtual python (venv)** -, rode os seguintes comandos de prompt na raiz do projeto:

    pip install -r requirements.txt

    python manage.py makemigrations

    python manage.py migrate

    python manage.py runserver

Pronto! Agora o projeto está sendo executado no seu computador no modo de desenvolvimento (DEBUG), basta acessar [127.0.0.1:8000](http://127.0.0.1:8000/) no seu navegador para vê-lo funcionando.

# Definição de Requisitos (Informal, para organização pessoal)

## Geral:

### O software deve conter um menu lateral para navegar entre as principais telas:

* Financeiro  
* Trabalho  
* Estudos  
* Hobbies  
* Autocuidado/Beleza  
* Saúde

### As principais funcionalidades do site são:

* No topo da tela devem haver dados como: Data atual, Tela atual  
* Mais funcionalidades gerais serão adicionadas futuramente…

## Financeiro

O módulo financeiro é focado no controle de fluxo de caixa, planejamento orçamentário e acompanhamento de metas de longo prazo.

### 1. Fase de Registro (Gestão de Transações)
* **Saldo Consolidado:** Visualização do saldo total somando múltiplas carteiras (bancos, dinheiro físico, benefícios).
* **Entrada e Saída do Mês:** Resumo rápido do fluxo financeiro do período atual.
* **Categorização Inteligente:** Registro de gastos/receitas com campos para Valor, Data, Descrição, Status (Pago/Pendente) e Forma de Pagamento.
    * **Tags e Categorias:** Classificação obrigatória (Lazer, Mercado, Fixos) para geração de relatórios.
* **Gestão de Recorrência e Parcelamentos:** * Checkbox "Mensal" para gerar automaticamente faturas de meses seguintes.
    * Cálculo automático de compras parceladas e seu impacto no saldo futuro.
* **Módulo de Cartão de Crédito:** Gestão de faturas onde o gasto compromete o limite de forma imediata, mas o abatimento do saldo ocorre apenas no vencimento.

### 2. Fase de Planejamento (Budgets e "E se?")
* **Limites de Gastos (Budgets):** Definição de tetos mensais por categoria (ex: limite para Combustível/Viagens).
* **Alertas de Consumo:** Notificação visual ao atingir 80% do limite estipulado para uma categoria.
* **Recurso "E se?":** Calculadora de imprevistos que reserva um valor extra hipotético e mostra o impacto no saldo final do mês.

### 3. Fase de Crescimento (Objetivos e Reservas)
* **Objetivos Macros (Cofres):** Cards com barras de progresso visual, valor atual, alvo e data limite (ex: "Viagem 2026", "Primeiro Carro").
* **Reserva de Emergência:** Categoria especial de meta para proteção financeira, separada dos objetivos de consumo.
* **Distribuição Automática:** Funcionalidade para alocar automaticamente uma porcentagem ou valor fixo da receita para metas específicas na virada do mês.

### 4. Fase de Análise (Dashboard e Projeções)
* **Dashboard Interativo:** Gráficos (Pizza ou Barra) detalhando a distribuição de gastos e fluxo de caixa.
* **Fechamento e Projeção:** Painel que indica, com base no ritmo atual de poupança, em qual mês/ano exato cada objetivo macro será alcançado.
* **Relatório de Desempenho:** Comparativo visual entre o que foi planejado (Budgets) e o que foi efetivamente gasto.

### Na integração com o calendário teremos em cada dia:
* Checklist de pagamentos manuais e vencimentos de faturas do dia.
* Lembretes de entradas esperadas (salários, rendimentos).

## Trabalho 

### A tela Trabalho deve conter:

* Kanban Pessoal: Colunas "To Do", "Doing", "Done" para suas tarefas diárias/semanais.

* Objetivo Macro: Objetivo de carreira, com uma descrição de como deverá alcançar e definição de metas diárias para cumprir esse objetivo até o fim do ano. 

* Calendário com datas e prazos.

### Na integração com o calendário teremos em cada dia:

- Checklist dos objetivos macro para o dia  
- Prazos do dia



## Estudos

Toda semana o usuário deverá entrar no aplicativo para registrar quais dias da semana ele estudou cada determinado assunto como uma checklist.  
Deve ser possível criar e deletar os cards (Assuntos estudados), e também adicionar e excluir dados a respeito, como os links e pdfs

### A tela Estudos deve conter:

* Lista de assuntos que o usuário deseja estudar, dividido em Cards. 
  * Cada card deverá conter nele mesmo, ou em um popup/tela individual, os dados do assunto, sejam eles links ou arquivos PDF

* Deverá ter acesso e visualização do calendário principal, mas somente com as informações referentes ao módulo Estudos.

* Rastreador de Horas: Botão "Start/Stop" para contabilizar quantas horas você estudou determinado assunto na semana.

* Revisão: Sistema simples que te lembra de revisar um tópico antigo

### Na integração com o calendário teremos em cada dia:

- Checklist de cada assunto meta para o dia



## Hobbies

### A tela Hobbies deve conter:

* Lista de hobbies que deseja praticar, e em cada um:  
  * Dedicação mínima por semana/dia

* Tracker de Consistência: Um "Heatmap" (igual ao do GitHub) mostrando os dias que você praticou cada hobby no ano.

* Lista de Leitura/Filmes: Um CRUD simples para livros e filmes que pretende consumir.

### Na integração com o calendário teremos em cada dia:

- Checklist com os hábitos cumpridos no dia

## Saúde

### A tela Saúde deve conter:

* Lista de médicos que devem estar em dia, e para cada um:  
  * Data da última consulta e a próxima data indicada para retorno

### Na integração com o calendário teremos em cada dia:

- Consultas futuras recomendadas a se agendar (1 a 2 meses de antecedência)  
- Consultas marcadas

## Autocuidado

### A tela Autocuidado deve conter:

* Checklist de Rotina: (Skin Care, Academia, …)

* Lista de coisas que deseja melhorar em si, e em cada um:  
  * Como melhorar  
  * Dedicação mínima por dia/semana

* Agenda de Procedimentos: Calendário para marcar corte de cabelo, dermato, etc., com lembrete de "Retorno previsto em X meses".

	  
### Na integração com calendário teremos em cada dia:

- Consultas futuras recomendadas a se agendar (1 a 2 meses de antecedência)  
- Consultas marcadas  
- Checklist de cumprimento de objetivos Macro

# Requisitos Técnicos

## Stack

	Será utilizado como base Django + Render + Supabase, para manter a aplicação em nuvem.

* Framework Principal: Django (Gerencia rotas, banco de dados e segurança).  
* API: Django REST Framework (DRF)  
* Banco de Dados: PostgreSQL (Via adaptador psycopg2-binary).  
* Frontend Web (Visual): Django Templates \+ Bootstrap 5\.  
* Servidor de Aplicação: Gunicorn.  
* Gerenciamento de Arquivos Estáticos: Whitenoise

## Paleta de Cores

Opção 1:

* Claro:  
  * .color1 { \#268b9b };  
  * .color2 { \#5aa8b4 };  
  * .color3 { \#8dc5cd };  
  * .color4 { \#c1e2e6 };  
  * .color5 { \#f4ffff };  
* Escuro:  
  * .color1 { \#343838 };  
  * .color2 { \#005f6b };  
  * .color3 { \#008c9e };  
  * .color4 { \#00b4cc };  
  * .color5 { \#00dffc };

  Opção 2:

* Claro:   
  * .color1 { \#2a8b8b };  
  * .color2 { \#75c58e };  
  * .color3 { \#bfff91 };  
  * .color4 { \#dfe9a8 };  
  * .color5 { \#ffd2bf };

