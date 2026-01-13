# Planejador Anual (Idealização do projeto)
    Futuramente documentação de requisitos formal completa

ESSE É O MEU ANO!

Projeto pessoal que visa o desenvolvimento de uma aplicação web, para facilitar a organização pessoal ao longo do ano, em diversos âmbitos do desenvolvimento pessoal, como Estudos, Trabalho, Finanças, Hobbies, Saúde, e Autocuidados por exemplo.

## Instalação

Após baixar o repositório, cria um arquivo na raiz do proeto, chamado _.env_
Nesse arquivo ficarão suas variáveis de ambiente, e essas informações são secretas. Escreva nesse arquivo as seguintes variáveis:

> DEBUG=True \
> SECRET_KEY='(exemplo-de-chave-secreta-pessoal-do-usuario)' \
> ALLOWED_HOSTS=localhost,127.0.0.1

Agora, em um ambiente que tenha Python 3.12.1+ instalado - **Altamente recomendado o uso de um ambiente virtual python (venv)** -, rode os seguintes comandos de prompt na raiz do projeto:

> pip install -r requirements.txt

> python manage.py makemigrations

> python manage.py migrate

> python manage.py runserver

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

### A tela de Financeiro deve conter:

* Saldo atual

* Entrada e Saída do Mês atual

* Dashboard Interativo: Gráficos (Pizza ou Barra) mostrando gastos por categoria (Lazer, Mercado, Fixos).

* Tabela com todos gastos e receitas do mês atual, sendo fácil de se adicionar ou remover itens.  
  * Campos: Valor, Data, Categoria (Tag), Descrição, Status (Pago/Pendente), Forma de Pagamento.  
  * Adicionar automaticamente gastos e receitas fixas, como para os objetivos macros.

* Gestão de Recorrência: Checkbox "Mensal" que gera automaticamente a fatura do próximo mês.

* Objetivos Macros: Cards com barras de progresso visual para objetivos, bem como o valor atual, objetivo e restante (ex: "Viagem 2026").

* Recurso "E se?": Uma calculadora simples automática que reservará um valor de gasto extra, mostrando quanto sobraria do saldo atual tendo em vista imprevistos.

### Na integração com calendário teremos em cada dia:

- Checklist de pagamentos manuais para o dia

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

