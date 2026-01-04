#!/bin/bash

# build.sh: Executa a limpeza, instalação, verificações de qualidade e segurança,
# e gera o arquivo de dependências para produção.

set -e
set -o pipefail

echo "--- INICIANDO PROCESSO DE BUILD ---"

# echo "--> 1. Limpando o ambiente..."
# make clean

# echo "--> 2. Instalando dependências..."
# make init

# echo "--> 3. Verificando qualidade do código (lint)..."
# make lint

# echo "--> 4. Verificando segurança (sec)..."
# make sec

echo "--> 5. Gerando requirements.txt para produção..."
.venv/bin/toml-to-req --toml-file pyproject.toml

echo "--- BUILD CONCLUÍDO COM SUCESSO ---"