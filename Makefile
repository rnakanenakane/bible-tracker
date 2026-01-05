SHELL := /bin/bash
VENV := .venv
SOURCES_DIR := ./src

# Define o alvo padrão que será executado quando 'make' for chamado sem argumentos.
.DEFAULT_GOAL := help

.PHONY: init lint sec check-deps run clean help

init: $(VENV)/.timestamp ## Cria o ambiente virtual e instala todas as dependências.

$(VENV)/.timestamp: pyproject.toml
	@echo "--> Criando ambiente virtual..."
	test -d $(VENV) || python3 -m venv $(VENV)
	@echo "--> Atualizando pip e setuptools..."
	$(VENV)/bin/pip install --upgrade pip setuptools
	@echo "--> Instalando dependências do projeto e de desenvolvimento..."
	# Instala as dependências do projeto e as de desenvolvimento (definidas como 'dev' no pyproject.toml)
	$(VENV)/bin/pip install ".[dev]"
	touch $(VENV)/.timestamp


lint: init ## Executa formatadores e analisadores de código (black, isort, flake8, mypy).
	@echo "--> Executando black, isort, flake8 e mypy..."
	# As ferramentas lerão suas configurações do pyproject.toml e .flake8
	$(VENV)/bin/black .
	$(VENV)/bin/isort .
	$(VENV)/bin/flake8 $(SOURCES_DIR)
	$(VENV)/bin/mypy $(SOURCES_DIR)
	@echo "--> Verificação concluída."

sec: init ## Executa verificações de segurança no código e nas dependências.
	@echo "--> Executando bandit para análise de segurança do código..."
	$(VENV)/bin/bandit -r $(SOURCES_DIR)
	@echo "--> Executando pip-audit para verificar vulnerabilidades nas dependências..."
	$(VENV)/bin/pip-audit
	@echo "--> Verificação de segurança concluída."

check-deps: init ## Verifica por dependências não utilizadas ou ausentes.
	@echo "--> Verificando dependências não utilizadas ou ausentes..."
	$(VENV)/bin/deptry .
	@echo "--> Verificação de dependências concluída."

run: ## Executa localmente a aplicação
	@echo "--> Iniciando a aplicação..."
	$(VENV)/bin/streamlit run app.py
	@echo "--> Aplicação iniciada."

clean: ## Remove o ambiente virtual e arquivos de cache do projeto.
	@echo "--> Removendo ambiente virtual e arquivos de cache..."
	rm -rf $(VENV)
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .mypy_cache .pytest_cache
	@echo "--> Limpeza concluída."

help: ## Exibe esta mensagem de ajuda com os comandos disponíveis.
	@echo "Comandos disponíveis:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
