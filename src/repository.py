from typing import Optional

import pandas as pd
import streamlit as st
from postgrest import CountMethod
from supabase import Client

from src.models import Leitura, Pergunta, Resposta, Usuario
from src.utils import expandir_capitulos


class DatabaseRepository:
    """
    Classe repositório para encapsular todas as interações com o banco de dados Supabase.
    """

    def __init__(self, client: Client):
        """Inicializa o repositório com o cliente Supabase.

        Args:
            client: O cliente Supabase para interagir com o banco de dados.
        """
        self._client: Client = client

    def get_all_users(self) -> list[Usuario]:
        """Carrega a lista de todos os usuários ordenados por nome.

        Returns:
            Uma lista de objetos Usuario.
        """
        try:
            response = self._client.table("tb_usuarios").select("id, nome").order("nome").execute()
            if not response.data:
                return []
            return [Usuario(**user_data) for user_data in response.data if isinstance(user_data, dict)]
        except Exception as e:
            st.error(f"Erro ao carregar lista de usuários: {e}")
            return []

    def get_last_active_plan_name(self, user: Usuario) -> Optional[str]:
        """Busca o nome do último plano de leitura ativo para um usuário.

        Isso é determinado pelo registro de leitura mais recente do usuário.

        Args:
            user: O objeto Usuario para o qual buscar o plano.

        Returns:
            O nome do último plano ativo, ou None se nenhum for encontrado.
        """
        try:
            response = (
                self._client.table("tb_leituras")
                .select("plano:tb_planos(nome)")
                .eq("usuario_id", user.id)
                .order("created_at", desc=True)
                .limit(1)
                .single()
                .execute()
            )
            if response.data and isinstance(response.data, dict):
                plano_data = response.data.get("plano")
                if isinstance(plano_data, dict):
                    nome = plano_data.get("nome")
                    if isinstance(nome, str):
                        return nome
        except Exception as e:
            print(f"AVISO: Não foi possível buscar o último plano ativo para {user.nome}: {e}")
        return None

    @st.cache_data(ttl=300)
    def get_all_plans_structured(_self) -> dict[str, pd.DataFrame]:
        """Carrega e estrutura todos os planos de leitura do banco de dados.

        Os dados são carregados da tabela 'tb_plano_entradas' e processados em
        um dicionário onde cada chave é o nome de um plano e o valor é um
        DataFrame do pandas contendo a estrutura desse plano.

        O método é cacheado pelo Streamlit para otimizar o desempenho.

        Returns:
            Um dicionário de DataFrames, onde cada DataFrame representa um plano de leitura.
        """
        try:
            response = (
                _self._client.table("tb_plano_entradas")
                .select("data_leitura, capitulos, plano:tb_planos(nome), livro:tb_livros(nome)")
                .execute()
            )

            df_completo = pd.DataFrame(response.data)
            if df_completo.empty:
                return {}

            df_completo["nome_plano"] = df_completo["plano"].apply(lambda x: x["nome"])
            df_completo["livro"] = df_completo["livro"].apply(lambda x: x["nome"])
            df_completo = df_completo.rename(columns={"data_leitura": "data"})
            df_completo["data"] = pd.to_datetime(df_completo["data"])

            todos_planos = {}
            for nome in df_completo["nome_plano"].unique():
                df_filtrado = df_completo[df_completo["nome_plano"] == nome].copy()
                df_filtrado = df_filtrado.sort_values(by="data")
                df_filtrado["qtd_capitulos"] = df_filtrado["capitulos"].apply(
                    lambda x: len(expandir_capitulos(x))
                )
                todos_planos[nome] = df_filtrado
            return todos_planos
        except Exception as e:
            st.error(f"Erro ao carregar planos do banco de dados: {e}")
            return {}

    def get_user_readings(self, user: Usuario, plan_name: str) -> list[Leitura]:
        """Carrega o histórico de capítulos lidos por um usuário em um plano específico.

        Args:
            user: O usuário cujas leituras serão buscadas.
            plan_name: O nome do plano de leitura a ser filtrado.

        Returns:
            Uma lista de objetos Leitura representando os capítulos lidos.
        """
        try:
            plano_resp = (
                self._client.table("tb_planos").select("id").eq("nome", plan_name).single().execute()
            )
            if not plano_resp.data or not isinstance(plano_resp.data, dict):
                return []
            plano_id = plano_resp.data["id"]

            response = (
                self._client.table("tb_leituras")
                .select("capitulo, created_at, livro:tb_livros(id, nome)")
                .eq("usuario_id", user.id)
                .eq("plano_id", plano_id)
                .execute()
            )
            if not response.data:
                return []
            return [Leitura(**data) for data in response.data if isinstance(data, dict)]
        except Exception as e:
            print(
                f"AVISO: Não foi possível carregar leituras para {user.nome} no plano {plan_name}: {e}"
            )
            return []

    def save_reading(self, user: Usuario, plan_name: str, book_name: str, chapter: int) -> bool:
        """Salva um novo registro de leitura para um usuário.

        Antes de salvar, verifica se o registro já existe para evitar duplicatas.
        Após salvar, invoca a verificação de conclusão do livro.

        Args:
            user: O usuário que realizou a leitura.
            plan_name: O nome do plano de leitura associado.
            book_name: O nome do livro lido.
            chapter: O número do capítulo lido.

        Returns:
            True se o livro foi recém-concluído, False caso contrário.
        """
        book_completed = False
        try:
            plano_resp = (
                self._client.table("tb_planos").select("id").eq("nome", plan_name).single().execute()
            )
            if not plano_resp.data or not isinstance(plano_resp.data, dict):
                st.error(f"Plano '{plan_name}' não encontrado.")
                return book_completed
            plano_id = plano_resp.data["id"]

            livro_resp = (
                self._client.table("tb_livros").select("id").eq("nome", book_name).single().execute()
            )
            if not livro_resp.data or not isinstance(livro_resp.data, dict):
                st.error(f"Livro '{book_name}' não encontrado.")
                return book_completed
            livro_id = livro_resp.data["id"]

            check_resp = (
                self._client.table("tb_leituras")
                .select("id", count=CountMethod.exact)
                .eq("usuario_id", user.id)
                .eq("plano_id", plano_id)
                .eq("id_livro", livro_id)
                .eq("capitulo", chapter)
                .execute()
            )

            if check_resp.count == 0:
                self._client.table("tb_leituras").insert(
                    {
                        "usuario_id": user.id,
                        "plano_id": plano_id,
                        "id_livro": livro_id,
                        "capitulo": chapter,
                    }
                ).execute()
                # Após salvar, verifica se o livro foi concluído.
                book_completed = self._check_and_save_book_completion(user.id, plano_id, livro_id)
        except Exception as e:
            st.error(f"Erro ao salvar leitura: {e}")
        return book_completed

    def _check_and_save_book_completion(self, usuario_id: int, plano_id: int, livro_id: int) -> bool:
        """
        Verifica se um livro foi concluído e salva o registro de conclusão.

        Este método chama a função de banco de dados (RPC) 'handle_book_completion_check'.
        A função de banco de dados contém a lógica para verificar se todos os capítulos
        de um livro em um plano foram lidos pelo usuário e, em caso afirmativo,
        insere um registro na tabela 'tb_livros_concluidos'.

        A RPC é executada com privilégios elevados (SECURITY DEFINER) para contornar
        as políticas de segurança de linha (RLS) na tabela de conclusões.

        Args:
            usuario_id: O ID do usuário.
            plano_id: O ID do plano de leitura.
            livro_id: O ID do livro a ser verificado.

        Returns:
            True se o livro foi recém-concluído, False caso contrário.
        """
        try:
            response = self._client.rpc(
                "handle_book_completion_check",
                {"p_usuario_id": usuario_id, "p_plano_id": plano_id, "p_livro_id": livro_id},
            ).execute()
            if isinstance(response.data, bool):
                return response.data
        except Exception as e:
            # O erro é logado no console, mas não interrompe o usuário
            print(f"AVISO: Erro ao verificar conclusão do livro via RPC: {e}")
        return False

    def save_question(self, text: str) -> None:
        """Salva uma nova pergunta anônima no mural de dúvidas.

        Args:
            text: O texto da pergunta a ser salva.
        """
        try:
            self._client.table("tb_perguntas").insert({"pergunta_texto": text}).execute()
            st.toast("Pergunta enviada!", icon="✅")
        except Exception as e:
            st.error(f"Erro ao salvar pergunta: {e}")

    def save_answer(self, question_id: int, user: Usuario, text: str) -> None:
        """Salva uma nova resposta para uma pergunta existente no mural.

        Args:
            question_id: O ID da pergunta que está sendo respondida.
            user: O usuário que está enviando a resposta.
            text: O texto da resposta.
        """
        try:
            self._client.table("tb_respostas").insert(
                {"pergunta_id": question_id, "usuario_id": user.id, "resposta_texto": text}
            ).execute()
            st.toast("Resposta enviada!", icon="💬")
        except Exception as e:
            st.error(f"Erro ao salvar resposta: {e}")

    @st.cache_data(ttl=60)
    def get_all_questions_with_answers(_self) -> list[Pergunta]:
        """Carrega todas as perguntas e suas respectivas respostas do mural.

        As perguntas são retornadas com uma lista aninhada de suas respostas.
        O método é cacheado pelo Streamlit.

        Returns:
            Uma lista de objetos Pergunta, cada um contendo suas respostas.
        """
        try:
            perguntas_resp = (
                _self._client.table("tb_perguntas").select("*").order("created_at", desc=True).execute()
            )
            if not perguntas_resp.data:
                return []

            perguntas_dict = {
                p_data["id"]: Pergunta(**p_data)
                for p_data in perguntas_resp.data
                if isinstance(p_data, dict) and "id" in p_data
            }
            ids_perguntas = list(perguntas_dict.keys())

            respostas_resp = (
                _self._client.table("tb_respostas")
                .select("*, autor:tb_usuarios(id, nome)")
                .in_("pergunta_id", ids_perguntas)
                .order("created_at")
                .execute()
            )

            if not respostas_resp.data:
                return list(perguntas_dict.values())

            for r_data in respostas_resp.data:
                if not isinstance(r_data, dict):
                    continue
                pergunta_id = r_data.get("pergunta_id")
                if pergunta_id in perguntas_dict:
                    perguntas_dict[pergunta_id].respostas.append(Resposta(**r_data))

            return list(perguntas_dict.values())
        except Exception as e:
            st.error(f"Erro ao carregar o mural de dúvidas: {e}")
            return []

    def get_user_unique_readings_count(self, user_id: int) -> int:
        """
        Conta o número de capítulos únicos lidos por um usuário em todos os planos.

        Este método chama a função de banco de dados (RPC) 'count_unique_readings_for_user'
        para realizar a contagem de forma eficiente no lado do servidor.

        Args:
            user_id: O ID do usuário a ser consultado.

        Returns:
            O número total de capítulos únicos lidos pelo usuário.
        """
        try:
            response = self._client.rpc(
                "count_unique_readings_for_user",
                {"p_usuario_id": user_id},
            ).execute()
            if isinstance(response.data, int):
                return response.data
            return 0
        except Exception as e:
            # Não mostra erro na tela, apenas no log, para não poluir a UI de 'Awards'.
            print(f"AVISO: Não foi possível contar as leituras únicas do usuário: {e}")
            return 0

    @st.cache_data(ttl=60)
    def get_completed_books_dashboard(_self) -> dict[str, set[str]]:
        """Busca os livros concluídos por todos os usuários.

        Os dados são carregados da tabela 'tb_livros_concluidos' e estruturados
        em um dicionário para fácil acesso na página de 'Awards'.
        O método é cacheado pelo Streamlit.

        Returns:
            Um dicionário onde as chaves são nomes de usuários e os valores são
            conjuntos (set) com os nomes dos livros concluídos.
        """
        try:
            response = (
                _self._client.table("tb_livros_concluidos")
                .select("usuario:tb_usuarios(nome), livro:tb_livros(nome)")
                .execute()
            )

            if not response.data:
                return {}

            completed_books: dict[str, set[str]] = {}
            for row in response.data:
                if not isinstance(row, dict):
                    continue

                user_info = row.get("usuario")
                book_info = row.get("livro")
                if isinstance(user_info, dict) and isinstance(book_info, dict):
                    user_name = user_info.get("nome")
                    book_name = book_info.get("nome")
                    if isinstance(user_name, str) and isinstance(book_name, str):
                        completed_books.setdefault(user_name, set()).add(book_name)
            return completed_books
        except Exception as e:
            st.warning(f"Não foi possível carregar os selos de conclusão: {e}")
            return {}

    def get_all_readings_for_dashboard(self) -> pd.DataFrame:
        """Busca todos os registros de leitura para o dashboard de progresso geral.

        Retorna um DataFrame contendo o nome do usuário e o plano para cada
        capítulo lido, que será usado para calcular as métricas do dashboard.

        Returns:
            Um DataFrame do pandas com as colunas 'Usuario' e 'Plano'.
        """
        try:
            response = (
                self._client.table("tb_leituras")
                .select("usuario:tb_usuarios(nome), plano:tb_planos(nome)")
                .execute()
            )
            df = pd.DataFrame(response.data)
            if df.empty:
                return df

            df["Usuario"] = df["usuario"].apply(lambda x: x["nome"] if x else None)
            df["Plano"] = df["plano"].apply(lambda x: x["nome"] if x else None)
            return df[["Usuario", "Plano"]]
        except Exception as e:
            st.warning(f"Não foi possível carregar os registros para o dashboard: {e}")
            return pd.DataFrame()
