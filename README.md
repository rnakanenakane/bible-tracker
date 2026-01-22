# ✝️ Bible Tracker: Acompanhamento de Leitura Bíblica

![Streamlit](https://img.shields.io/badge/Feito%20com-Streamlit-red?style=for-the-badge&logo=streamlit)
![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=for-the-badge&logo=python)
![Supabase](https://img.shields.io/badge/Backend-Supabase-green?style=for-the-badge&logo=supabase)

**Bible Tracker** é uma aplicação web moderna e interativa, desenvolvida com Streamlit, para acompanhar o progresso de leitura da Bíblia em comunidade. A ferramenta foi projetada para ser intuitiva, motivadora e promover o engajamento entre os membros, transformando a jornada de leitura em uma experiência compartilhada.

## ✨ Funcionalidades Principais

- **Acompanhamento Pessoal Detalhado:** Marque capítulos como lidos em uma interface limpa e veja seu progresso diário de forma clara.
- **Múltiplos Planos de Leitura:** Suporte para diferentes planos de leitura (ex: cronológico, canônico), carregados dinamicamente do banco de dados.
- **Navegação Inteligente:** O sistema guia o usuário automaticamente para a próxima data com leitura pendente, facilitando a continuidade do estudo.
- **Dashboard Comunitário:** Um painel de controle visual que exibe o progresso de todos os participantes, com gráficos que comparam o avanço de cada um em relação à meta do plano.
- **Página de Conquistas (Awards):**
    - **Insígnias Visuais:** Ganhe selos (imagens) para cada livro da Bíblia concluído.
    - **Progresso Pessoal:** Visualize suas próprias insígnias e seu percentual de progresso na leitura da Bíblia completa.
    - **Galeria da Comunidade:** Veja as conquistas de outros membros, incentivando a todos.
- **Mural de Dúvidas Anônimas:** Um espaço seguro para fazer perguntas sobre as leituras de forma anônima e colaborar respondendo às dúvidas de outros membros.

---

## 🛠️ Arquitetura e Tecnologias

O projeto segue uma arquitetura limpa, separando a lógica da interface (UI), o acesso a dados (Repository) e as configurações.

- **Frontend:** [Streamlit](https://streamlit.io/)
- **Backend & Banco de Dados:** [Supabase](https://supabase.com/) (PostgreSQL)
- **Linguagem:** Python 3.11+
- **Gerenciamento de Dependências:** `pip` e `venv`, com arquivos `pyproject.toml`.
- **Qualidade de Código e CI/CD:**
  - **Automação:** `Makefile` para simplificar tarefas comuns (instalação, linting, execução).
  - **Formatação:** `black` e `isort`.
  - **Análise Estática:** `flake8` e `mypy` para detecção de erros e consistência de tipos.
  - **Segurança:** `bandit` para análise de vulnerabilidades no código e `pip-audit` para as dependências.
  - **Hooks de Pré-commit:** Para garantir a qualidade do código antes de cada commit.

---

## 🚀 Configuração e Execução Local

Siga os passos abaixo para configurar e executar o projeto em seu ambiente.

### 1. Pré-requisitos

- **Python 3.11 ou superior**
- **Make** (padrão em Linux/macOS; no Windows, pode ser usado via WSL, Git Bash ou Chocolatey).

### 2. Clonar o Repositório

```bash
git clone <URL_DO_SEU_REPOSITORIO>
cd bible-tracker
```

### 3. Configurar o Banco de Dados (Supabase)

1.  **Crie um projeto** na plataforma Supabase.
2.  **Schema do Banco:** No painel do seu projeto, vá para a seção **SQL Editor**.
    - Copie e execute o conteúdo do arquivo `scripts/ddl.sql` para criar as tabelas e políticas de segurança (RLS).
    - **Importante:** Além das tabelas, o script cria as funções `handle_book_completion_check` e `count_unique_readings_for_user`, que são essenciais para a aplicação.
3.  **Povoamento dos Dados:** Para que a aplicação funcione, é crucial inserir os dados nas tabelas `tb_usuarios`, `tb_planos`, `tb_livros` e, principalmente, `tb_plano_entradas` (que contém a estrutura dos planos de leitura).

### 4. Configurar as Credenciais

1.  Crie uma pasta chamada `.streamlit` na raiz do projeto.
2.  Dentro dela, crie um arquivo chamado `secrets.toml`.
3.  Adicione suas credenciais do Supabase (encontradas em `Project Settings > API`) neste arquivo:

```toml
# .streamlit/secrets.toml

[supabase]
url = "SUA_URL_DO_PROJETO_SUPABASE"
key = "SUA_CHAVE_ANON_SUPABASE"
```

### 5. Instalar Dependências e Executar

O `Makefile` automatiza todo o processo. Execute os seguintes comandos no seu terminal:

```bash
# 1. Cria o ambiente virtual e instala todas as dependências
make init

# 2. Inicia a aplicação Streamlit
make run
```

A aplicação estará disponível em `http://localhost:8501`.

---

## ⚙️ Comandos Disponíveis (`Makefile`)

O projeto utiliza um `Makefile` para simplificar as tarefas de desenvolvimento.

- `make init`: Cria o ambiente virtual e instala todas as dependências do projeto.
- `make lint`: Executa todas as ferramentas de formatação e análise de código.
- `make sec`: Realiza verificações de segurança no código (`bandit`) e nas dependências (`pip-audit`).
- `make check-deps`: Verifica por dependências não utilizadas ou ausentes (`deptry`).
- `make run`: Inicia a aplicação Streamlit localmente.
- `make clean`: Remove o ambiente virtual e arquivos de cache.
- `make help`: Exibe a lista de todos os comandos disponíveis com suas descrições.

---

## 🗄️ Tarefas de Manutenção

### Atualizando Selos de Conclusão Retroativos

Se a aplicação esteve em uso antes da implementação da funcionalidade de "Selos de Conclusão", a tabela `tb_livros_concluidos` pode não refletir os livros que já foram completados.

Para corrigir isso, existe um script de *backfill* que processa todos os registros de leitura existentes e popula a tabela de conclusões corretamente.

1.  **Crie um arquivo `.env`** na raiz do projeto com as credenciais do Supabase. É **essencial** usar a chave `service_role` para que o script tenha as permissões necessárias.

    ```
    # .env
    SUPABASE_URL="SUA_URL_DO_PROJETO_SUPABASE"
    SUPABASE_SERVICE_KEY="SUA_CHAVE_SERVICE_ROLE_SUPABASE"
    ```

2.  Execute o script diretamente via Python (com o ambiente virtual ativado):

    ```bash
    # Ative o ambiente virtual se não estiver ativo
    # source .venv/bin/activate
    python scripts/backfill_completions.py
    ```

Este processo precisa ser executado apenas uma vez para sincronizar os dados históricos.

---

## 📂 Estrutura do Projeto

```
bible-tracker/
├── .streamlit/
│   └── secrets.toml        # Credenciais (não versionado)
├── media/                  # Imagens dos selos dos livros
├── scripts/
│   ├── ddl.sql             # Schema e funções do banco de dados
│   └── backfill_completions.py # Script para popular dados históricos
├── src/                    # Código fonte da aplicação
│   ├── __init__.py
│   ├── config.py           # Configurações e cliente Supabase
│   ├── models.py           # Modelos de dados (Pydantic)
│   ├── repository.py       # Camada de acesso a dados (interação com DB)
│   ├── ui.py               # Funções de renderização da interface
│   └── utils.py            # Funções utilitárias e constantes
├── .pre-commit-config.yaml # Configuração dos hooks de pré-commit
├── app.py                  # Ponto de entrada da aplicação
├── book_images.yaml        # Mapeamento de livros para imagens
├── Makefile                # Comandos de automação
├── pyproject.toml          # Dependências e configurações do projeto
└── README.md               # Este arquivo
```