import streamlit as st

from src.config import supabase_client
from src.models import Usuario
from src.repository import DatabaseRepository
from src.ui import (
    apply_styles,
    render_dashboard_page,
    render_login_page,
    render_qa_page,
    render_reading_page,
    render_sidebar,
)


def main():
    """Função principal que orquestra a aplicação Streamlit."""
    st.set_page_config(page_title="Rondoninha Church | Leitura", page_icon="✝️", layout="wide")
    apply_styles()
    st.markdown(
        '<div class="main-header">✝️ Rondoninha Church: Leitura Bíblica</div>',
        unsafe_allow_html=True,
    )

    repo = DatabaseRepository(supabase_client)

    if "logged_in_user" not in st.session_state:
        # --- PÁGINA DE LOGIN ---
        all_users = repo.get_all_users()
        user_to_login = render_login_page(all_users)
        if user_to_login:
            st.session_state["logged_in_user"] = user_to_login
            # Limpa estados antigos para garantir uma sessão limpa
            for key in ["data_selecionada", "plano_anterior", "user_check_plano"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    else:
        # --- APLICAÇÃO PRINCIPAL (APÓS LOGIN) ---
        current_user: Usuario = st.session_state["logged_in_user"]

        page, logout_clicked = render_sidebar(current_user)
        if logout_clicked:
            # Limpa toda a sessão para um logout completo
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

        # Carrega dados necessários para as páginas
        # Usando o método cacheado do repositório
        all_plans = repo.get_all_plans_structured()

        if page == "Minha Leitura":
            render_reading_page(current_user, repo, all_plans)
        elif page == "Progresso Geral":
            render_dashboard_page(repo, all_plans)
        elif page == "Dúvidas da Comunidade":
            render_qa_page(current_user, repo)


if __name__ == "__main__":
    main()
