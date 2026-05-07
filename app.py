import streamlit as st
from utils import get_css, verificar_senha

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
bg_hero   = "linear-gradient(135deg, #F9F0FD 0%, #FDF5FF 100%)" if not dark else "linear-gradient(135deg, #16162A 0%, #1C1C34 100%)"
brd_hero  = "#EDD8F5" if not dark else "#2D2D52"
txt_main  = "#C85DA4" if not dark else "#D470B5"
txt_sub   = "#9B3DC4" if not dark else "#A860E0"
txt_desc  = "#666" if not dark else "#9090B0"

st.markdown(f"""
<div style="background:{bg_hero};border:1px solid {brd_hero};border-radius:20px;
            padding:2.2rem 2.5rem;margin-bottom:2rem;
            box-shadow:0 4px 24px rgba(139,47,201,0.1)">
    <div style="display:flex;align-items:center;gap:1.2rem">
        <div style="font-size:3rem;line-height:1">👗</div>
        <div>
            <h1 style="margin:0;padding:0;border:none;font-size:2rem;color:{txt_main}">
                CRM Mari Amaral
            </h1>
            <p style="margin:0.2rem 0 0;color:{txt_desc};font-size:0.95rem">
                Gestão inteligente de clientes · E-commerce + Loja Jardim América + Loja Bernardo Sayão
            </p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Cards de módulos ──────────────────────────────────────────────────────────
bg_card  = "white" if not dark else "#1A1A30"
brd_card = "#EDD8F5" if not dark else "#2D2D52"
shadow   = "0 2px 16px rgba(139,47,201,0.08)" if not dark else "0 2px 16px rgba(0,0,0,0.3)"
clr_icon = "#C85DA4"
clr_tit  = "#7B2FA8" if not dark else "#C870B8"
clr_desc = "#888" if not dark else "#7878A0"

MODULOS = [
    ("📊", "Visão Geral",     "KPIs de receita, pedidos, ticket médio e crescimento por canal"),
    ("🎯", "Matriz RFM",      "Segmentação automática de clientes por recência, frequência e valor"),
    ("📈", "Retenção",        "Cohort mensal de retenção e taxa de recompra por canal"),
    ("🏪", "Canais",          "Comparativo entre E-commerce, Jardim América e Bernardo Sayão"),
    ("👥", "Clientes",        "Base completa com busca, filtros avançados e ficha individual"),
    ("📤", "Exportação",      "Listas segmentadas para disparos via WhatsApp com filtros RFM"),
    ("🎂", "Aniversariantes", "Clientes aniversariantes do mês com envio automático pelo WhatsApp"),
]

cols = st.columns(3)
for i, (icon, titulo, descricao) in enumerate(MODULOS):
    with cols[i % 3]:
        st.markdown(f"""
        <div style="background:{bg_card};border:1px solid {brd_card};border-radius:16px;
                    padding:1.5rem 1.4rem;margin-bottom:1rem;
                    box-shadow:{shadow};
                    transition:transform 0.2s ease;cursor:default">
            <div style="font-size:2rem;margin-bottom:0.6rem">{icon}</div>
            <div style="font-weight:800;color:{clr_tit};font-size:1.05rem;margin-bottom:0.35rem">
                {titulo}
            </div>
            <div style="font-size:0.82rem;color:{clr_desc};line-height:1.5">{descricao}</div>
        </div>
        """, unsafe_allow_html=True)

# ── Dica de navegação ─────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.info("👈 Use o **menu lateral** para navegar entre os módulos. Os dados são atualizados automaticamente a cada hora (cache BigQuery).")
