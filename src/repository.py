import logging
from datetime import date
from typing import Any, Dict, Optional

import pandas as pd
import streamlit as st
from postgrest import CountMethod
from supabase import Client

from src.models import Leitura, Pergunta, Usuario
from src.utils import expandir_capitulos

logger = logging.getLogger(__name__)


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
            logger.error(f"Erro ao carregar lista de usuários: {e}", exc_info=True)
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
                plano = response.data.get("plano")
                if isinstance(plano, dict):
                    return plano.get("nome")
        except Exception as e:
            logger.warning(f"Não foi possível buscar o último plano ativo para {user.nome}: {e}")
        return None

    @st.cache_data(ttl=300)
    def get_all_plans_structured(_self) -> dict[str, pd.DataFrame]:
        """Carrega e estrutura todos os planos de leitura do banco de dados.

        Este método busca todas as entradas da tabela `tb_plano_entradas`, processa
        os dados e os agrupa em um dicionário. Cada chave do dicionário é o nome
        de um plano, e o valor é um DataFrame do pandas contendo a estrutura
        completa daquele plano, com colunas como 'data', 'livro', 'capitulos',
        'livro_id', e 'qtd_capitulos'.

        O método é cacheado pelo Streamlit para otimizar o desempenho, evitando
        consultas repetidas ao banco de dados.

        Returns:
            Um dicionário de DataFrames, onde cada DataFrame representa um plano de leitura.
            Retorna um dicionário vazio se nenhum plano for encontrado ou em caso de erro.
        """
        try:
            response = (
                _self._client.table("tb_plano_entradas")
                .select("data_leitura, capitulos, plano:tb_planos(id, nome), livro:tb_livros(id, nome)")
                .execute()
            )

            df_completo = pd.DataFrame(response.data)
            if df_completo.empty:
                return {}

            df_completo["nome_plano"] = df_completo["plano"].apply(lambda p: p["nome"] if p else None)
            df_completo["plano_id"] = df_completo["plano"].apply(lambda p: p["id"] if p else None)
            # Correção: Extrair o ID ANTES de sobrescrever a coluna 'livro' com o nome.
            df_completo["livro_id"] = df_completo["livro"].apply(
                lambda livro_obj: livro_obj["id"] if livro_obj else None
            )
            df_completo["livro"] = df_completo["livro"].apply(
                lambda livro_obj: livro_obj["nome"] if livro_obj else None
            )
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
            logger.error(f"Erro ao carregar planos do banco de dados: {e}", exc_info=True)
            st.error(f"Erro ao carregar planos do banco de dados: {e}")
            return {}

    @st.cache_data(ttl=60)
    def get_user_readings(_self, user: Usuario, plan_id: int) -> list[Leitura]:
        """Carrega o histórico de capítulos lidos por um usuário em um plano específico.

        Args:
            user: O usuário cujas leituras serão buscadas.
            plan_id: O ID do plano de leitura a ser filtrado.

        Returns:
            Uma lista de objetos Leitura representando os capítulos lidos.
        """
        try:
            response = (
                _self._client.table("tb_leituras")
                .select("capitulo, created_at, data_leitura_plano, livro:tb_livros(id, nome)")
                .eq("usuario_id", user.id)
                .eq("plano_id", plan_id)
                .execute()
            )
            if not response.data:
                return []
            return [Leitura(**data) for data in response.data if isinstance(data, dict)]
        except Exception as e:
            logger.warning(
                f"AVISO: Não foi possível carregar leituras para {user.nome} no plano ID {plan_id}: {e}"
            )
            return []

    def save_reading(
        self, user: Usuario, plan_id: int, book_id: int, chapter: int, reading_date: date
    ) -> bool:
        """Salva um novo registro de leitura para um usuário.

        Após salvar, invoca a verificação de conclusão do livro.

        Args:
            user: O usuário que realizou a leitura.
            plan_id: O ID do plano de leitura associado.
            book_id: O ID do livro lido.
            chapter: O número do capítulo lido.
            reading_date: A data para a qual a leitura foi planejada.

        Returns:
            True se o livro foi recém-concluído, False caso contrário.
        """
        try:
            insert_data: Dict[str, Any] = {
                "usuario_id": user.id,
                "plano_id": plan_id,
                "id_livro": book_id,
                "capitulo": chapter,
                "data_leitura_plano": str(reading_date),
            }

            response = (
                self._client.table("tb_leituras")
                .upsert(
                    insert_data,
                    count=CountMethod.exact,
                    on_conflict="usuario_id, plano_id, id_livro, capitulo, data_leitura_plano",
                    ignore_duplicates=True,
                )
                .execute()
            )

            # Se a contagem de linhas inseridas for > 0, a leitura era nova.
            if response.count is not None and response.count > 0:
                # Invalida o cache das leituras do usuário para forçar a recarga dos dados.
                self.get_user_readings.clear()
                return self._check_and_save_book_completion(user.id, plan_id, book_id)

        except Exception as e:
            logger.error(f"Erro ao salvar leitura: {e}", exc_info=True)
            st.error(f"Erro ao salvar leitura: {e}")

        return False

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
            # O erro é logado, mas não interrompe o usuário
            logger.warning(f"Erro ao verificar conclusão do livro via RPC: {e}")
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
            logger.error(f"Erro ao salvar pergunta: {e}", exc_info=True)
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
            logger.error(f"Erro ao salvar resposta: {e}", exc_info=True)
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
            response = (
                _self._client.table("tb_perguntas")
                .select("*, respostas:tb_respostas(*, autor:tb_usuarios(id, nome))")
                .order("created_at", desc=True)
                .order("created_at", foreign_table="tb_respostas", desc=False)
                .execute()
            )

            if not response.data:
                return []

            perguntas = [Pergunta(**p_data) for p_data in response.data if isinstance(p_data, dict)]
            return perguntas

        except Exception as e:
            logger.error(f"Erro ao carregar o mural de dúvidas: {e}", exc_info=True)
            st.error("Não foi possível carregar o mural de dúvidas. Tente recarregar a página.")
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
            # Não mostra erro na tela, apenas no log, para não poluir a UI de 'Awards'
            logger.warning(f"Não foi possível contar as leituras únicas do usuário {user_id}: {e}")
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
            logger.warning(f"Não foi possível carregar os selos de conclusão: {e}")
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
            logger.warning(f"Não foi possível carregar os registros para o dashboard: {e}")
            st.warning(f"Não foi possível carregar os registros para o dashboard: {e}")
            return pd.DataFrame()

    @st.cache_data(ttl=3600)
    def get_total_bible_chapters(_self) -> int:
        """Calcula o número total de capítulos na Bíblia a partir do banco de dados.

        Returns:
            O número total de capítulos em todos os livros.
        """
        try:
            # Usamos a função de agregação 'sum' do PostgREST
            response = (
                _self._client.table("tb_livros").select("chapters", count=CountMethod.exact).execute()
            )
            if response.data:
                return sum(
                    item["chapters"]
                    for item in response.data
                    if isinstance(item, dict) and "chapters" in item and item["chapters"] is not None
                )
        except Exception as e:
            logger.warning(f"Não foi possível calcular o total de capítulos da Bíblia: {e}")
        return 0

    @st.cache_data(ttl=3600)
    def get_book_order_map(_self) -> dict[str, int]:
        """Cria um mapa de nome do livro para sua ordem canônica.

        Returns:
            Um dicionário mapeando o nome de cada livro para seu número de ordem.
        """
        try:
            response = _self._client.table("tb_livros").select("nome, ordem").execute()
            if response.data:
                return {
                    item["nome"]: item["ordem"]
                    for item in response.data
                    if isinstance(item, dict)
                    and "nome" in item
                    and "ordem" in item
                    and item["ordem"] is not None
                }
        except Exception as e:
            logger.warning(f"Não foi possível carregar o mapa de ordem dos livros: {e}")
        return {}

    @st.cache_data(ttl=3600)
    def get_book_images_map(_self) -> dict[str, str]:
        """Cria um mapa de nome do livro para o caminho da sua imagem a partir do banco de dados.

        Returns:
            Um dicionário mapeando o nome de cada livro para o caminho da imagem.
        """
        try:
            response = _self._client.table("tb_livros").select("nome, image_path").execute()
            if response.data:
                return {
                    item["nome"]: item["image_path"]
                    for item in response.data
                    if isinstance(item, dict)
                    and "nome" in item
                    and "image_path" in item
                    and item["image_path"] is not None
                }
        except Exception as e:
            logger.warning(f"Não foi possível carregar o mapa de imagens dos livros: {e}")
        return {}
