import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from utils import run_query, fmt_brl, fmt_num, CSS, periodo_para_data, sidebar_periodo
from config import PEDIDOS, CLIENTES

st.set_page_config(page_title="Canais | CRM", page_icon="🏪", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)
st.title("🏪 Análise de Canais")
st.markdown("Comparativo entre **E-commerce**, **Loja Jardim América** e **Loja Bernardo Sayão**.")

with st.sidebar:
    st.header("Filtros")
    periodo = sidebar_periodo()
    data_inicio = periodo_para_data(periodo)

filtro = f"AND DATE(data_pedido) >= '{data_inicio}'"

# ── KPIs por canal ────────────────────────────────────────────────────────────
SQL_CANAIS = f"""
    SELECT
        loja,
        origem_sistema,
        COUNT(DISTINCT documento)  AS clientes_unicos,
        COUNT(DISTINCT pedido_id)  AS total_pedidos,
        SUM(total_pedido)          AS receita_total,
        AVG(total_pedido)          AS ticket_medio,
        SUM(desconto)              AS total_desconto
    FROM {PEDIDOS}
    WHERE documento IS NOT NULL {filtro}
    GROUP BY 1, 2
    ORDER BY receita_total DESC
"""
df_canais = run_query(SQL_CANAIS)

if df_canais.empty:
    st.warning("Sem dados para o período selecionado.")
    st.stop()

st.subheader("KPIs por Canal")
for _, row in df_canais.iterrows():
    with st.expander(f"📍 {row['loja']} ({row['origem_sistema']})", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Clientes Únicos", fmt_num(row.clientes_unicos))
        c2.metric("Pedidos",         fmt_num(row.total_pedidos))
        c3.metric("Receita",         fmt_brl(row.receita_total))
        c4.metric("Ticket Médio",    fmt_brl(row.ticket_medio))

st.divider()

# ── Comparativo visual ────────────────────────────────────────────────────────
col_l, col_r = st.columns(2)

with col_l:
    st.subheader("Receita por Canal")
    fig = px.bar(
        df_canais, x="loja", y="receita_total",
        color="loja", color_discrete_sequence=["#C85DA4", "#8B2FC9", "#E8A0D0"],
        labels={"loja": "Canal", "receita_total": "Receita Total (R$)"},
        text="receita_total",
    )
    fig.update_traces(texttemplate="R$ %{text:,.0f}", textposition="outside")
    fig.update_layout(plot_bgcolor="white", showlegend=False)
    fig.update_yaxes(tickprefix="R$ ")
    st.plotly_chart(fig, use_container_width=True)

with col_r:
    st.subheader("Clientes Únicos por Canal")
    fig2 = px.bar(
        df_canais, x="loja", y="clientes_unicos",
        color="loja", color_discrete_sequence=["#C85DA4", "#8B2FC9", "#E8A0D0"],
        labels={"loja": "Canal", "clientes_unicos": "Clientes Únicos"},
        text="clientes_unicos",
    )
    fig2.update_traces(texttemplate="%{text:,}", textposition="outside")
    fig2.update_layout(plot_bgcolor="white", showlegend=False)
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ── Evolução mensal por canal ─────────────────────────────────────────────────
st.subheader("Evolução Mensal por Canal")
df_mensal = run_query(f"""
    SELECT
        DATE_TRUNC(DATE(data_pedido), MONTH) AS mes,
        loja,
        SUM(total_pedido)         AS receita,
        COUNT(DISTINCT pedido_id) AS pedidos
    FROM {PEDIDOS}
    WHERE documento IS NOT NULL {filtro}
    GROUP BY 1, 2
    ORDER BY 1
""")
if not df_mensal.empty:
    df_mensal["mes"] = pd.to_datetime(df_mensal["mes"])
    metrica = st.radio("Métrica", ["Receita", "Pedidos"], horizontal=True)
    col_y = "receita" if metrica == "Receita" else "pedidos"
    fig3 = px.line(
        df_mensal, x="mes", y=col_y, color="loja",
        markers=True,
        color_discrete_sequence=["#C85DA4", "#8B2FC9", "#E8A0D0"],
        labels={"mes": "Mês", col_y: metrica, "loja": "Canal"},
    )
    fig3.update_layout(plot_bgcolor="white", hovermode="x unified", legend_title="")
    if metrica == "Receita":
        fig3.update_yaxes(tickprefix="R$ ")
    st.plotly_chart(fig3, use_container_width=True)

st.divider()

# ── Clientes Omnichannel ──────────────────────────────────────────────────────
st.subheader("🔀 Análise Omnichannel")
st.markdown("Clientes que compraram em **mais de um canal**.")

SQL_OMNI = f"""
    WITH canais_por_cliente AS (
        SELECT
            documento,
            COUNT(DISTINCT origem_sistema) AS qtd_sistemas,
            COUNT(DISTINCT loja)           AS qtd_lojas,
            STRING_AGG(DISTINCT loja, ' + ' ORDER BY loja) AS lojas_usadas
        FROM {PEDIDOS}
        WHERE documento IS NOT NULL {filtro}
        GROUP BY documento
    )
    SELECT
        CASE
            WHEN qtd_sistemas > 1 THEN 'Omnichannel (online + loja)'
            WHEN lojas_usadas LIKE '%+%' THEN 'Multi-loja (2 lojas físicas)'
            ELSE lojas_usadas
        END AS perfil,
        COUNT(*) AS clientes
    FROM canais_por_cliente
    GROUP BY 1
    ORDER BY 2 DESC
"""
df_omni = run_query(SQL_OMNI)

col_a, col_b = st.columns([1, 2])

with col_a:
    if not df_omni.empty:
        total_omni = df_omni[df_omni["perfil"].str.contains("Omnichannel|Multi", na=False)]["clientes"].sum()
        total_geral = df_omni["clientes"].sum()
        st.metric("Clientes Omnichannel", fmt_num(total_omni))
        st.metric("% da Base Total",      f"{total_omni / total_geral * 100:.1f}%" if total_geral else "0%")
        st.markdown("---")
        st.dataframe(
            df_omni.rename(columns={"perfil": "Perfil", "clientes": "Clientes"}),
            hide_index=True, use_container_width=True,
        )

with col_b:
    if not df_omni.empty:
        fig4 = px.pie(
            df_omni, values="clientes", names="perfil",
            color_discrete_sequence=["#C85DA4", "#8B2FC9", "#E8A0D0", "#F4C6E7"],
            title="Distribuição por Perfil de Canal",
        )
        fig4.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig4, use_container_width=True)

st.divider()

# ── Sequência de canais (Primeira compra → Última compra) ─────────────────────
st.subheader("📍 Jornada: Primeiro Canal → Último Canal")
st.markdown("Mostra como os clientes transitam entre canais ao longo do tempo.")

SQL_JORNADA = f"""
    WITH ranked AS (
        SELECT
            documento,
            loja,
            data_pedido,
            ROW_NUMBER() OVER (PARTITION BY documento ORDER BY data_pedido ASC)  AS rn_first,
            ROW_NUMBER() OVER (PARTITION BY documento ORDER BY data_pedido DESC) AS rn_last
        FROM {PEDIDOS}
        WHERE documento IS NOT NULL {filtro}
    ),
    first_last AS (
        SELECT
            documento,
            MAX(CASE WHEN rn_first = 1 THEN loja END) AS primeiro_canal,
            MAX(CASE WHEN rn_last  = 1 THEN loja END) AS ultimo_canal
        FROM ranked
        GROUP BY documento
    )
    SELECT
        primeiro_canal AS origem,
        ultimo_canal   AS destino,
        COUNT(*)       AS clientes
    FROM first_last
    WHERE primeiro_canal IS NOT NULL AND ultimo_canal IS NOT NULL
    GROUP BY 1, 2
    ORDER BY 3 DESC
"""
df_jornada = run_query(SQL_JORNADA)

if not df_jornada.empty:
    lojas    = sorted(set(df_jornada["origem"].tolist() + df_jornada["destino"].tolist()))
    node_idx = {loja: i for i, loja in enumerate(lojas)}

    fig5 = go.Figure(go.Sankey(
        node=dict(
            pad=20, thickness=20,
            label=lojas,
            color=["#C85DA4", "#8B2FC9", "#E8A0D0"][:len(lojas)],
        ),
        link=dict(
            source=[node_idx[o] for o in df_jornada["origem"]],
            target=[node_idx[d] for d in df_jornada["destino"]],
            value=df_jornada["clientes"].tolist(),
        ),
    ))
    fig5.update_layout(title_text="Fluxo de Canais (1ª compra → última compra)", height=350)
    st.plotly_chart(fig5, use_container_width=True)
    st.dataframe(
        df_jornada.rename(columns={"origem": "1º Canal", "destino": "Último Canal", "clientes": "Clientes"}),
        hide_index=True, use_container_width=True,
    )
