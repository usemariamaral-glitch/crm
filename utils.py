import streamlit as st
import pandas as pd
import hashlib
import google.auth
from google.cloud import bigquery
from datetime import date, timedelta


@st.cache_resource
def get_client():
    try:
        if "gcp_service_account" in st.secrets:
            from google.oauth2 import service_account
            credentials = service_account.Credentials.from_service_account_info(
                st.secrets["gcp_service_account"],
                scopes=["https://www.googleapis.com/auth/bigquery"],
            )
            return bigquery.Client(project="datalake-488518", credentials=credentials)
        credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/bigquery"]
        )
        return bigquery.Client(project="datalake-488518", credentials=credentials)
    except Exception as e:
        st.error(f"Erro de autenticação com o Google: {e}")
        st.stop()


@st.cache_data(ttl=3600, show_spinner="Carregando dados do BigQuery...")
def run_query(sql: str) -> pd.DataFrame:
    try:
        df = get_client().query(sql).to_dataframe()
        for col in df.select_dtypes(include=["object"]).columns:
            try:
                df[col] = pd.to_numeric(df[col])
            except (ValueError, TypeError):
                pass
        return df
    except Exception as e:
        st.error(f"Erro na consulta: {e}")
        return pd.DataFrame()


def periodo_para_data(periodo: str) -> str:
    hoje = date.today()
    mapa = {
        "Últimos 30 dias":  str(hoje - timedelta(days=30)),
        "Últimos 90 dias":  str(hoje - timedelta(days=90)),
        "Últimos 12 meses": str(hoje.replace(year=hoje.year - 1)),
        "Este ano":         str(hoje.replace(month=1, day=1)),
        "Tudo":             "2000-01-01",
    }
    return mapa.get(periodo, "2000-01-01")


def fmt_brl(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "R$ 0,00"
    return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_num(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "0"
    return f"{int(float(v)):,}".replace(",", ".")


def fone_whatsapp(ddd, tel) -> str:
    try:
        if pd.isna(ddd) or pd.isna(tel):
            return ""
        d = str(int(float(str(ddd).strip().replace("(", "").replace(")", "").replace(" ", ""))))
        t = str(int(float(str(tel).strip().replace("-", "").replace(" ", ""))))
        if not d or not t:
            return ""
        return f"55{d}{t}"
    except (ValueError, TypeError, OverflowError):
        return ""


def primeiro_nome(nome) -> str:
    if not pd.notna(nome):
        return ""
    parts = str(nome).strip().split()
    return parts[0].capitalize() if parts else ""


# ── Tema / CSS ────────────────────────────────────────────────────────────────
# Cor principal da marca: #1d3c4d (azul marinho)
# Cor de destaque:        #C85DA4 (rosa — gráficos e badges)

CSS_LIGHT = """
<style>
/* ═══ APP BASE ═══ */
.stApp { background: #F2F6F8 !important; }
.block-container {
    padding-top: 1.8rem !important;
    padding-bottom: 2rem !important;
}

/* ═══ SIDEBAR — azul marinho escuro ═══ */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1d3c4d 0%, #162e3c 100%) !important;
    border-right: none !important;
    box-shadow: 4px 0 20px rgba(0,0,0,0.18) !important;
}
section[data-testid="stSidebar"] * { color: #A8C8D8 !important; }
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] div { color: #B8D0DC !important; }
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    color: white !important;
    font-size: 0.7rem !important;
    font-weight: 800 !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    border-bottom: none !important;
    margin-bottom: 0.4rem !important;
}
section[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.12) !important;
    margin: 0.6rem 0 !important;
}
section[data-testid="stSidebar"] .stButton > button {
    background: rgba(255,255,255,0.08) !important;
    border: 1px solid rgba(255,255,255,0.18) !important;
    color: #C8DCE8 !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.82rem !important;
    transition: all 0.2s ease !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.16) !important;
    color: white !important;
}
/* Nav links no menu lateral */
[data-testid="stSidebarNav"] a { color: #A8C8D8 !important; }
[data-testid="stSidebarNav"] a:hover { color: white !important; background: rgba(255,255,255,0.08) !important; }
[data-testid="stSidebarNav"] a[aria-current="page"] {
    color: white !important;
    background: rgba(255,255,255,0.14) !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
}

/* ═══ METRIC CARDS ═══ */
[data-testid="stMetric"] {
    background: white !important;
    border: 1px solid #C8D8E4 !important;
    border-radius: 14px !important;
    padding: 1.2rem 1.5rem !important;
    box-shadow: 0 2px 14px rgba(29,60,77,0.10) !important;
    position: relative !important;
    overflow: hidden !important;
    transition: transform 0.2s ease, box-shadow 0.2s ease !important;
}
[data-testid="stMetric"]::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 4px;
    background: linear-gradient(90deg, #1d3c4d, #2d7a94);
    border-radius: 4px 4px 0 0;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-3px) !important;
    box-shadow: 0 8px 28px rgba(29,60,77,0.16) !important;
}
[data-testid="stMetricValue"] {
    color: #1d3c4d !important;
    font-weight: 800 !important;
    font-size: 1.45rem !important;
    letter-spacing: -0.01em !important;
}
[data-testid="stMetricLabel"] {
    color: #6B8A9A !important;
    font-size: 0.72rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.07em !important;
}

/* ═══ HEADINGS ═══ */
h1 {
    color: #1d3c4d !important;
    font-weight: 800 !important;
    font-size: 1.75rem !important;
    letter-spacing: -0.02em !important;
    padding-bottom: 0.5rem !important;
    border-bottom: 2px solid #C8D8E4 !important;
    margin-bottom: 1.4rem !important;
}
h2 { color: #1d3c4d !important; font-weight: 700 !important; font-size: 1.1rem !important; }
h3 { color: #2d5a72 !important; font-weight: 600 !important; }

/* ═══ BUTTONS ═══ */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #1d3c4d 0%, #2d7a94 100%) !important;
    border: none !important;
    color: white !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    box-shadow: 0 4px 14px rgba(29,60,77,0.32) !important;
    transition: all 0.2s ease !important;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 6px 20px rgba(29,60,77,0.48) !important;
    transform: translateY(-1px) !important;
}
.stButton > button[kind="secondary"] {
    border-radius: 10px !important;
    border: 1.5px solid #C8D8E4 !important;
    color: #1d3c4d !important;
    font-weight: 600 !important;
    background: white !important;
    transition: all 0.2s ease !important;
}
.stButton > button[kind="secondary"]:hover {
    border-color: #1d3c4d !important;
    background: #EEF3F6 !important;
}

/* ═══ INPUTS ═══ */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input {
    border-radius: 10px !important;
    border: 1.5px solid #C8D8E4 !important;
    background: white !important;
    transition: all 0.2s ease !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus {
    border-color: #1d3c4d !important;
    box-shadow: 0 0 0 3px rgba(29,60,77,0.12) !important;
}

/* ═══ SELECT / MULTISELECT ═══ */
[data-testid="stSelectbox"] > div > div,
[data-testid="stMultiSelect"] > div > div {
    border-radius: 10px !important;
    border-color: #C8D8E4 !important;
    background: white !important;
}

/* ═══ DATAFRAME ═══ */
[data-testid="stDataFrame"] {
    border-radius: 14px !important;
    overflow: hidden !important;
    box-shadow: 0 2px 10px rgba(29,60,77,0.08) !important;
    border: 1px solid #C8D8E4 !important;
}

/* ═══ PLOTLY CHARTS ═══ */
[data-testid="stPlotlyChart"] {
    border-radius: 16px !important;
    overflow: hidden !important;
    box-shadow: 0 2px 14px rgba(29,60,77,0.08) !important;
    background: white !important;
    border: 1px solid #C8D8E4 !important;
    padding: 0.3rem !important;
}

/* ═══ EXPANDERS ═══ */
details {
    border: 1.5px solid #C8D8E4 !important;
    border-radius: 14px !important;
    overflow: hidden !important;
}
details summary {
    background: linear-gradient(135deg, #EEF3F6, #fff) !important;
    color: #1d3c4d !important;
    font-weight: 600 !important;
    padding: 0.8rem 1rem !important;
}

/* ═══ ALERTS ═══ */
[data-testid="stAlert"] { border-radius: 12px !important; }

/* ═══ DIVIDER ═══ */
hr { border-color: #C8D8E4 !important; opacity: 0.9 !important; }

/* ═══ DOWNLOAD BUTTON ═══ */
[data-testid="stDownloadButton"] button {
    border-radius: 10px !important;
    border: 2px solid #1d3c4d !important;
    color: #1d3c4d !important;
    background: white !important;
    font-weight: 700 !important;
    transition: all 0.2s ease !important;
}
[data-testid="stDownloadButton"] button:hover {
    background: #1d3c4d !important;
    color: white !important;
    box-shadow: 0 4px 14px rgba(29,60,77,0.32) !important;
}

/* ═══ TABS ═══ */
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: #1d3c4d !important;
    border-bottom-color: #1d3c4d !important;
}
</style>
"""

CSS_DARK = """
<style>
/* ═══ APP BASE ═══ */
.stApp { background: #091520 !important; }
.block-container { padding-top: 1.8rem !important; padding-bottom: 2rem !important; }
body, p, span, label, li, .stMarkdown { color: #B8D0DC !important; }

/* ═══ SIDEBAR (mais escura no dark mode) ═══ */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #091520 0%, #0d1e2b 100%) !important;
    border-right: 1px solid #1a3040 !important;
}
section[data-testid="stSidebar"] * { color: #7A9AAA !important; }
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    color: #A8C8D8 !important;
    font-size: 0.7rem !important;
    font-weight: 800 !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    border-bottom: none !important;
}
section[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.07) !important;
}
section[data-testid="stSidebar"] .stButton > button {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.10) !important;
    color: #7A9AAA !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.82rem !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.10) !important;
    color: #A8C8D8 !important;
}
[data-testid="stSidebarNav"] a { color: #7A9AAA !important; }
[data-testid="stSidebarNav"] a:hover { color: #A8C8D8 !important; }
[data-testid="stSidebarNav"] a[aria-current="page"] {
    color: #C8E0EC !important;
    background: rgba(255,255,255,0.08) !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
}

/* ═══ METRIC CARDS ═══ */
[data-testid="stMetric"] {
    background: #0F2030 !important;
    border: 1px solid #1E3A50 !important;
    border-radius: 14px !important;
    padding: 1.2rem 1.5rem !important;
    box-shadow: 0 2px 16px rgba(0,0,0,0.3) !important;
    position: relative !important;
    overflow: hidden !important;
    transition: transform 0.2s ease, box-shadow 0.2s ease !important;
}
[data-testid="stMetric"]::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 4px;
    background: linear-gradient(90deg, #2d7a94, #5AAAC8);
    border-radius: 4px 4px 0 0;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-3px) !important;
    box-shadow: 0 8px 28px rgba(0,0,0,0.4) !important;
}
[data-testid="stMetricValue"] {
    color: #5AAAC8 !important;
    font-weight: 800 !important;
    font-size: 1.45rem !important;
}
[data-testid="stMetricLabel"] {
    color: #4A7A8A !important;
    font-size: 0.72rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.07em !important;
}

/* ═══ HEADINGS ═══ */
h1 {
    color: #5AAAC8 !important;
    font-weight: 800 !important;
    font-size: 1.75rem !important;
    letter-spacing: -0.02em !important;
    padding-bottom: 0.5rem !important;
    border-bottom: 2px solid #1E3A50 !important;
    margin-bottom: 1.4rem !important;
}
h2 { color: #4A9AB8 !important; font-weight: 700 !important; }
h3 { color: #3A8AA8 !important; font-weight: 600 !important; }

/* ═══ BUTTONS ═══ */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #1d3c4d 0%, #2d7a94 100%) !important;
    border: none !important;
    color: white !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    box-shadow: 0 4px 14px rgba(0,0,0,0.4) !important;
    transition: all 0.2s ease !important;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 6px 20px rgba(45,122,148,0.5) !important;
    transform: translateY(-1px) !important;
}
.stButton > button[kind="secondary"] {
    border-radius: 10px !important;
    background: #0F2030 !important;
    border: 1.5px solid #1E3A50 !important;
    color: #7A9AAA !important;
    font-weight: 600 !important;
    transition: all 0.2s ease !important;
}
.stButton > button[kind="secondary"]:hover {
    border-color: #3A8AAA !important;
    color: #A8C8D8 !important;
}

/* ═══ INPUTS ═══ */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input {
    border-radius: 10px !important;
    border: 1.5px solid #1E3A50 !important;
    background: #0F2030 !important;
    color: #B8D0DC !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus {
    border-color: #3A8AAA !important;
    box-shadow: 0 0 0 3px rgba(58,138,170,0.18) !important;
}

/* ═══ SELECT / MULTISELECT ═══ */
[data-testid="stSelectbox"] > div > div,
[data-testid="stMultiSelect"] > div > div {
    border-radius: 10px !important;
    border-color: #1E3A50 !important;
    background: #0F2030 !important;
}

/* ═══ DATAFRAME ═══ */
[data-testid="stDataFrame"] {
    border-radius: 14px !important;
    overflow: hidden !important;
    box-shadow: 0 2px 10px rgba(0,0,0,0.35) !important;
    border: 1px solid #1E3A50 !important;
}

/* ═══ PLOTLY CHARTS ═══ */
[data-testid="stPlotlyChart"] {
    border-radius: 16px !important;
    overflow: hidden !important;
    box-shadow: 0 2px 14px rgba(0,0,0,0.35) !important;
    background: #0F2030 !important;
    border: 1px solid #1E3A50 !important;
    padding: 0.3rem !important;
}

/* ═══ EXPANDERS ═══ */
details {
    border: 1.5px solid #1E3A50 !important;
    border-radius: 14px !important;
    overflow: hidden !important;
    background: #0F2030 !important;
}
details summary {
    background: #132838 !important;
    color: #5AAAC8 !important;
    font-weight: 600 !important;
    padding: 0.8rem 1rem !important;
}

/* ═══ ALERTS / DIVIDER ═══ */
[data-testid="stAlert"] { border-radius: 12px !important; }
hr { border-color: #1E3A50 !important; opacity: 0.9 !important; }

/* ═══ DOWNLOAD BUTTON ═══ */
[data-testid="stDownloadButton"] button {
    border-radius: 10px !important;
    border: 2px solid #3A8AAA !important;
    color: #5AAAC8 !important;
    background: #0F2030 !important;
    font-weight: 700 !important;
    transition: all 0.2s ease !important;
}
[data-testid="stDownloadButton"] button:hover {
    background: #1d3c4d !important;
    color: white !important;
    border-color: transparent !important;
}

/* ═══ CHECKBOX / RADIO ═══ */
[data-testid="stCheckbox"] label,
[data-testid="stRadio"] label { color: #B8D0DC !important; }

/* ═══ TABS ═══ */
[data-testid="stTabs"] [role="tab"] { color: #4A7A8A !important; }
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: #5AAAC8 !important;
    border-bottom-color: #5AAAC8 !important;
}
</style>
"""

# Alias para compatibilidade
CSS = CSS_LIGHT


def get_css() -> str:
    return CSS_DARK if st.session_state.get("dark_mode", False) else CSS_LIGHT


# ── Autenticação ──────────────────────────────────────────────────────────────

_SALT = "crm_mari_2024"


def _hash_senha(senha: str) -> str:
    return "sha256:" + hashlib.sha256(f"{_SALT}{senha}".encode()).hexdigest()


def _verificar_credencial(senha_input: str, senha_armazenada: str) -> bool:
    if senha_armazenada.startswith("sha256:"):
        return _hash_senha(senha_input) == senha_armazenada
    return senha_input == senha_armazenada


def _sidebar_controles():
    """Adiciona card de usuário + botões de tema e logout no topo da sidebar."""
    dark = st.session_state.get("dark_mode", False)
    nome = st.session_state.get("_usuario", {}).get("name", "Usuário")

    with st.sidebar:
        st.markdown(f"""
        <div style="background:rgba(255,255,255,0.09);
                    border:1px solid rgba(255,255,255,0.16);
                    border-radius:10px;padding:0.65rem 1rem;margin-bottom:0.75rem">
            <div style="font-size:0.65rem;color:rgba(168,200,216,0.65);
                        font-weight:800;text-transform:uppercase;letter-spacing:0.1em">
                Logado como
            </div>
            <div style="font-weight:700;color:white;font-size:0.9rem;margin-top:3px">
                👤 {nome}
            </div>
        </div>
        """, unsafe_allow_html=True)

        col_t, col_s = st.columns(2)
        with col_t:
            icone = "☀️ Claro" if dark else "🌙 Escuro"
            if st.button(icone, use_container_width=True, key="_btn_tema"):
                st.session_state["dark_mode"] = not dark
                st.rerun()
        with col_s:
            if st.button("🚪 Sair", use_container_width=True, key="_btn_sair"):
                st.session_state["_autenticado"] = False
                st.session_state["_usuario"] = {}
                st.rerun()

        st.divider()


def _tela_login():
    dark = st.session_state.get("dark_mode", False)
    bg_card = "#0F2030" if dark else "white"
    brd     = "#1E3A50" if dark else "#C8D8E4"
    clr_h   = "#5AAAC8" if dark else "#1d3c4d"
    clr_sub = "#4A7A8A" if dark else "#6B8A9A"

    users = dict(st.secrets.get("users", {}))

    _, col, _ = st.columns([1, 1.1, 1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(f"""
        <div style="background:{bg_card};border:1px solid {brd};border-radius:22px;
                    padding:2.4rem 2rem 1.8rem;
                    box-shadow:0 12px 48px rgba(29,60,77,0.18);text-align:center">
            <div style="font-size:3rem;line-height:1.1;margin-bottom:0.5rem">👗</div>
            <h2 style="color:{clr_h};margin:0 0 0.2rem;font-size:1.5rem;font-weight:800;
                        border:none;padding:0">CRM Mari Amaral</h2>
            <p style="color:{clr_sub};margin:0;font-size:0.83rem">
                Sistema de gestão de clientes
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        if users:
            username_input = st.text_input("Usuário", placeholder="seu_usuario", key="_user_input")
            senha_input    = st.text_input("Senha", type="password", placeholder="••••••••", key="_pass_input")
            if st.button("Entrar →", use_container_width=True, type="primary", key="_btn_login"):
                uname = username_input.strip().lower()
                if uname in users:
                    data = dict(users[uname])
                    if _verificar_credencial(senha_input, str(data.get("password", ""))):
                        st.session_state["_autenticado"] = True
                        st.session_state["_usuario"] = {
                            "username": uname,
                            "name":     data.get("name", uname),
                            "email":    data.get("email", ""),
                        }
                        st.rerun()
                    else:
                        st.error("Senha incorreta.")
                else:
                    st.error("Usuário não encontrado.")
        else:
            # Fallback senha única (legado)
            senha = st.text_input("Senha", type="password", placeholder="••••••••", key="_senha_input")
            if st.button("Entrar →", use_container_width=True, type="primary", key="_btn_login_leg"):
                if _verificar_credencial(senha, st.secrets.get("app_password", "maricrm2024")):
                    st.session_state["_autenticado"] = True
                    st.session_state["_usuario"] = {"name": "Admin", "username": "admin"}
                    st.rerun()
                else:
                    st.error("Senha incorreta.")


def verificar_senha() -> bool:
    """Verifica autenticação. Aplica CSS e controles de sidebar se autenticado."""
    if st.session_state.get("_autenticado"):
        st.markdown(get_css(), unsafe_allow_html=True)
        _sidebar_controles()
        return True

    st.markdown(get_css(), unsafe_allow_html=True)
    _tela_login()
    return False


# ── Sidebar utilitários ───────────────────────────────────────────────────────

def sidebar_periodo():
    from config import PERIODOS
    hoje = date.today()
    opcoes = PERIODOS + ["Período personalizado"]
    periodo = st.sidebar.selectbox("Período", opcoes, index=2)

    if periodo == "Período personalizado":
        d_ini = st.sidebar.date_input("De",  value=hoje - timedelta(days=90), max_value=hoje)
        d_fim = st.sidebar.date_input("Até", value=hoje,                      max_value=hoje)
        return str(d_ini), str(d_fim)

    return periodo_para_data(periodo), str(hoje)


def sidebar_lojas(df_lojas: pd.DataFrame | None = None):
    if df_lojas is not None and not df_lojas.empty:
        opcoes = ["Todas"] + sorted(df_lojas["loja"].dropna().unique().tolist())
        return st.sidebar.selectbox("Canal / Loja", opcoes)
    return "Todas"
