from datetime import datetime

import altair as alt
import pandas as pd
import pytz
import streamlit as st
from supabase import Client, create_client

# --- 1. CONFIGURAÇÃO DA PÁGINA E CSS ---
st.set_page_config(page_title="Rondoninha Church | Leitura", page_icon="✝️", layout="wide")

# Estilos CSS Personalizados
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

# --- 2. CONFIGURAÇÕES GERAIS ---
FUSO_BR = pytz.timezone("America/Sao_Paulo")

st.markdown(
    '<div class="main-header">✝️ Rondoninha Church: Leitura Bíblica</div>',
    unsafe_allow_html=True,
)

# Conexão com Supabase
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error(f"Erro ao configurar Supabase. Verifique o secrets.toml. {e}")
    st.stop()

# --- 3. FUNÇÕES AUXILIARES ---

def expandir_capitulos(str_caps):
    str_caps = str(str_caps).strip()
    if "-" in str_caps:
        try:
            inicio, fim = map(int, str_caps.split("-"))
            return list(range(inicio, fim + 1))
        except:
            return []
    else:
        try:
            return [int(str_caps)]
        except:
            return []


def encontrar_proxima_data_nao_lida(df_plano, df_lidos):
    if df_plano.empty:
        return datetime.now(FUSO_BR)

    if df_lidos.empty:
        return df_plano["data"].min()

    lidos_set = set(zip(df_lidos["Livro"], df_lidos["Capitulo"]))
    df_plano_ordenado = df_plano.sort_values(by="data")

    for _, row in df_plano_ordenado.iterrows():
        livro_plano = row["livro"]
        lista_caps = expandir_capitulos(row["capitulos"])

        todas_lidas_hoje = True
        for cap in lista_caps:
            if (livro_plano, cap) not in lidos_set:
                todas_lidas_hoje = False
                break

        if not todas_lidas_hoje:
            return row["data"]

    return datetime.now(FUSO_BR)


def buscar_ultimo_plano_ativo(usuario):
    """Busca o último plano usado por um usuário consultando as novas tabelas."""
    try:
        # 1. Obter o ID do usuário a partir do nome
        user_resp = supabase.table("tb_usuarios").select("id").eq("nome", usuario).single().execute()
        if not user_resp.data:
            return None
        user_id = user_resp.data["id"]

        # 2. Buscar a última leitura desse usuário e obter o nome do plano associado
        response = (
            supabase.table("tb_leituras")
            .select("plano:tb_planos(nome)")
            .eq("usuario_id", user_id)
            .order("created_at", desc=True)
            .limit(1)
            .single()
            .execute()
        )

        if response.data and response.data.get("plano"):
            return response.data["plano"]["nome"]
    except Exception as e:
        print(f"AVISO: Não foi possível buscar o último plano ativo para {usuario}: {e}")
    return None


@st.cache_data(ttl=300)
def carregar_planos():
    """Carrega todos os planos de leitura e seus detalhes das novas tabelas."""
    try:
        # Usamos a sintaxe de join do Supabase para buscar dados de tabelas relacionadas
        response = supabase.table("tb_plano_entradas").select(
            "data_leitura, capitulos, plano:tb_planos(nome), livro:tb_livros(nome)"
        ).execute()

        df_completo = pd.DataFrame(response.data)

        if df_completo.empty:
            st.warning("Nenhum plano encontrado no banco de dados.")
            return {}

        # Processar os dados aninhados retornados pelo Supabase
        df_completo["nome_plano"] = df_completo["plano"].apply(lambda x: x["nome"])
        df_completo["livro"] = df_completo["livro"].apply(lambda x: x["nome"])
        df_completo = df_completo.rename(columns={"data_leitura": "data"})
        df_completo["data"] = pd.to_datetime(df_completo["data"])

        # Agrupar em um dicionário por nome de plano
        todos_planos = {}
        nomes_planos = df_completo["nome_plano"].unique()

        for nome in nomes_planos:
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


def carregar_lista_usuarios():
    """Carrega a lista de nomes de usuários da tabela tb_usuarios."""
    try:
        response = supabase.table("tb_usuarios").select("nome").order("nome").execute()
        lista = [item["nome"] for item in response.data]
        return sorted(lista)
    except Exception as e:
        st.error(f"Erro ao carregar lista de usuários: {e}")
        return ["Erro"]


def carregar_leituras_usuario(usuario, plano):
    """Carrega o histórico de leitura de um usuário para um plano específico."""
    try:
        # 1. Obter IDs de usuário e plano
        user_resp = supabase.table("tb_usuarios").select("id").eq("nome", usuario).single().execute()
        plano_resp = supabase.table("tb_planos").select("id").eq("nome", plano).single().execute()

        if not user_resp.data or not plano_resp.data:
            return pd.DataFrame(columns=["Livro", "Capitulo", "Data"])

        user_id = user_resp.data["id"]
        plano_id = plano_resp.data["id"]

        # 2. Buscar leituras com join para obter o nome do livro
        response = (
            supabase.table("tb_leituras")
            .select("capitulo, created_at, livro:tb_livros(nome)")
            .eq("usuario_id", user_id)
            .eq("plano_id", plano_id)
            .execute()
        )

        df = pd.DataFrame(response.data)

        if not df.empty:
            # Processar dados aninhados
            df["livro"] = df["livro"].apply(lambda x: x["nome"] if isinstance(x, dict) else None)
            df = df.rename(columns={"livro": "Livro", "capitulo": "Capitulo", "created_at": "Data"})
            df["Data"] = pd.to_datetime(df["Data"])

        return df
    except Exception as e:
        print(f"AVISO: Não foi possível carregar leituras para {usuario} no plano {plano}: {e}")
        return pd.DataFrame(columns=["Livro", "Capitulo", "Data"])


def salvar_nova_leitura(usuario, plano, livro, capitulo):
    """Salva um novo registro de leitura, verificando antes se ele já não existe."""
    try:
        # 1. Obter os IDs correspondentes aos nomes
        user_id = supabase.table("tb_usuarios").select("id").eq("nome", usuario).single().execute().data['id']
        plano_id = supabase.table("tb_planos").select("id").eq("nome", plano).single().execute().data['id']
        livro_id = supabase.table("tb_livros").select("id").eq("nome", livro).single().execute().data['id']

        # 2. Verificar se a leitura já existe
        check_resp = supabase.table("tb_leituras").select("id", count='exact') \
            .eq("usuario_id", user_id) \
            .eq("plano_id", plano_id) \
            .eq("id_livro", livro_id) \
            .eq("capitulo", capitulo) \
            .execute()

        # 3. Se não existir (count=0), insere o novo registro
        if check_resp.count == 0:
            supabase.table("tb_leituras").insert({
                "usuario_id": user_id,
                "plano_id": plano_id,
                "id_livro": livro_id,
                "capitulo": capitulo
            }).execute()

    except Exception as e:
        st.error(f"Erro ao salvar: {e}")


def calcular_metricas(dict_planos):
    """Calcula as métricas do dashboard a partir das novas tabelas."""
    try:
        # Busca todas as leituras, trazendo o nome do usuário e do plano via join
        response = supabase.table("tb_leituras").select(
            "usuario:tb_usuarios(nome), plano:tb_planos(nome)"
        ).execute()

        df_registros = pd.DataFrame(response.data)
        if df_registros.empty:
            return None, None

        # Processar dados aninhados
        df_registros["usuario"] = df_registros["usuario"].apply(lambda x: x["nome"])
        df_registros["plano"] = df_registros["plano"].apply(lambda x: x["nome"])
        df_registros = df_registros.rename(columns={"usuario": "Usuario", "plano": "Plano"})

    except Exception as e:
        st.warning(f"Não foi possível carregar os registros para o dashboard: {e}")
        return None, None

    dados_consolidados = []
    usuarios_unicos = set()
    qtd_em_dia = 0
    qtd_atrasados = 0

    hoje = datetime.now(FUSO_BR)
    hoje_date = hoje.date()

    grupos = df_registros.groupby(["Usuario", "Plano"])

    for (usuario, plano_nome), grupo in grupos:
        if plano_nome not in dict_planos:
            continue

        usuarios_unicos.add(usuario)
        caps_lidos = len(grupo)

        df_plano = dict_planos[plano_nome]

        meta_ate_hoje = df_plano[df_plano["data"].dt.date <= hoje_date]["qtd_capitulos"].sum()
        total_do_plano = df_plano["qtd_capitulos"].sum()

        status = "Em dia" if caps_lidos >= meta_ate_hoje else "Atrasado"
        if status == "Em dia":
            qtd_em_dia += 1
        else:
            qtd_atrasados += 1

        dados_consolidados.append(
            {
                "Usuario": usuario,
                "Plano": plano_nome,
                "Lidos": caps_lidos,
                "Meta_Hoje": meta_ate_hoje,
                "Total_Plano": total_do_plano,
                "Status": status,
                "Pct_Lido": (caps_lidos / total_do_plano) if total_do_plano > 0 else 0,
                "Pct_Meta": ((meta_ate_hoje / total_do_plano) if total_do_plano > 0 else 0),
            }
        )

    metricas = {
        "total_leitores": len(usuarios_unicos),
        "total_lidos": len(df_registros),
        "em_dia": qtd_em_dia,
        "atrasados": qtd_atrasados,
    }
    return metricas, pd.DataFrame(dados_consolidados)


# --- 4. INICIALIZAÇÃO DA INTERFACE ---

lista_usuarios = carregar_lista_usuarios()
dict_planos = carregar_planos()

if "data_selecionada" not in st.session_state:
    st.session_state["data_selecionada"] = datetime.now(FUSO_BR)
if "usuario_anterior" not in st.session_state:
    st.session_state["usuario_anterior"] = None
if "plano_anterior" not in st.session_state:
    st.session_state["plano_anterior"] = None

with st.sidebar:
    st.markdown("### ⛪ Menu")
    pagina = st.radio("Navegar", ["Minha Leitura", "Progresso Geral"], label_visibility="collapsed")
    st.divider()
    st.caption("Rondoninha Church © 2026")

# --- PÁGINA 1: LEITURA ---
if pagina == "Minha Leitura":
    col_user, col_plano = st.columns(2)

    with col_user:
        if not lista_usuarios:
            st.error("Nenhum usuário encontrado.")
            st.stop()

        usuario = st.selectbox("👤 Quem é você?", lista_usuarios)

        if usuario != st.session_state.get("user_check_plano"):
            ultimo_plano = buscar_ultimo_plano_ativo(usuario)
            if ultimo_plano and ultimo_plano in dict_planos:
                st.session_state["plano_selecionado_widget"] = ultimo_plano
            st.session_state["user_check_plano"] = usuario

    if not dict_planos:
        st.warning("Carregando planos...")
        st.stop()

    with col_plano:
        lista_planos_keys = sorted(list(dict_planos.keys()))
        plano_nome = st.selectbox(
            "📅 Escolha o Plano", lista_planos_keys, key="plano_selecionado_widget"
        )

    df_plano = dict_planos[plano_nome]

    mudou_usuario = usuario != st.session_state["usuario_anterior"]
    mudou_plano = plano_nome != st.session_state["plano_anterior"]

    if mudou_usuario or mudou_plano:
        df_historico = carregar_leituras_usuario(usuario, plano_nome)

        proxima_data = encontrar_proxima_data_nao_lida(df_plano, df_historico)

        try:
            st.session_state["data_selecionada"] = pd.to_datetime(proxima_data)
            msg_data = pd.to_datetime(proxima_data).strftime("%d/%m")

            if pd.to_datetime(proxima_data).date() != datetime.now(FUSO_BR).date():
                st.toast(f"Indo para próxima leitura pendente: {msg_data}", icon="📖")
            elif mudou_usuario:
                st.toast(f"Tudo em dia! Mostrando hoje: {msg_data}", icon="✅")

        except:
            st.session_state["data_selecionada"] = datetime.now(FUSO_BR)

        st.session_state["usuario_anterior"] = usuario
        st.session_state["plano_anterior"] = plano_nome

    st.markdown("---")
    c_data, c_info = st.columns([1, 3])

    with c_data:
        data_input = st.date_input("Data da Leitura", value=st.session_state["data_selecionada"])
        st.session_state["data_selecionada"] = pd.to_datetime(data_input)

    df_plano_valido = df_plano.dropna(subset=["data"])
    leitura_do_dia = df_plano_valido[
        df_plano_valido["data"].dt.date == st.session_state["data_selecionada"].date()
    ]

    df_lidos = carregar_leituras_usuario(usuario, plano_nome)

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
                    chave_botao = f"{usuario}_{plano_nome}_{livro}_{c}"

                    ja_leu = False
                    if not df_lidos.empty:
                        check = df_lidos[(df_lidos["Livro"] == livro) & (df_lidos["Capitulo"] == c)]
                        if not check.empty:
                            ja_leu = True

                    label = f"{c} ✅" if ja_leu else f"{c}"

                    if cols[i % 10].button(
                        label,
                        key=chave_botao,
                        disabled=ja_leu,
                        type="primary" if ja_leu else "secondary",
                    ):
                        salvar_nova_leitura(usuario, plano_nome, livro, c)
                        st.rerun()

# --- PÁGINA 2: DASHBOARD ---
elif pagina == "Progresso Geral":
    st.markdown("### 🏆 Dashboard da Comunidade")
    metricas, df_dash = calcular_metricas(dict_planos)

    if metricas:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("👥 Leitores", metricas["total_leitores"])
        c2.metric("📚 Capítulos Lidos", metricas["total_lidos"])
        c3.metric("🎯 Em Dia", metricas["em_dia"])
        c4.metric("⚠️ Atrasados", metricas["atrasados"])

        st.markdown("<br>", unsafe_allow_html=True)

        if not df_dash.empty:
            planos_ativos = sorted(df_dash["Plano"].unique())

            for plano in planos_ativos:
                with st.container():
                    st.write(f"**Plano: {plano}**")
                    df_filtro = df_dash[df_dash["Plano"] == plano].copy()

                    base = alt.Chart(df_filtro).encode(y=alt.Y("Usuario", title=None))

                    barra = base.mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5).encode(
                        x=alt.X(
                            "Pct_Lido",
                            axis=alt.Axis(format="%", title="Progresso"),
                            scale=alt.Scale(domain=[0, 1]),
                        ),
                        color=alt.Color(
                            "Status",
                            scale=alt.Scale(
                                domain=["Em dia", "Atrasado"],
                                range=["#2ecc71", "#e74c3c"],
                            ),
                            legend=None,
                        ),
                        tooltip=["Usuario", "Lidos", "Status"],
                    )

                    meta = base.mark_tick(color="black", thickness=3, height=20).encode(
                        x="Pct_Meta",
                        tooltip=[alt.Tooltip("Pct_Meta", format=".1%", title="Meta Esperada")],
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
                    width="stretch",
                    hide_index=True,
                )
        else:
            st.info("Nenhum dado para exibir.")
    else:
        st.info("Ainda não há registros de leitura.")
