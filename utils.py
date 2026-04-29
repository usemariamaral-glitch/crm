import streamlit as st
import pandas as pd
import google.auth
from google.cloud import bigquery
from datetime import date, timedelta


@st.cache_resource
def get_client():
    try:
        # Na nuvem (Streamlit Cloud): usa a chave de serviço salva nos secrets
        if "gcp_service_account" in st.secrets:
            from google.oauth2 import service_account
            credentials = service_account.Credentials.from_service_account_info(
                st.secrets["gcp_service_account"],
                scopes=["https://www.googleapis.com/auth/bigquery"],
            )
            return bigquery.Client(project="datalake-488518", credentials=credentials)

        # Local: usa o login do Google feito via gcloud
        credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/bigquery"]
        )
        return bigquery.Client(project="datalake-488518", credentials=credentials)

    except Exception as e:
        st.error(f"Erro de autenticação com o Google: {e}")
        st.info("**Solução local:** Abra o terminal e execute:\n\n`gcloud auth application-default login`")
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
    if not ddd or not tel:
        return ""
    d = str(ddd).strip().replace("(", "").replace(")", "").replace(" ", "")
    t = str(tel).strip().replace("-", "").replace(" ", "")
    return f"55{d}{t}"


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


def sidebar_periodo():
    from config import PERIODOS
    return st.sidebar.selectbox("Período", PERIODOS, index=2)


def sidebar_lojas(df_lojas: pd.DataFrame | None = None):
    if df_lojas is not None and not df_lojas.empty:
        opcoes = ["Todas"] + sorted(df_lojas["loja"].dropna().unique().tolist())
        return st.sidebar.selectbox("Canal / Loja", opcoes)
    return "Todas"
