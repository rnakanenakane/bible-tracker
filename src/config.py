import pytz
import streamlit as st
from supabase import Client, create_client

FUSO_BR = pytz.timezone("America/Sao_Paulo")


@st.cache_resource
def get_supabase_client() -> Client:
    """
    Cria e retorna um cliente Supabase.
    Usa @st.cache_resource para garantir que a conexão seja criada apenas uma vez.
    """
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Erro ao configurar Supabase. Verifique o secrets.toml. {e}")
        st.stop()


supabase_client = get_supabase_client()
