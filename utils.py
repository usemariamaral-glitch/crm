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
        "Últimos 30 dias":   str(hoje - timedelta(days=30)),
        "Últimos 90 dias":   str(hoje - timedelta(days=90)),
        "Últimos 12 meses":  str(hoje.replace(year=hoje.year - 1)),
        "Este ano":          str(hoje.replace(month=1, day=1)),
        "Tudo":              "2000-01-01",
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

CSS_LIGHT = """
<style>
/* ═══ BASE ═══ */
.stApp { background: #F7F3FA !important; }
.block-container { padding-top: 1.8rem !important; padding-bottom: 2rem !important; }

/* ═══ SIDEBAR ═══ */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #EEE4F6 0%, #F5EFF9 40%, #FAF7FC 100%) !important;
    border-right: 1px solid #DDD0EC !important;
}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    color: #8B2FC9 !important;
    font-size: 0.95rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.04em !important;
    text-transform: uppercase !important;
    border-bottom: none !important;
    margin-bottom: 0.6rem !important;
}

/* ═══ METRIC CARDS ═══ */
[data-testid="stMetric"] {
    background: white !important;
    border: 1px solid #EDD8F5 !important;
    border-radius: 16px !important;
    padding: 1.1rem 1.4rem !important;
    box-shadow: 0 2px 16px rgba(139,47,201,0.07) !important;
    position: relative !important;
    overflow: hidden !important;
    transition: transform 0.2s ease, box-shadow 0.2s ease !important;
}
[data-testid="stMetric"]::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, #C85DA4, #8B2FC9);
    border-radius: 3px 3px 0 0;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-3px) !important;
    box-shadow: 0 8px 28px rgba(200,93,164,0.18) !important;
}
[data-testid="stMetricValue"] {
    color: #C85DA4 !important;
    font-weight: 800 !important;
    font-size: 1.45rem !important;
    letter-spacing: -0.01em !important;
}
[data-testid="stMetricLabel"] {
    color: #9B8AAA !important;
    font-size: 0.72rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.07em !important;
}
[data-testid="stMetricDelta"] { font-size: 0.8rem !important; }

/* ═══ HEADINGS ═══ */
h1 {
    color: #C85DA4 !important;
    font-weight: 800 !important;
    font-size: 1.75rem !important;
    letter-spacing: -0.02em !important;
    padding-bottom: 0.5rem !important;
    border-bottom: 2px solid #EDD8F5 !important;
    margin-bottom: 1.4rem !important;
}
h2 { color: #7B2FA8 !important; font-weight: 700 !important; }
h3 { color: #9B3DC4 !important; font-weight: 600 !important; }

/* ═══ PRIMARY BUTTON ═══ */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #C85DA4 0%, #8B2FC9 100%) !important;
    border: none !important;
    color: white !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    padding: 0.55rem 1.5rem !important;
    box-shadow: 0 4px 14px rgba(200,93,164,0.3) !important;
    transition: all 0.2s ease !important;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 6px 20px rgba(200,93,164,0.45) !important;
    transform: translateY(-1px) !important;
}
.stButton > button[kind="secondary"] {
    border-radius: 10px !important;
    border: 1.5px solid #DDD0EC !important;
    color: #7B2FA8 !important;
    font-weight: 600 !important;
    transition: all 0.2s ease !important;
}
.stButton > button[kind="secondary"]:hover {
    border-color: #C85DA4 !important;
    background: #FBF5FF !important;
}

/* ═══ INPUTS ═══ */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input {
    border-radius: 10px !important;
    border: 1.5px solid #DDD0EC !important;
    transition: all 0.2s ease !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus {
    border-color: #C85DA4 !important;
    box-shadow: 0 0 0 3px rgba(200,93,164,0.12) !important;
}

/* ═══ SELECT / MULTISELECT ═══ */
[data-testid="stSelectbox"] > div > div,
[data-testid="stMultiSelect"] > div > div {
    border-radius: 10px !important;
    border-color: #DDD0EC !important;
}

/* ═══ DATAFRAME ═══ */
[data-testid="stDataFrame"] {
    border-radius: 14px !important;
    overflow: hidden !important;
    box-shadow: 0 2px 10px rgba(139,47,201,0.08) !important;
    border: 1px solid #EDD8F5 !important;
}

/* ═══ PLOTLY CHARTS ═══ */
[data-testid="stPlotlyChart"] {
    border-radius: 16px !important;
    overflow: hidden !important;
    box-shadow: 0 2px 14px rgba(0,0,0,0.06) !important;
    background: white !important;
    border: 1px solid #EDD8F5 !important;
    padding: 0.2rem !important;
}

/* ═══ EXPANDERS ═══ */
details {
    border: 1.5px solid #EDD8F5 !important;
    border-radius: 14px !important;
    overflow: hidden !important;
}
details summary {
    background: linear-gradient(135deg, #FBF5FF, #fff) !important;
    color: #8B2FC9 !important;
    font-weight: 600 !important;
    padding: 0.8rem 1rem !important;
}

/* ═══ ALERTS ═══ */
[data-testid="stAlert"] { border-radius: 12px !important; }

/* ═══ DIVIDER ═══ */
hr { border-color: #EDD8F5 !important; opacity: 0.9 !important; }

/* ═══ DOWNLOAD BUTTON ═══ */
[data-testid="stDownloadButton"] button {
    border-radius: 10px !important;
    border: 2px solid #C85DA4 !important;
    color: #C85DA4 !important;
    background: white !important;
    font-weight: 700 !important;
    transition: all 0.2s ease !important;
}
[data-testid="stDownloadButton"] button:hover {
    background: linear-gradient(135deg, #C85DA4, #8B2FC9) !important;
    color: white !important;
    border-color: transparent !important;
    box-shadow: 0 4px 14px rgba(200,93,164,0.3) !important;
}

/* ═══ TABS ═══ */
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: #C85DA4 !important;
    border-bottom-color: #C85DA4 !important;
}

/* ═══ RADIO ═══ */
[data-testid="stRadio"] label { font-weight: 500 !important; }
</style>
"""

CSS_DARK = """
<style>
/* ═══ BASE ═══ */
.stApp { background: #0E0E1C !important; }
.block-container { padding-top: 1.8rem !important; padding-bottom: 2rem !important; }
body, p, span, div, label, li, .stMarkdown { color: #DDD8F0 !important; }

/* ═══ SIDEBAR ═══ */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #16162A 0%, #191928 100%) !important;
    border-right: 1px solid #2A2A48 !important;
}
section[data-testid="stSidebar"] * { color: #C8C4E0 !important; }
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    color: #C870B8 !important;
    font-size: 0.95rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.04em !important;
    text-transform: uppercase !important;
    border-bottom: none !important;
}

/* ═══ METRIC CARDS ═══ */
[data-testid="stMetric"] {
    background: #1A1A30 !important;
    border: 1px solid #2D2D52 !important;
    border-radius: 16px !important;
    padding: 1.1rem 1.4rem !important;
    box-shadow: 0 2px 16px rgba(0,0,0,0.3) !important;
    position: relative !important;
    overflow: hidden !important;
    transition: transform 0.2s ease, box-shadow 0.2s ease !important;
}
[data-testid="stMetric"]::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, #D470B5, #9B4FD9);
    border-radius: 3px 3px 0 0;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-3px) !important;
    box-shadow: 0 8px 28px rgba(200,93,164,0.25) !important;
}
[data-testid="stMetricValue"] {
    color: #D470B5 !important;
    font-weight: 800 !important;
    font-size: 1.45rem !important;
}
[data-testid="stMetricLabel"] {
    color: #7878A0 !important;
    font-size: 0.72rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.07em !important;
}

/* ═══ HEADINGS ═══ */
h1 {
    color: #D470B5 !important;
    font-weight: 800 !important;
    font-size: 1.75rem !important;
    letter-spacing: -0.02em !important;
    padding-bottom: 0.5rem !important;
    border-bottom: 2px solid #2D2D52 !important;
    margin-bottom: 1.4rem !important;
}
h2 { color: #A860E0 !important; font-weight: 700 !important; }
h3 { color: #C070D0 !important; font-weight: 600 !important; }

/* ═══ PRIMARY BUTTON ═══ */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #C85DA4 0%, #8B2FC9 100%) !important;
    border: none !important;
    color: white !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    box-shadow: 0 4px 14px rgba(200,93,164,0.35) !important;
    transition: all 0.2s ease !important;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 6px 20px rgba(200,93,164,0.5) !important;
    transform: translateY(-1px) !important;
}
.stButton > button[kind="secondary"] {
    border-radius: 10px !important;
    background: #1A1A30 !important;
    border: 1.5px solid #3A3A60 !important;
    color: #C8C4E0 !important;
    font-weight: 600 !important;
    transition: all 0.2s ease !important;
}
.stButton > button[kind="secondary"]:hover {
    border-color: #D470B5 !important;
    background: #222240 !important;
}

/* ═══ INPUTS ═══ */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input {
    border-radius: 10px !important;
    border: 1.5px solid #3A3A60 !important;
    background: #1A1A30 !important;
    color: #DDD8F0 !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus {
    border-color: #D470B5 !important;
    box-shadow: 0 0 0 3px rgba(212,112,181,0.18) !important;
}

/* ═══ SELECT / MULTISELECT ═══ */
[data-testid="stSelectbox"] > div > div,
[data-testid="stMultiSelect"] > div > div {
    border-radius: 10px !important;
    border-color: #3A3A60 !important;
    background: #1A1A30 !important;
}

/* ═══ DATAFRAME ═══ */
[data-testid="stDataFrame"] {
    border-radius: 14px !important;
    overflow: hidden !important;
    box-shadow: 0 2px 10px rgba(0,0,0,0.35) !important;
    border: 1px solid #2D2D52 !important;
}

/* ═══ PLOTLY CHARTS ═══ */
[data-testid="stPlotlyChart"] {
    border-radius: 16px !important;
    overflow: hidden !important;
    box-shadow: 0 2px 14px rgba(0,0,0,0.35) !important;
    background: #1A1A30 !important;
    border: 1px solid #2D2D52 !important;
    padding: 0.2rem !important;
}

/* ═══ EXPANDERS ═══ */
details {
    border: 1.5px solid #2D2D52 !important;
    border-radius: 14px !important;
    overflow: hidden !important;
    background: #1A1A30 !important;
}
details summary {
    background: #1E1E38 !important;
    color: #D470B5 !important;
    font-weight: 600 !important;
    padding: 0.8rem 1rem !important;
}

/* ═══ ALERTS ═══ */
[data-testid="stAlert"] { border-radius: 12px !important; }

/* ═══ DIVIDER ═══ */
hr { border-color: #2D2D52 !important; opacity: 0.9 !important; }

/* ═══ DOWNLOAD BUTTON ═══ */
[data-testid="stDownloadButton"] button {
    border-radius: 10px !important;
    border: 2px solid #D470B5 !important;
    color: #D470B5 !important;
    background: #1A1A30 !important;
    font-weight: 700 !important;
    transition: all 0.2s ease !important;
}
[data-testid="stDownloadButton"] button:hover {
    background: linear-gradient(135deg, #C85DA4, #8B2FC9) !important;
    color: white !important;
    border-color: transparent !important;
}

/* ═══ CHECKBOX ═══ */
[data-testid="stCheckbox"] label { color: #DDD8F0 !important; }

/* ═══ RADIO ═══ */
[data-testid="stRadio"] label { color: #DDD8F0 !important; font-weight: 500 !important; }

/* ═══ TABS ═══ */
[data-testid="stTabs"] [role="tab"] { color: #9090B0 !important; }
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: #D470B5 !important;
    border-bottom-color: #D470B5 !important;
}
</style>
"""

# Alias para compatibilidade (pages que ainda importam CSS)
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
    dark = st.session_state.get("dark_mode", False)
    nome = st.session_state.get("_usuario", {}).get("name", "Usuário")
    cor_card = "rgba(200,93,164,0.15)" if not dark else "rgba(200,93,164,0.12)"
    cor_texto = "#C85DA4" if not dark else "#D470B5"
    cor_sub = "#888" if not dark else "#9090B0"

    with st.sidebar:
        st.markdown(f"""
        <div style="background:{cor_card};border:1px solid rgba(200,93,164,0.25);
                    border-radius:12px;padding:0.65rem 1rem;margin-bottom:0.7rem">
            <div style="font-size:0.7rem;color:{cor_sub};font-weight:600;
                        text-transform:uppercase;letter-spacing:0.05em">Logado como</div>
            <div style="font-weight:700;color:{cor_texto};font-size:0.95rem;margin-top:2px">
                👤 {nome}
            </div>
        </div>
        """, unsafe_allow_html=True)

        col_t, col_s = st.columns(2)
        with col_t:
            icone = "☀️" if dark else "🌙"
            label = "Claro" if dark else "Escuro"
            if st.button(f"{icone} {label}", use_container_width=True, key="_btn_tema"):
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
    bg_card  = "#1E1E38" if dark else "white"
    brd      = "#2D2D52" if dark else "#EDD8F5"
    txt_sub  = "#9090B0" if dark else "#AAA"

    users = dict(st.secrets.get("users", {}))

    _, col, _ = st.columns([1, 1.1, 1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(f"""
        <div style="background:{bg_card};border:1px solid {brd};border-radius:22px;
                    padding:2.5rem 2rem 2rem;
                    box-shadow:0 12px 48px rgba(139,47,201,0.18);text-align:center">
            <div style="font-size:3.2rem;line-height:1.1;margin-bottom:0.6rem">👗</div>
            <h2 style="color:#C85DA4;margin:0 0 0.25rem;font-size:1.55rem;font-weight:800">
                CRM Mari Amaral
            </h2>
            <p style="color:{txt_sub};margin:0;font-size:0.85rem">
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
            # Fallback: senha única (legado)
            senha = st.text_input("Senha", type="password", placeholder="••••••••", key="_senha_input")
            if st.button("Entrar →", use_container_width=True, type="primary", key="_btn_login_leg"):
                if _verificar_credencial(senha, st.secrets.get("app_password", "maricrm2024")):
                    st.session_state["_autenticado"] = True
                    st.session_state["_usuario"] = {"name": "Admin", "username": "admin"}
                    st.rerun()
                else:
                    st.error("Senha incorreta.")


def verificar_senha() -> bool:
    """Verifica autenticação. Retorna True se autenticado."""
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
