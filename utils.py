import streamlit as st
import pandas as pd
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


CSS = """
<style>
[data-testid="stMetric"] {
    background: linear-gradient(135deg, #FDF0F8, #FFFFFF);
    border: 1px solid #E0C0D8;
    border-radius: 12px;
    padding: 1rem 1.2rem;
}
[data-testid="stMetricValue"] { color: #C85DA4 !important; font-weight: 700 !important; }
[data-testid="stMetricLabel"] { color: #888 !important; font-size: 0.82rem !important; }
div[data-testid="stSidebarContent"] { background: linear-gradient(180deg, #F8F0F5 0%, #fff 100%); }
</style>
"""


def verificar_senha() -> bool:
    """Retorna True se autenticado. Exibe tela de login caso contrário."""
    if st.session_state.get("_autenticado"):
        return True

    st.markdown(CSS, unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1, 1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("## 👗 CRM Mari Amaral")
        st.markdown("Digite a senha para acessar o sistema.")
        senha = st.text_input("Senha", type="password", key="_senha_input")
        if st.button("Entrar", use_container_width=True, type="primary"):
            senha_correta = st.secrets.get("app_password", "maricrm2024")
            if senha == senha_correta:
                st.session_state["_autenticado"] = True
                st.rerun()
            else:
                st.error("Senha incorreta.")
    return False


def sidebar_periodo():
    """Retorna (data_inicio: str, data_fim: str)."""
    from config import PERIODOS
    hoje = date.today()
    opcoes = PERIODOS + ["Período personalizado"]
    periodo = st.sidebar.selectbox("Período", opcoes, index=2)

    if periodo == "Período personalizado":
        d_ini = st.sidebar.date_input("De", value=hoje - timedelta(days=90), max_value=hoje)
        d_fim = st.sidebar.date_input("Até", value=hoje, max_value=hoje)
        return str(d_ini), str(d_fim)

    return periodo_para_data(periodo), str(hoje)


def sidebar_lojas(df_lojas: pd.DataFrame | None = None):
    if df_lojas is not None and not df_lojas.empty:
        opcoes = ["Todas"] + sorted(df_lojas["loja"].dropna().unique().tolist())
        return st.sidebar.selectbox("Canal / Loja", opcoes)
    return "Todas"
