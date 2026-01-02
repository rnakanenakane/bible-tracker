import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
from supabase import create_client, Client
import pytz

st.set_page_config(
    page_title="Rondoninha Church | Leitura",
    page_icon="✝️",
    layout="wide"
)

# Estilos CSS Personalizados
st.markdown("""
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
""", unsafe_allow_html=True)

# --- 2. CONFIGURAÇÕES GERAIS ---
# Define o fuso horário do Brasil para evitar virada de dia errada (UTC)
FUSO_BR = pytz.timezone('America/Sao_Paulo')

st.markdown('<div class="main-header">✝️ Rondoninha Church: Leitura Bíblica</div>', unsafe_allow_html=True)

# Conexão com Supabase
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Erro ao configurar Supabase. Verifique o secrets.toml")
    st.stop()

def expandir_capitulos(str_caps):
    """Converte '1-3' em [1, 2, 3] ou '1' em [1]"""
    str_caps = str(str_caps).strip()
    if '-' in str_caps:
        try:
            inicio, fim = map(int, str_caps.split('-'))
            return list(range(inicio, fim + 1))
        except: return []
    else:
        try: return [int(str_caps)]
        except: return []

@st.cache_data(ttl=300) # Cache de 5 min para não ficar batendo no banco toda hora
def carregar_planos():
    try:
        # Busca todos os registros da tabela 'planos' no Supabase
        response = supabase.table("planos").select("*").execute()
        df_completo = pd.DataFrame(response.data)
        
        if df_completo.empty:
            st.warning("Nenhum plano encontrado no banco de dados.")
            return {}

        # Ajusta formatos
        df_completo['data'] = pd.to_datetime(df_completo['data'])
        
        # Cria um dicionário separado por nome do plano
        todos_planos = {}
        nomes_planos = df_completo['nome_plano'].unique()
        
        for nome in nomes_planos:
            df_filtrado = df_completo[df_completo['nome_plano'] == nome].copy()
            # Ordena por data
            df_filtrado = df_filtrado.sort_values(by='data')
            
            # Pré-cálculo de quantidade de capítulos (para a meta)
            df_filtrado['qtd_capitulos'] = df_filtrado['capitulos'].apply(lambda x: len(expandir_capitulos(x)))
            todos_planos[nome] = df_filtrado
            
        return todos_planos
    except Exception as e:
        st.error(f"Erro ao carregar planos do Supabase: {e}")
        return {}

def carregar_lista_usuarios():
    try:
        # Busca na tabela 'usuarios'
        response = supabase.table("usuarios").select("nome").execute()
        lista = [item['nome'] for item in response.data]
        return sorted(lista)
    except Exception as e:
        st.error(f"Erro ao conectar Supabase (Usuários): {e}")
        return ["Erro"]

def carregar_leituras_usuario(usuario, plano):
    try:
        # Busca na tabela 'leituras' filtrando por usuario e plano
        response = supabase.table("leituras") \
            .select("*") \
            .eq("usuario", usuario) \
            .eq("plano", plano) \
            .execute()
        
        df = pd.DataFrame(response.data)
        if not df.empty:
            # Renomeia colunas para bater com a lógica do app
            df = df.rename(columns={"livro": "Livro", "capitulo": "Capitulo", "created_at": "Data"})
            df['Data'] = pd.to_datetime(df['Data'])
        return df
    except Exception:
        return pd.DataFrame(columns=["Livro", "Capitulo", "Data"])

def salvar_nova_leitura(usuario, plano, livro, capitulo):
    try:
        # Insere no Supabase
        dados = {
            "usuario": usuario,
            "plano": plano,
            "livro": livro,
            "capitulo": capitulo
            # created_at é automático no banco
        }
        supabase.table("leituras").insert(dados).execute()
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")

def calcular_metricas(dict_planos):
    try:
        response = supabase.table("leituras").select("*").execute()
        df_registros = pd.DataFrame(response.data)
        
        if df_registros.empty: return None, None
        
        df_registros = df_registros.rename(columns={"usuario": "Usuario", "plano": "Plano"})
    except: return None, None

    dados_consolidados = []
    usuarios_unicos = set()
    qtd_em_dia = 0
    qtd_atrasados = 0
    
    hoje = datetime.now(FUSO_BR)
    hoje_date = hoje.date()
    
    grupos = df_registros.groupby(["Usuario", "Plano"])
    
    for (usuario, plano_nome), grupo in grupos:
        if plano_nome not in dict_planos: continue
        
        usuarios_unicos.add(usuario)
        caps_lidos = len(grupo)
        
        df_plano = dict_planos[plano_nome]
        
        # Filtra metas até a data de hoje (inclusive)
        meta_ate_hoje = df_plano[df_plano['data'].dt.date <= hoje_date]['qtd_capitulos'].sum()
        total_do_plano = df_plano['qtd_capitulos'].sum()
        
        status = "Em dia" if caps_lidos >= meta_ate_hoje else "Atrasado"
        if status == "Em dia": qtd_em_dia += 1
        else: qtd_atrasados += 1
            
        dados_consolidados.append({
            "Usuario": usuario,
            "Plano": plano_nome,
            "Lidos": caps_lidos,
            "Meta_Hoje": meta_ate_hoje,
            "Total_Plano": total_do_plano,
            "Status": status,
            "Pct_Lido": (caps_lidos / total_do_plano) if total_do_plano > 0 else 0,
            "Pct_Meta": (meta_ate_hoje / total_do_plano) if total_do_plano > 0 else 0
        })

    metricas = {
        "total_leitores": len(usuarios_unicos),
        "total_lidos": len(df_registros),
        "em_dia": qtd_em_dia,
        "atrasados": qtd_atrasados
    }
    return metricas, pd.DataFrame(dados_consolidados)


lista_usuarios = carregar_lista_usuarios()
dict_planos = carregar_planos()

if 'data_selecionada' not in st.session_state: 
    st.session_state['data_selecionada'] = datetime.now(FUSO_BR)
if 'usuario_anterior' not in st.session_state: 
    st.session_state['usuario_anterior'] = None

# Sidebar
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
    
    if not dict_planos:
        st.warning("Carregando planos...")
        st.stop()
        
    with col_plano:
        plano_nome = st.selectbox("📅 Escolha o Plano", sorted(list(dict_planos.keys())))
    
    df_plano = dict_planos[plano_nome]
    
    if usuario != st.session_state['usuario_anterior']:
        df_historico = carregar_leituras_usuario(usuario, plano_nome)
        if not df_historico.empty and 'Data' in df_historico.columns:
            try:
                ultima = pd.to_datetime(df_historico['Data']).max()
                st.toast(f"Última leitura registrada em: {ultima.strftime('%d/%m')}", icon="🔙")
            except: pass
        
        st.session_state['data_selecionada'] = datetime.now(FUSO_BR)
        st.session_state['usuario_anterior'] = usuario

    st.markdown("---")
    c_data, c_info = st.columns([1, 3])
    
    with c_data:
        data_input = st.date_input("Data da Leitura", value=st.session_state['data_selecionada'])
        st.session_state['data_selecionada'] = pd.to_datetime(data_input)
    
    # Filtra o plano para a data selecionada
    df_plano_valido = df_plano.dropna(subset=['data'])
    leitura_do_dia = df_plano_valido[df_plano_valido['data'].dt.date == st.session_state['data_selecionada'].date()]
    
    df_lidos = carregar_leituras_usuario(usuario, plano_nome)

    with c_info:
        if leitura_do_dia.empty:
            st.info("😴 Nada programado para esta data.")
        else:
            for _, row in leitura_do_dia.iterrows():
                livro = row['livro']
                caps_str = str(row['capitulos'])
                lista_caps = expandir_capitulos(caps_str)
                
                st.markdown(f"### 📖 {livro} <span style='font-size:0.8em; color:gray'>Caps {caps_str}</span>", unsafe_allow_html=True)
                
                cols = st.columns(10)
                for i, c in enumerate(lista_caps):
                    chave_botao = f"{usuario}_{plano_nome}_{livro}_{c}"
                    
                    ja_leu = False
                    if not df_lidos.empty:
                         check = df_lidos[
                             (df_lidos['Livro'] == livro) & 
                             (df_lidos['Capitulo'] == c)
                         ]
                         if not check.empty: ja_leu = True
                    
                    label = f"{c} ✅" if ja_leu else f"{c}"
                    
                    if cols[i%10].button(
                        label, 
                        key=chave_botao, 
                        disabled=ja_leu, 
                        type="primary" if ja_leu else "secondary"
                    ):
                        salvar_nova_leitura(usuario, plano_nome, livro, c)
                        st.rerun()

# --- PÁGINA 2: DASHBOARD ---
elif pagina == "Progresso Geral":
    st.markdown("### 🏆 Dashboard da Comunidade")
    metricas, df_dash = calcular_metricas(dict_planos)
    
    if metricas:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("👥 Leitores", metricas['total_leitores'])
        c2.metric("📚 Capítulos Lidos", metricas['total_lidos'])
        c3.metric("🎯 Em Dia", metricas['em_dia'])
        c4.metric("⚠️ Atrasados", metricas['atrasados'])
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if not df_dash.empty:
            planos_ativos = sorted(df_dash['Plano'].unique())
            
            for plano in planos_ativos:
                with st.container():
                    st.write(f"**Plano: {plano}**")
                    df_filtro = df_dash[df_dash['Plano'] == plano].copy()
                    
                    base = alt.Chart(df_filtro).encode(y=alt.Y('Usuario', title=None))
                    
                    barra = base.mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5).encode(
                        x=alt.X('Pct_Lido', axis=alt.Axis(format='%', title='Progresso'), scale=alt.Scale(domain=[0, 1])),
                        color=alt.Color('Status', scale=alt.Scale(domain=['Em dia', 'Atrasado'], range=['#2ecc71', '#e74c3c']), legend=None),
                        tooltip=['Usuario', 'Lidos', 'Status']
                    )
                    
                    meta = base.mark_tick(color='black', thickness=3, height=20).encode(
                        x='Pct_Meta',
                        tooltip=[alt.Tooltip('Pct_Meta', format='.1%', title="Meta Esperada")]
                    )
                    
                    texto = base.mark_text(align='left', dx=5, color='black').encode(
                        x='Pct_Lido',
                        text=alt.Text('Pct_Lido', format='.0%')
                    )
                    
                    altura = max(120, len(df_filtro) * 60)
                    st.altair_chart((barra + meta + texto).properties(height=altura), use_container_width=True)
                    st.divider()
                    
            with st.expander("📂 Ver Tabela Completa"):
                st.dataframe(
                    df_dash[['Usuario', 'Plano', 'Lidos', 'Meta_Hoje', 'Status']], 
                    width="stretch",
                    hide_index=True
                )
        else: st.info("Nenhum dado para exibir.") 
    else: st.info("Ainda não há registros de leitura.")