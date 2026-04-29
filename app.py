import streamlit as st
from utils import CSS

st.set_page_config(
    page_title="CRM Mari Amaral",
    page_icon="👗",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(CSS, unsafe_allow_html=True)

st.title("👗 CRM Mari Amaral")
st.markdown("**Gestão inteligente de clientes** — E-commerce + Loja Jardim América + Loja Bernardo Sayão")
st.divider()

modulos = [
    ("📊", "Visão Geral",      "KPIs de receita, pedidos e crescimento"),
    ("🎯", "Matriz RFM",       "Segmentação de clientes por comportamento"),
    ("📈", "Retenção",         "Cohort mensal e taxa de recompra"),
    ("🏪", "Canais",           "E-commerce vs Lojas Físicas e clientes omnichannel"),
    ("👥", "Clientes",         "Base completa com busca e filtros avançados"),
    ("📤", "Exportação",       "Listas segmentadas para disparos no WhatsApp"),
    ("🎂", "Aniversariantes",  "Gestão de aniversários por mês"),
]

cols = st.columns(4)
for i, (icon, titulo, descricao) in enumerate(modulos):
    with cols[i % 4]:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#FDF0F8,#fff);border:1px solid #E0C0D8;
                    border-radius:12px;padding:1.2rem;margin-bottom:1rem;text-align:center;min-height:120px">
            <div style="font-size:1.8rem">{icon}</div>
            <div style="font-weight:700;color:#C85DA4;margin:.3rem 0">{titulo}</div>
            <div style="font-size:.82rem;color:#888">{descricao}</div>
        </div>
        """, unsafe_allow_html=True)

st.divider()
st.info("👈 **Use o menu lateral para navegar entre os módulos.** Os dados são atualizados automaticamente do BigQuery (cache de 1 hora).")
