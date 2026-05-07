import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from utils import run_query, fmt_num, sidebar_periodo, verificar_senha
from config import PEDIDOS, EXCLUIR_LOJAS, STATUS_FATURADO

st.set_page_config(page_title="Retenção | CRM", page_icon="📈", layout="wide")
if not verificar_senha():
    st.stop()
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
        documento,
        DATE_TRUNC(DATE(data_pedido), MONTH) AS mes_atividade
    FROM {PEDIDOS}
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

# ── Clientes novos vs recorrentes no período ──────────────────────────────────
st.subheader("Novos vs Recorrentes no Período")
st.markdown("""
**Como funciona:** De todas as clientes que compraram no período selecionado,
quantas eram **novas** (primeira compra de toda a vida delas) e quantas já eram
**clientes** (já tinham comprado antes do período)?
""")

SQL_RECOMPRA = f"""
WITH compras_periodo AS (
    SELECT DISTINCT documento, loja
    FROM {PEDIDOS}
    WHERE documento IS NOT NULL
      AND DATE(data_pedido) BETWEEN '{data_inicio}' AND '{data_fim}'
      {STATUS_FATURADO}
      {EXCLUIR_LOJAS}
),
primeira_compra_historica AS (
    SELECT documento, MIN(DATE(data_pedido)) AS primeira_compra
    FROM {PEDIDOS}
    WHERE documento IS NOT NULL
      {STATUS_FATURADO}
      {EXCLUIR_LOJAS}
    GROUP BY documento
)
SELECT
    COUNT(DISTINCT cp.documento)                                    AS total_compradores,
    COUNTIF(p.primeira_compra >= '{data_inicio}')                  AS clientes_novos,
    COUNTIF(p.primeira_compra < '{data_inicio}')                   AS clientes_retorno
FROM compras_periodo cp
JOIN primeira_compra_historica p USING (documento)
"""

df_rc = run_query(SQL_RECOMPRA)

if not df_rc.empty and df_rc.iloc[0].total_compradores > 0:
    r = df_rc.iloc[0]
    total = int(r.total_compradores)
    novos = int(r.clientes_novos)
    retorno = int(r.clientes_retorno)
    pct_novos   = novos / total * 100
    pct_retorno = retorno / total * 100

    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("Compraram no período",  fmt_num(total))
    col_m2.metric("Clientes novas",        fmt_num(novos),
                  delta=f"{pct_novos:.1f}% do total")
    col_m3.metric("Clientes recorrentes",  fmt_num(retorno),
                  delta=f"{pct_retorno:.1f}% do total")

    col_g1, col_g2 = st.columns(2)
    with col_g1:
        df_pizza = pd.DataFrame({
            "Tipo": ["Novas", "Recorrentes"],
            "Clientes": [novos, retorno],
        })
        fig_pizza = px.pie(
            df_pizza, values="Clientes", names="Tipo",
            color_discrete_sequence=["#8B2FC9", "#C85DA4"],
            title="Proporção no período",
        )
        fig_pizza.update_traces(textposition="inside", textinfo="percent+label+value")
        st.plotly_chart(fig_pizza, use_container_width=True)

    with col_g2:
        # Por canal
        SQL_RC_CANAL = f"""
        WITH compras_periodo AS (
            SELECT DISTINCT documento, loja
            FROM {PEDIDOS}
            WHERE documento IS NOT NULL
              AND DATE(data_pedido) BETWEEN '{data_inicio}' AND '{data_fim}'
              {STATUS_FATURADO}
              {EXCLUIR_LOJAS}
        ),
        primeira_historica AS (
            SELECT documento, MIN(DATE(data_pedido)) AS primeira_compra
            FROM {PEDIDOS}
            WHERE documento IS NOT NULL {STATUS_FATURADO} {EXCLUIR_LOJAS}
            GROUP BY documento
        )
        SELECT
            cp.loja,
            COUNTIF(p.primeira_compra >= '{data_inicio}') AS novas,
            COUNTIF(p.primeira_compra < '{data_inicio}')  AS recorrentes,
            COUNT(*) AS total
        FROM compras_periodo cp
        JOIN primeira_historica p USING (documento)
        GROUP BY cp.loja
        ORDER BY total DESC
        """
        df_canal = run_query(SQL_RC_CANAL)
        if not df_canal.empty:
            df_canal_melt = df_canal.melt(
                id_vars="loja", value_vars=["novas", "recorrentes"],
                var_name="Tipo", value_name="Clientes"
            )
            df_canal_melt["Tipo"] = df_canal_melt["Tipo"].map(
                {"novas": "Novas", "recorrentes": "Recorrentes"}
            )
            fig_canal = px.bar(
                df_canal_melt, x="loja", y="Clientes", color="Tipo",
                barmode="stack",
                color_discrete_map={"Novas": "#8B2FC9", "Recorrentes": "#C85DA4"},
                labels={"loja": "Canal", "Clientes": "Clientes"},
                title="Por canal",
            )
            fig_canal.update_layout(plot_bgcolor="white", legend_title="")
            st.plotly_chart(fig_canal, use_container_width=True)

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
    st.caption("Tempo médio que uma cliente leva para fazer a próxima compra no mesmo canal.")
