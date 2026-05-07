import streamlit as st
from utils import verificar_senha

st.set_page_config(
    page_title="CRM Mari Amaral",
    page_icon="👗",
    layout="wide",
    initial_sidebar_state="expanded",
)

if not verificar_senha():
    st.stop()

dark = st.session_state.get("dark_mode", False)

# ── Header ────────────────────────────────────────────────────────────────────
bg_hero  = "linear-gradient(135deg, #1d3c4d 0%, #2d7a94 100%)"
clr_icon = "rgba(255,255,255,0.85)"
clr_h    = "white"
clr_sub  = "rgba(255,255,255,0.75)"

st.markdown(f"""
<div style="background:{bg_hero};border-radius:18px;
            padding:2rem 2.5rem;margin-bottom:2rem;
            box-shadow:0 4px 24px rgba(29,60,77,0.25)">
    <div style="display:flex;align-items:center;gap:1.2rem">
        <div style="font-size:2.8rem;line-height:1">👗</div>
        <div>
            <h1 style="margin:0;padding:0;border:none;font-size:1.9rem;
                        color:{clr_h};font-weight:800;letter-spacing:-0.02em">
                CRM Mari Amaral
            </h1>
            <p style="margin:0.25rem 0 0;color:{clr_sub};font-size:0.9rem">
                Gestão inteligente de clientes · E-commerce + Loja Jardim América + Loja Bernardo Sayão
            </p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Cards de módulos ──────────────────────────────────────────────────────────
bg_card  = "#0F2030" if dark else "white"
brd_card = "#1E3A50" if dark else "#C8D8E4"
shadow   = "0 2px 16px rgba(0,0,0,0.3)" if not dark else "0 2px 16px rgba(0,0,0,0.4)"
clr_tit  = "#5AAAC8" if dark else "#1d3c4d"
clr_desc = "#4A7A8A" if dark else "#6B8A9A"
clr_icon_card = "#C85DA4"

MODULOS = [
    ("📊", "Visão Geral",     "KPIs de receita, pedidos, ticket médio e crescimento por canal"),
    ("🎯", "Matriz RFM",      "Segmentação automática de clientes por recência, frequência e valor"),
    ("📈", "Retenção",        "Cohort mensal de retenção e taxa de recompra por canal"),
    ("🏪", "Canais",          "Comparativo entre E-commerce, Jardim América e Bernardo Sayão"),
    ("👥", "Clientes",        "Base completa com busca, filtros avançados e ficha individual"),
    ("📤", "Exportação",      "Listas segmentadas para disparos via WhatsApp com filtros RFM"),
    ("🎂", "Aniversariantes", "Clientes aniversariantes do mês com envio automático de mensagem"),
]

cols = st.columns(3)
for i, (icon, titulo, descricao) in enumerate(MODULOS):
    with cols[i % 3]:
        st.markdown(f"""
        <div style="background:{bg_card};border:1px solid {brd_card};border-radius:16px;
                    padding:1.5rem 1.4rem;margin-bottom:1rem;
                    box-shadow:{shadow}">
            <div style="font-size:2rem;margin-bottom:0.55rem">{icon}</div>
            <div style="font-weight:800;color:{clr_tit};font-size:1rem;margin-bottom:0.35rem">
                {titulo}
            </div>
            <div style="font-size:0.82rem;color:{clr_desc};line-height:1.5">{descricao}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
st.info("👈 Use o **menu lateral** para navegar entre os módulos. Os dados são atualizados automaticamente a cada hora.")
