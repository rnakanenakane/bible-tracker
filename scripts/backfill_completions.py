import os
import sys

from dotenv import load_dotenv
from supabase import Client, create_client

# Adiciona o diretório raiz ao path para encontrar o módulo 'src'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.repository import DatabaseRepository


def run_backfill():
    """
    Executa um script para preencher retroativamente a tabela tb_livros_concluidos.

    Este script busca todas as combinações únicas de usuário, plano e livro
    da tabela de leituras e dispara a lógica de verificação de conclusão para cada uma.
    """
    # Carrega as variáveis de ambiente de um arquivo .env na raiz do projeto
    # Crie um arquivo .env com SUPABASE_URL e SUPABASE_SERVICE_KEY
    load_dotenv()

    supabase_url = os.getenv("SUPABASE_URL")
    # IMPORTANTE: Use a chave de 'service_role' para ter permissões de escrita/leitura totais
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_key:
        print("Erro: As variáveis de ambiente SUPABASE_URL e SUPABASE_SERVICE_KEY não foram definidas.")
        print("Crie um arquivo .env na raiz do projeto com essas credenciais.")
        return

    print("Conectando ao Supabase...")
    client: Client = create_client(supabase_url, supabase_key)
    repo = DatabaseRepository(client)
    print("Conexão estabelecida.")

    try:
        print("Buscando todas as leituras existentes para análise...")
        response = client.table("tb_leituras").select("usuario_id, plano_id, id_livro").execute()
        if not response.data:
            print("Nenhum registro de leitura encontrado. Nada a fazer.")
            return

        unique_checks = {(r["usuario_id"], r["plano_id"], r["id_livro"]) for r in response.data}
        total_checks = len(unique_checks)
        print(f"Encontradas {total_checks} combinações únicas para verificar.")

        for i, (user_id, plan_id, book_id) in enumerate(unique_checks):
            print(
                f"[{i+1}/{total_checks}] Verificando: Usuário={user_id}, Plano={plan_id}, Livro={book_id}"
            )
            repo._check_and_save_book_completion(user_id, plan_id, book_id)

        print("\nVerificação concluída! A tabela 'tb_livros_concluidos' foi atualizada.")
    except Exception as e:
        print(f"\nOcorreu um erro durante o processo de backfill: {e}")


if __name__ == "__main__":
    run_backfill()
