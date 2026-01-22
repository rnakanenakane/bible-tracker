from datetime import datetime
from typing import Optional

import altair as alt
import pandas as pd
import streamlit as st

from src.config import FUSO_BR
from src.models import Usuario
from src.repository import DatabaseRepository
from src.utils import (
    BIBLE_BOOKS_DATA,
    expandir_capitulos,
    get_total_bible_chapters,
    load_book_images_map,
)


def apply_styles():
    """Aplica os estilos CSS customizados na página."""
    st.markdown(
        """
    <style>
        html, body, [class*="css"] {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        .main-header {
            font-size: 2.5rem;
            color: #4A90E2;
            text-align: center;
            font-weight: 700;
            margin-bottom: 1rem;
            padding-bottom: 1rem;
            border-bottom: 2px solid #f0f2f6;
        }
        div[data-testid="stMetric"] {
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            text-align: center;
            transition: transform 0.2s;
        }
        div[data-testid="stMetric"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 8px rgba(0,0,0,0.1);
        }
        @media (prefers-color-scheme: dark) {
            div[data-testid="stMetric"] {
                background-color: #262730;
                border: 1px solid #41444e;
            }
        }
        .stButton button {
            width: 100%;
            border-radius: 8px;
            font-weight: 600;
            border: 1px solid #dcdcdc;
        }
        section[data-testid="stSidebar"] {
            background-color: #f8f9fa;
        }
        h2, h3 { color: #2c3e50; }
        @media (prefers-color-scheme: dark) {
            h2, h3 { color: #fafafa; }
            section[data-testid="stSidebar"] { background-color: #1e1e1e; }
        }
    </style>
    """,
        unsafe_allow_html=True,
    )


def render_login_page(users: list[Usuario]) -> Optional[Usuario]:
    """Renderiza a página de login e gerencia a seleção de usuário.

    Apresenta um selectbox para o usuário escolher seu nome. Após a seleção e
    o clique no botão "Entrar", o objeto Usuario correspondente é retornado
    para ser armazenado na sessão.

    Args:
        users: Uma lista de todos os objetos Usuario cadastrados.

    Returns:
        O objeto Usuario selecionado se o login for bem-sucedido, caso contrário None.
    """
    st.header("Bem-vindo! Selecione seu usuário para continuar.")

    if not users:
        st.error("Nenhum usuário cadastrado no sistema. Por favor, popule o banco de dados.")
        st.stop()

    user_map = {user.nome: user for user in users}
    selected_user_name = st.selectbox(
        "Selecione seu nome", list(user_map.keys()), index=None, placeholder="Selecione seu nome..."
    )

    if st.button("Entrar", type="primary", disabled=(not selected_user_name)):
        if selected_user_name:
            return user_map.get(selected_user_name)
    return None


def render_sidebar(user: Usuario) -> tuple[str, bool]:
    """Renderiza a barra lateral da aplicação.

    A barra lateral contém uma saudação ao usuário, o menu de navegação principal
    e o botão de logout.

    Args:
        user: O objeto Usuario do usuário logado.

    Returns:
        Uma tupla contendo a string da página selecionada e um booleano
        indicando se o botão de logout foi clicado.
    """
    with st.sidebar:
        st.markdown(f"### Olá, {user.nome}!")
        st.divider()
        pagina = st.radio(
            "Navegar",
            ["Minha Leitura", "Progresso Geral", "Awards", "Dúvidas da Comunidade"],
            label_visibility="collapsed",
        )
        st.divider()
        logout_clicked = st.button("Sair")
        st.caption("Rondoninha Church © 2026")
    return pagina, logout_clicked


def _encontrar_proxima_data_nao_lida(df_plano: pd.DataFrame, leituras_usuario: list) -> datetime:
    """Encontra a próxima data de leitura com capítulos pendentes em um plano.

    Compara os capítulos planejados com os capítulos já lidos pelo usuário
    para determinar a primeira data no cronograma que ainda não foi completada.

    Args:
        df_plano: DataFrame do plano de leitura específico.
        leituras_usuario: Lista de objetos Leitura do usuário.

    Returns:
        Um objeto datetime correspondente à próxima data com leitura pendente.
        Retorna a data atual se o plano estiver completo ou vazio.
    """
    if df_plano.empty:
        return datetime.now(FUSO_BR)

    if not leituras_usuario:
        return df_plano["data"].min()

    lidos_set = {(leitura.livro.nome, leitura.capitulo) for leitura in leituras_usuario}
    df_plano_ordenado = df_plano.sort_values(by="data")

    for _, row in df_plano_ordenado.iterrows():
        livro_plano = row["livro"]
        lista_caps = expandir_capitulos(row["capitulos"])

        if not all((livro_plano, cap) in lidos_set for cap in lista_caps):
            return row["data"]

    return datetime.now(FUSO_BR)


def render_reading_page(user: Usuario, repo: DatabaseRepository, plans: dict[str, pd.DataFrame]):
    """Renderiza a página principal 'Minha Leitura'.

    Esta página permite ao usuário selecionar um plano de leitura, navegar
    pelas datas e marcar os capítulos como lidos. A lógica gerencia o estado
    da sessão para lembrar o plano e a data selecionados.

    Args:
        user: O usuário logado.
        repo: A instância do repositório de banco de dados.
        plans: Um dicionário com todos os planos de leitura estruturados.
    """
    st.header("Meu Plano de Leitura")

    if not plans:
        st.warning("Nenhum plano de leitura encontrado.")
        st.stop()

    # Define o plano padrão para o usuário (último ativo)
    if "user_check_plano" not in st.session_state or st.session_state.user_check_plano != user.id:
        ultimo_plano = repo.get_last_active_plan_name(user)
        if ultimo_plano and ultimo_plano in plans:
            st.session_state["plano_selecionado_widget"] = ultimo_plano
        st.session_state["user_check_plano"] = user.id

    lista_planos_keys = sorted(list(plans.keys()))
    default_index = 0
    if (
        "plano_selecionado_widget" in st.session_state
        and st.session_state.plano_selecionado_widget in lista_planos_keys
    ):
        default_index = lista_planos_keys.index(st.session_state.plano_selecionado_widget)

    plano_nome = st.selectbox("📅 Escolha o Plano", lista_planos_keys, index=default_index)
    st.session_state.plano_selecionado_widget = plano_nome
    df_plano = plans[plano_nome]

    if plano_nome != st.session_state.get("plano_anterior"):
        leituras_usuario = repo.get_user_readings(user, plano_nome)
        proxima_data = _encontrar_proxima_data_nao_lida(df_plano, leituras_usuario)
        st.session_state["data_selecionada"] = pd.to_datetime(proxima_data)
        st.session_state["plano_anterior"] = plano_nome
        st.rerun()  # Força o rerun para atualizar a data

    st.markdown("---")
    c_data, c_info = st.columns([1, 3])

    with c_data:
        data_input = st.date_input(
            "Data da Leitura", value=st.session_state.get("data_selecionada", datetime.now(FUSO_BR))
        )
        st.session_state["data_selecionada"] = pd.to_datetime(data_input)

    leitura_do_dia = df_plano[df_plano["data"].dt.date == st.session_state["data_selecionada"].date()]
    leituras_usuario = repo.get_user_readings(user, plano_nome)
    lidos_set = {(leitura.livro.nome, leitura.capitulo) for leitura in leituras_usuario}

    with c_info:
        if leitura_do_dia.empty:
            st.info("😴 Nada programado para esta data.")
        else:
            for _, row in leitura_do_dia.iterrows():
                livro = row["livro"]
                caps_str = str(row["capitulos"])
                lista_caps = expandir_capitulos(caps_str)

                st.markdown(
                    f"### 📖 {livro} <span style='font-size:0.8em; color:gray'>Caps {caps_str}</span>",
                    unsafe_allow_html=True,
                )

                cols = st.columns(10)
                for i, c in enumerate(lista_caps):
                    ja_leu = (livro, c) in lidos_set
                    label = f"{c} ✅" if ja_leu else f"{c}"
                    if cols[i % 10].button(
                        label,
                        key=f"{user.id}_{plano_nome}_{livro}_{c}",
                        disabled=ja_leu,
                        type="primary" if ja_leu else "secondary",
                    ):
                        repo.save_reading(user, plano_nome, livro, c)
                        st.rerun()


def _render_user_seals(books: set[str], book_images_map: dict[str, str]):
    """Helper para renderizar os selos de um usuário em uma grade."""
    seals_per_row = 6  # Menos colunas = imagens maiores
    sorted_books = sorted(
        list(books),
        key=lambda book_name: BIBLE_BOOKS_DATA.get(book_name, {"order": 999})["order"],
    )

    book_chunks = [
        sorted_books[i : i + seals_per_row] for i in range(0, len(sorted_books), seals_per_row)
    ]

    for chunk in book_chunks:
        cols = st.columns(seals_per_row)
        for i, book_name in enumerate(chunk):
            with cols[i]:
                image_path = book_images_map.get(book_name)
                if image_path:
                    st.image(image_path)
                else:
                    # Fallback para o nome do livro se a imagem não for encontrada
                    st.caption(book_name)


def render_awards_page(user: Usuario, repo: DatabaseRepository):
    """Renderiza a página de 'Awards', destacando o usuário logado e a comunidade."""
    st.markdown("# 🏅 Insígnias de Conclusão")

    completed_books = repo.get_completed_books_dashboard()
    book_images_map = load_book_images_map()

    # --- Seção do Usuário Logado ---
    st.markdown("### 🌟 Minhas Insígnias")

    # Adiciona o cálculo e exibição do progresso geral de leitura da Bíblia
    total_bible_chapters = get_total_bible_chapters()
    user_chapters_read = repo.get_user_unique_readings_count(user.id)

    if total_bible_chapters > 0:
        progress_pct = user_chapters_read / total_bible_chapters
        st.metric(
            label="Progresso na Bíblia Completa",
            value=f"{progress_pct:.1%}",
            help=f"Você leu {user_chapters_read} de {total_bible_chapters} capítulos.",
        )
        st.progress(progress_pct)

    my_books = completed_books.get(user.nome)

    if my_books:
        _render_user_seals(my_books, book_images_map)
    else:
        st.info(
            "Você ainda não possui insígnias. Conclua a leitura de um livro para ganhar a sua primeira!"
        )

    st.divider()

    # --- Seção da Comunidade ---
    st.markdown("### 🏆 Insígnias da Comunidade")
    other_users_completed = {name: books for name, books in completed_books.items() if name != user.nome}

    if not other_users_completed:
        st.info("Nenhum outro membro da comunidade concluiu um livro ainda.")
        return

    for other_user_name in sorted(other_users_completed.keys()):
        books = other_users_completed[other_user_name]
        st.markdown(f"**{other_user_name}:**")
        _render_user_seals(books, book_images_map)
        st.markdown("<br>", unsafe_allow_html=True)


def _calculate_dashboard_metrics(
    df_registros: pd.DataFrame, plans: dict[str, pd.DataFrame]
) -> tuple[Optional[dict], Optional[pd.DataFrame]]:
    """Calcula as métricas de progresso para o dashboard da comunidade.

    Processa um DataFrame de registros de leitura para gerar estatísticas agregadas
    (total de leitores, capítulos lidos, etc.) e um DataFrame detalhado com o
    progresso de cada usuário em cada plano.

    Args:
        df_registros: DataFrame com todos os registros de leitura.
        plans: Dicionário com os DataFrames de cada plano para cálculo das metas.

    Returns:
        Uma tupla contendo:
        - Um dicionário com as métricas agregadas.
        - Um DataFrame detalhado com o progresso de cada usuário.
        Retorna (None, None) se não for possível calcular as métricas.
    """
    if df_registros is None or df_registros.empty:
        return None, None

    dados_consolidados = []
    hoje_date = datetime.now(FUSO_BR).date()
    grupos = df_registros.groupby(["Usuario", "Plano"])

    for (usuario, plano_nome), grupo in grupos:
        if plano_nome not in plans:
            continue

        df_plano = plans[plano_nome]
        caps_lidos = len(grupo)
        meta_ate_hoje = df_plano[df_plano["data"].dt.date <= hoje_date]["qtd_capitulos"].sum()
        total_do_plano = df_plano["qtd_capitulos"].sum()

        dados_consolidados.append(
            {
                "Usuario": usuario,
                "Plano": plano_nome,
                "Lidos": caps_lidos,
                "Meta_Hoje": meta_ate_hoje,
                "Total_Plano": total_do_plano,
                "Status": "Em dia" if caps_lidos >= meta_ate_hoje else "Atrasado",
                "Pct_Lido": (caps_lidos / total_do_plano) if total_do_plano > 0 else 0,
                "Pct_Meta": (meta_ate_hoje / total_do_plano) if total_do_plano > 0 else 0,
            }
        )

    if not dados_consolidados:
        return None, None

    df_dash = pd.DataFrame(dados_consolidados)
    metricas = {
        "total_leitores": df_dash["Usuario"].nunique(),
        "total_lidos": df_registros.shape[0],
        "em_dia": df_dash[df_dash["Status"] == "Em dia"].shape[0],
        "atrasados": df_dash[df_dash["Status"] == "Atrasado"].shape[0],
    }
    return metricas, df_dash


def render_dashboard_page(repo: DatabaseRepository, plans: dict[str, pd.DataFrame]):
    """Renderiza a página 'Progresso Geral' (Dashboard da Comunidade).

    Exibe métricas chave sobre o engajamento da comunidade e gráficos de barras
    que mostram o progresso de cada participante em seus respectivos planos de leitura.

    Args:
        repo: A instância do repositório de banco de dados.
        plans: Um dicionário com todos os planos de leitura estruturados.
    """
    st.markdown("### 🏆 Dashboard da Comunidade")

    df_registros = repo.get_all_readings_for_dashboard()
    if df_registros.empty:
        st.info("Ainda não há registros de leitura para exibir os gráficos de progresso.")
        return

    # Calcula e exibe as métricas e gráficos de progresso
    metricas, df_dash = _calculate_dashboard_metrics(df_registros, plans)

    if not metricas or df_dash is None:
        st.info("Não foi possível calcular as métricas de progresso.")
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("👥 Leitores", metricas["total_leitores"])
    c2.metric("📚 Capítulos Lidos", metricas["total_lidos"])
    c3.metric("🎯 Em Dia", metricas["em_dia"])
    c4.metric("⚠️ Atrasados", metricas["atrasados"])
    st.markdown("<br>", unsafe_allow_html=True)

    for plano in sorted(df_dash["Plano"].unique()):
        with st.container():
            st.write(f"**Plano: {plano}**")
            df_filtro = df_dash[df_dash["Plano"] == plano].copy()
            base = alt.Chart(df_filtro).encode(y=alt.Y("Usuario", title=None, sort="-x"))
            barra = base.mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5).encode(
                x=alt.X(
                    "Pct_Lido",
                    axis=alt.Axis(format="%", title="Progresso"),
                    scale=alt.Scale(domain=[0, 1]),
                ),
                color=alt.Color(
                    "Status",
                    scale=alt.Scale(domain=["Em dia", "Atrasado"], range=["#2ecc71", "#e74c3c"]),
                    legend=None,
                ),
                tooltip=["Usuario", "Lidos", "Status"],
            )
            meta = base.mark_tick(color="black", thickness=3, height=20).encode(
                x="Pct_Meta", tooltip=[alt.Tooltip("Pct_Meta", format=".1%", title="Meta Esperada")]
            )
            texto = base.mark_text(align="left", dx=5, color="black").encode(
                x="Pct_Lido", text=alt.Text("Pct_Lido", format=".0%")
            )
            altura = max(120, len(df_filtro) * 60)
            st.altair_chart((barra + meta + texto).properties(height=altura, width="container"))
            st.divider()

    with st.expander("📂 Ver Tabela Completa"):
        st.dataframe(
            df_dash[["Usuario", "Plano", "Lidos", "Meta_Hoje", "Status"]],
            hide_index=True,
            width="stretch",
        )


def render_qa_page(user: Usuario, repo: DatabaseRepository):
    """Renderiza a página 'Dúvidas da Comunidade'.

    Permite que usuários enviem perguntas anonimamente e respondam às perguntas
    de outros membros da comunidade.

    Args:
        user: O usuário logado (usado para atribuir autoria às respostas).
        repo: A instância do repositório de banco de dados.
    """
    st.markdown("### 💬 Mural de Dúvidas e Respostas")
    st.info("Faça uma pergunta anônima para a comunidade ou ajude a responder as dúvidas existentes.")

    with st.expander("🙋 Faça uma pergunta anônima"):
        with st.form("form_pergunta_geral", clear_on_submit=True):
            texto_pergunta = st.text_area(
                "Qual sua dúvida?", height=100, placeholder="Sua pergunta será postada anonimamente."
            )
            if st.form_submit_button("Enviar Pergunta") and texto_pergunta:
                repo.save_question(texto_pergunta)
                repo.get_all_questions_with_answers.clear()
                st.rerun()

    st.markdown("---")
    st.markdown("### Mural")

    perguntas = repo.get_all_questions_with_answers()
    if not perguntas:
        st.success("Nenhuma dúvida no mural por enquanto. Seja o primeiro a perguntar!")
        return

    perguntas.sort(key=lambda p: len(p.respostas) > 0)

    for p in perguntas:
        indicator = "✅" if p.respostas else "❔"
        expander_title = f"{indicator} **Pergunta**: {p.pergunta_texto[:75]}..."

        with st.expander(expander_title):
            st.markdown("**Perguntado por:** `Anônimo`")
            st.markdown("---")
            st.markdown("##### Pergunta Completa:")
            st.info(p.pergunta_texto)
            st.markdown("---")
            st.markdown("##### Respostas:")

            if not p.respostas:
                st.write("Ainda não há respostas. Seja o primeiro a ajudar!")
            else:
                for r in p.respostas:
                    with st.container(border=True):
                        st.markdown(f"**`{r.autor.nome}` respondeu:**")
                        st.write(r.resposta_texto)

            with st.form(key=f"form_resposta_{p.id}", clear_on_submit=True):
                texto_resposta = st.text_area("Sua resposta:", height=120, key=f"ta_{p.id}")
                if st.form_submit_button("Enviar Resposta") and texto_resposta:
                    repo.save_answer(p.id, user, texto_resposta)
                    repo.get_all_questions_with_answers.clear()
                    st.rerun()
