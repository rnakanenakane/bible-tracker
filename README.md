# ✝️ Rondoninha Church: Acompanhamento de Leitura Bíblica

![Streamlit](https://img.shields.io/badge/Feito%20com-Streamlit-red?style=for-the-badge&logo=streamlit)
![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=for-the-badge&logo=python)
![Supabase](https://img.shields.io/badge/Backend-Supabase-green?style=for-the-badge&logo=supabase)

Uma aplicação web desenvolvida com Streamlit para acompanhar o progresso de leitura da Bíblia, tanto individualmente quanto em comunidade, com base em planos de leitura pré-definidos.

## ✨ Funcionalidades

- **Acompanhamento Pessoal:** Marque capítulos como lidos e veja seu progresso diário.
- **Seleção de Planos:** Escolha entre diferentes planos de leitura disponíveis no banco de dados.
- **Navegação Inteligente:** O sistema direciona automaticamente para a próxima data com leitura pendente.
- **Dashboard Comunitário:** Visualize o progresso de todos os participantes em um gráfico interativo, comparando o avanço de cada um com a meta do plano.
- **Status de Leitura:** Identifique facilmente quem está "Em dia" ou "Atrasado" em relação ao cronograma.

---

## 🛠️ Tecnologias Utilizadas

- **Frontend:** [Streamlit](https://streamlit.io/)
- **Backend & Banco de Dados:** [Supabase](https://supabase.com/) (PostgreSQL)
- **Linguagem:** Python 3.9+
- **Ferramentas de Desenvolvimento:**
  - `make` para automação de tarefas.
  - `venv` para gerenciamento de ambiente virtual.
  - `black`, `isort`, `flake8`, `mypy` para formatação e análise estática de código.
  - `bandit`, `pip-audit` para verificação de segurança.
  - `deptry` para análise de dependências.

---

## 🚀 Configuração e Execução

Siga os passos abaixo para configurar e executar o projeto localmente.

### 1. Pré-requisitos

- **Python 3.9 ou superior**
- **Make** (geralmente já instalado em sistemas Linux/macOS; no Windows, pode ser usado via WSL ou Git Bash).

### 2. Clonar o Repositório

```bash
git clone <URL_DO_SEU_REPOSITORIO>
cd bible-tracker
```

### 3. Configurar o Banco de Dados (Supabase)

1. Crie um novo projeto na plataforma Supabase.
2. No painel do seu projeto, vá para a seção **SQL Editor**.
3. Copie todo o conteúdo do arquivo `scripts/ddl.sql` e execute-o para criar as tabelas necessárias.
4. **Povoamento dos Dados:** Para que a aplicação funcione, é crucial inserir os dados nas tabelas `tb_usuarios`, `tb_planos`, `tb_livros` e, principalmente, `tb_plano_entradas` (que contém a estrutura dos planos de leitura).

### 4. Configurar as Credenciais

1. Crie uma pasta chamada `.streamlit` na raiz do projeto, caso ela não exista.
2. Dentro dela, crie um arquivo chamado `secrets.toml`.
3. Adicione suas credenciais do Supabase (encontradas em `Project Settings > API`) neste arquivo:

```toml
# .streamlit/secrets.toml

[supabase]
url = "SUA_URL_DO_PROJETO_SUPABASE"
key = "SUA_CHAVE_ANON_SUPABASE"
```

### 5. Instalar Dependências e Executar

O `Makefile` automatiza todo o processo de configuração e execução.

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
- `make lint`: Executa formatadores e analisadores de código (`black`, `isort`, `flake8`, `mypy`).
- `make sec`: Realiza verificações de segurança no código (`bandit`) e nas dependências (`pip-audit`).
- `make check-deps`: Verifica por dependências não utilizadas ou ausentes (`deptry`).
- `make run`: Inicia a aplicação Streamlit localmente.
- `make clean`: Remove o ambiente virtual e arquivos de cache.
- `make help`: Exibe a lista de todos os comandos disponíveis.

---

## 📂 Estrutura do Projeto

```
bible-tracker/
├── .streamlit/
│   └── secrets.toml    # Credenciais (não versionado)
├── scripts/
│   └── ddl.sql         # Schema do banco de dados
├── app.py              # Código principal da aplicação Streamlit
├── Makefile            # Comandos de automação
├── pyproject.toml      # Dependências e configurações do projeto
└── README.md           # Este arquivo
```