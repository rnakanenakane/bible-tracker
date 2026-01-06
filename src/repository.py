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
        self._client = client

    def get_all_users(self) -> list[Usuario]:
        """Carrega a lista de todos os usuários."""
        try:
            response = self._client.table("tb_usuarios").select("id, nome").order("nome").execute()
            if not response.data:
                return []
            return [Usuario(**user_data) for user_data in response.data if isinstance(user_data, dict)]
        except Exception as e:
            st.error(f"Erro ao carregar lista de usuários: {e}")
            return []

    def get_last_active_plan_name(self, user: Usuario) -> Optional[str]:
        """Busca o nome do último plano ativo para um usuário."""
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
        """
        Carrega e estrutura todos os planos de leitura em um dicionário de DataFrames.
        O _self é usado para que o Streamlit possa cachear o método de instância.
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
        """Carrega o histórico de leitura de um usuário para um plano específico."""
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

    def save_reading(self, user: Usuario, plan_name: str, book_name: str, chapter: int) -> None:
        """Salva um novo registro de leitura, verificando antes se ele já não existe."""
        try:
            plano_resp = (
                self._client.table("tb_planos").select("id").eq("nome", plan_name).single().execute()
            )
            if not plano_resp.data or not isinstance(plano_resp.data, dict):
                st.error(f"Plano '{plan_name}' não encontrado.")
                return
            plano_id = plano_resp.data["id"]

            livro_resp = (
                self._client.table("tb_livros").select("id").eq("nome", book_name).single().execute()
            )
            if not livro_resp.data or not isinstance(livro_resp.data, dict):
                st.error(f"Livro '{book_name}' não encontrado.")
                return
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
        except Exception as e:
            st.error(f"Erro ao salvar leitura: {e}")

    def save_question(self, text: str) -> None:
        """Salva uma nova pergunta anônima."""
        try:
            self._client.table("tb_perguntas").insert({"pergunta_texto": text}).execute()
            st.toast("Pergunta enviada!", icon="✅")
        except Exception as e:
            st.error(f"Erro ao salvar pergunta: {e}")

    def save_answer(self, question_id: int, user: Usuario, text: str) -> None:
        """Salva uma nova resposta para uma pergunta."""
        try:
            self._client.table("tb_respostas").insert(
                {"pergunta_id": question_id, "usuario_id": user.id, "resposta_texto": text}
            ).execute()
            st.toast("Resposta enviada!", icon="💬")
        except Exception as e:
            st.error(f"Erro ao salvar resposta: {e}")

    @st.cache_data(ttl=60)
    def get_all_questions_with_answers(_self) -> list[Pergunta]:
        """Carrega todas as perguntas e suas respectivas respostas."""
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

    def get_all_readings_for_dashboard(self) -> pd.DataFrame:
        """Busca todas as leituras para o cálculo das métricas do dashboard."""
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
