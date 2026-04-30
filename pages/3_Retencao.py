import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from utils import run_query, fmt_num, CSS, sidebar_periodo, verificar_senha
from config import PEDIDOS, EXCLUIR_LOJAS, STATUS_FATURADO

st.set_page_config(page_title="Retenção | CRM", page_icon="📈", layout="wide")
if not verificar_senha():
    st.stop()
st.markdown(CSS, unsafe_allow_html=True)
st.title("📈 Retenção & Recompra")

with st.sidebar:
    st.header("Filtros")
    data_inicio, data_fim = sidebar_periodo()

base_where = f"""
    WHERE documento IS NOT NULL
      AND DATE(data_pedido) BETWEEN '{data_inicio}' AND '{data_fim}'
      {STATUS_FATURADO}
      {EXCLUIR_LOJAS}
"""

# ── Cohort de retenção ────────────────────────────────────────────────────────
SQL_COHORT = f"""
WITH primeira_compra AS (
    SELECT
        documento,
        DATE_TRUNC(DATE(MIN(data_pedido)), MONTH) AS cohort_mes
    FROM {PEDIDOS}
    {base_where}
    GROUP BY documento
),
atividade AS (
    SELECT DISTINCT
        p.documento,
        DATE_TRUNC(DATE(p.data_pedido), MONTH) AS mes_atividade
    FROM {PEDIDOS} p
    {base_where}
),
cohort_data AS (
    SELECT
        pc.cohort_mes,
        DATE_DIFF(a.mes_atividade, pc.cohort_mes, MONTH) AS periodo,
        COUNT(DISTINCT a.documento) AS clientes_ativos
    FROM primeira_compra pc
    JOIN atividade a USING (documento)
    WHERE a.mes_atividade >= pc.cohort_mes
    GROUP BY 1, 2
),
cohort_size AS (
    SELECT cohort_mes, COUNT(*) AS total
    FROM primeira_compra
    GROUP BY 1
)
SELECT
    cd.cohort_mes,
    cd.periodo,
    cd.clientes_ativos,
    cs.total AS cohort_size,
    ROUND(cd.clientes_ativos / cs.total * 100, 1) AS taxa_retencao
FROM cohort_data cd
JOIN cohort_size cs USING (cohort_mes)
ORDER BY 1, 2
"""

with st.spinner("Calculando cohort de retenção..."):
    df_cohort = run_query(SQL_COHORT)

if df_cohort.empty:
    st.warning("Sem dados suficientes para o período selecionado.")
    st.stop()

df_cohort["cohort_mes"] = pd.to_datetime(df_cohort["cohort_mes"])
df_cohort["mes_label"]  = df_cohort["cohort_mes"].dt.strftime("%b/%Y")

st.subheader("Heatmap de Retenção por Cohort")
st.markdown("Percentual de clientes que voltaram a comprar em cada mês após a primeira compra.")

pivot = df_cohort.pivot_table(
    index="mes_label", columns="periodo", values="taxa_retencao"
)
pivot = pivot.sort_index(key=lambda x: pd.to_datetime(x, format="%b/%Y"))

fig_heat = go.Figure(go.Heatmap(
    z=pivot.values,
    x=[f"Mês {int(c)}" for c in pivot.columns],
    y=pivot.index.tolist(),
    colorscale=[[0, "#F8F0F5"], [0.5, "#C85DA4"], [1, "#4A0A5C"]],
    text=pivot.values.round(1),
    texttemplate="%{text}%",
    hoverongaps=False,
    showscale=True,
    colorbar=dict(title="Retenção %"),
))
fig_heat.update_layout(
    xaxis_title="Período após primeira compra",
    yaxis_title="Cohort (mês de entrada)",
    height=400,
)
st.plotly_chart(fig_heat, use_container_width=True)

st.divider()

# ── Taxa de recompra ──────────────────────────────────────────────────────────
col_l, col_r = st.columns(2)

with col_l:
    st.subheader("Taxa de Recompra Geral")
    df_recompra = run_query(f"""
        WITH pedidos_por_cliente AS (
            SELECT
                documento,
                COUNT(DISTINCT pedido_id) AS total_pedidos
            FROM {PEDIDOS}
            {base_where}
            GROUP BY 1
        )
        SELECT
            CASE
                WHEN total_pedidos = 1 THEN '1 compra (único)'
                WHEN total_pedidos = 2 THEN '2 compras'
                WHEN total_pedidos BETWEEN 3 AND 5 THEN '3–5 compras'
                WHEN total_pedidos BETWEEN 6 AND 10 THEN '6–10 compras'
                ELSE '11+ compras'
            END AS faixa,
            COUNT(*) AS clientes
        FROM pedidos_por_cliente
        GROUP BY 1
        ORDER BY MIN(total_pedidos)
    """)
    if not df_recompra.empty:
        total = df_recompra["clientes"].sum()
        recompram = df_recompra[df_recompra["faixa"] != "1 compra (único)"]["clientes"].sum()
        taxa = recompram / total * 100 if total > 0 else 0
        st.metric("Taxa de Recompra", f"{taxa:.1f}%", help="% de clientes que compraram mais de 1 vez")
        fig_rc = px.bar(
            df_recompra, x="faixa", y="clientes",
            color_discrete_sequence=["#C85DA4"],
            labels={"faixa": "Faixa de Compras", "clientes": "Clientes"},
        )
        fig_rc.update_layout(plot_bgcolor="white")
        st.plotly_chart(fig_rc, use_container_width=True)

with col_r:
    st.subheader("Recompra por Canal")
    df_rc_canal = run_query(f"""
        WITH pedidos_por_cliente AS (
            SELECT
                documento,
                loja,
                COUNT(DISTINCT pedido_id) AS total_pedidos
            FROM {PEDIDOS}
            {base_where}
            GROUP BY 1, 2
        )
        SELECT
            loja,
            COUNTIF(total_pedidos > 1) AS recompraram,
            COUNT(*) AS total_clientes,
            ROUND(COUNTIF(total_pedidos > 1) / COUNT(*) * 100, 1) AS taxa_recompra
        FROM pedidos_por_cliente
        GROUP BY 1
        ORDER BY 4 DESC
    """)
    if not df_rc_canal.empty:
        fig_rc2 = px.bar(
            df_rc_canal, x="loja", y="taxa_recompra",
            color_discrete_sequence=["#8B2FC9"],
            labels={"loja": "Canal/Loja", "taxa_recompra": "Taxa de Recompra (%)"},
            text="taxa_recompra",
        )
        fig_rc2.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig_rc2.update_layout(plot_bgcolor="white", yaxis_range=[0, 100])
        st.plotly_chart(fig_rc2, use_container_width=True)

st.divider()

# ── Intervalo médio entre compras ─────────────────────────────────────────────
st.subheader("Intervalo Médio entre Compras (dias)")
df_intv = run_query(f"""
    WITH datas AS (
        SELECT
            documento,
            loja,
            DATE(data_pedido) AS dt,
            LAG(DATE(data_pedido)) OVER (PARTITION BY documento ORDER BY data_pedido) AS dt_anterior
        FROM {PEDIDOS}
        {base_where}
    )
    SELECT
        loja,
        ROUND(AVG(DATE_DIFF(dt, dt_anterior, DAY)), 0) AS intervalo_medio_dias,
        COUNT(*) AS pares
    FROM datas
    WHERE dt_anterior IS NOT NULL
    GROUP BY 1
    ORDER BY 2
""")
if not df_intv.empty:
    fig_intv = px.bar(
        df_intv, x="loja", y="intervalo_medio_dias",
        color_discrete_sequence=["#E8A0D0"],
        labels={"loja": "Canal/Loja", "intervalo_medio_dias": "Dias entre compras"},
        text="intervalo_medio_dias",
    )
    fig_intv.update_traces(texttemplate="%{text:.0f} dias", textposition="outside")
    fig_intv.update_layout(plot_bgcolor="white")
    st.plotly_chart(fig_intv, use_container_width=True)
    st.caption("Tempo médio que um cliente leva para fazer a próxima compra no mesmo canal.")
