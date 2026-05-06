import streamlit as st
import plotly.express as px
import pandas as pd
from utils import run_query, fmt_brl, fmt_num, CSS, sidebar_periodo, verificar_senha
from config import PEDIDOS, ITENS, PAGAMENTOS, EXCLUIR_LOJAS, STATUS_FATURADO

st.set_page_config(page_title="Visão Geral | CRM", page_icon="📊", layout="wide")
if not verificar_senha():
    st.stop()
st.markdown(CSS, unsafe_allow_html=True)
st.title("📊 Visão Geral")

with st.sidebar:
    st.header("Filtros")
    data_inicio, data_fim = sidebar_periodo()
    st.divider()
    canal_opcoes = ["Todos", "E-commerce", "Loja Jardim América", "Loja Bernardo Sayão"]
    canal_sel = st.selectbox("Canal", canal_opcoes)

canal_sql = ""
if canal_sel == "E-commerce":
    canal_sql = "AND origem_sistema = 'ECOM'"
elif canal_sel == "Loja Jardim América":
    canal_sql = "AND LOWER(loja) LIKE '%jardim%'"
elif canal_sel == "Loja Bernardo Sayão":
    canal_sql = "AND LOWER(loja) LIKE '%bernardo%'"

filtro = f"AND DATE(data_pedido) BETWEEN '{data_inicio}' AND '{data_fim}' {STATUS_FATURADO} {canal_sql}"

# ── KPIs ──────────────────────────────────────────────────────────────────────
df_kpi = run_query(f"""
    SELECT
        COUNT(DISTINCT documento)  AS total_clientes,
        COUNT(DISTINCT CONCAT(pedido_id, loja))  AS total_pedidos,
        SUM(total_pedido)                        AS receita_total,
        AVG(total_pedido)                        AS ticket_medio,
        SUM(desconto)                            AS total_desconto
    FROM {PEDIDOS}
    WHERE documento IS NOT NULL {filtro} {EXCLUIR_LOJAS}
""")

if not df_kpi.empty:
    r = df_kpi.iloc[0]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Clientes Únicos",    fmt_num(r.total_clientes))
    c2.metric("Total de Pedidos",   fmt_num(r.total_pedidos))
    c3.metric("Receita Total",      fmt_brl(r.receita_total))
    c4.metric("Ticket Médio",       fmt_brl(r.ticket_medio))
    c5.metric("Total em Descontos", fmt_brl(r.total_desconto))

# ── Novos vs Recorrentes ───────────────────────────────────────────────────────
df_nv = run_query(f"""
    WITH compras AS (
        SELECT documento, DATE(data_pedido) AS dt
        FROM {PEDIDOS}
        WHERE documento IS NOT NULL {STATUS_FATURADO} {EXCLUIR_LOJAS} {canal_sql}
    ),
    primeira AS (
        SELECT documento, MIN(dt) AS primeira_compra FROM compras GROUP BY documento
    ),
    no_periodo AS (
        SELECT DISTINCT documento FROM compras
        WHERE dt BETWEEN '{data_inicio}' AND '{data_fim}'
    )
    SELECT
        COUNT(*) AS total,
        COUNTIF(p.primeira_compra BETWEEN '{data_inicio}' AND '{data_fim}') AS novos,
        COUNTIF(p.primeira_compra < '{data_inicio}') AS retornantes
    FROM no_periodo np
    JOIN primeira p USING (documento)
""")

if not df_nv.empty and df_nv.iloc[0].total > 0:
    nv = df_nv.iloc[0]
    total = int(nv.total) if nv.total else 1
    cn1, cn2, cn3 = st.columns(3)
    cn1.metric("Clientes no Período",   fmt_num(nv.total))
    cn2.metric("Clientes Novos",        fmt_num(nv.novos),
               delta=f"{nv.novos/total*100:.1f}% do total")
    cn3.metric("Clientes Recorrentes",  fmt_num(nv.retornantes),
               delta=f"{nv.retornantes/total*100:.1f}% do total")

st.divider()

# ── Receita por mês + por canal ───────────────────────────────────────────────
col_l, col_r = st.columns([3, 2])

with col_l:
    st.subheader("Receita Mensal por Loja")
    df_trend = run_query(f"""
        SELECT
            DATE_TRUNC(DATE(data_pedido), MONTH) AS mes,
            loja,
            SUM(total_pedido) AS receita
        FROM {PEDIDOS}
        WHERE documento IS NOT NULL {filtro} {EXCLUIR_LOJAS}
        GROUP BY 1, 2
        ORDER BY 1
    """)
    if not df_trend.empty:
        df_trend["mes"] = pd.to_datetime(df_trend["mes"])
        fig = px.line(
            df_trend, x="mes", y="receita", color="loja",
            labels={"mes": "Mês", "receita": "Receita (R$)", "loja": "Loja"},
            color_discrete_sequence=["#C85DA4", "#8B2FC9", "#F4A0D0"],
            markers=True,
        )
        fig.update_layout(plot_bgcolor="white", hovermode="x unified", legend_title="")
        fig.update_yaxes(tickprefix="R$ ")
        st.plotly_chart(fig, use_container_width=True)

with col_r:
    st.subheader("Participação por Canal")
    df_canal = run_query(f"""
        SELECT
            CASE WHEN origem_sistema = 'ECOM' THEN 'E-commerce' ELSE loja END AS canal,
            SUM(total_pedido) AS receita,
            COUNT(DISTINCT documento) AS clientes
        FROM {PEDIDOS}
        WHERE documento IS NOT NULL {filtro} {EXCLUIR_LOJAS}
        GROUP BY 1
        ORDER BY 2 DESC
    """)
    if not df_canal.empty:
        fig2 = px.pie(
            df_canal, values="receita", names="canal",
            color_discrete_sequence=["#C85DA4", "#8B2FC9", "#E8A0D0", "#F4C6E7"],
        )
        fig2.update_traces(textposition="inside", textinfo="percent+label")
        fig2.update_layout(showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)
        st.dataframe(
            df_canal.rename(columns={"canal": "Canal", "receita": "Receita", "clientes": "Clientes"})
            .assign(Receita=lambda x: x["Receita"].apply(fmt_brl))
            .assign(Clientes=lambda x: x["Clientes"].apply(fmt_num)),
            hide_index=True, use_container_width=True,
        )

st.divider()

# ── Top categorias + Novos clientes ───────────────────────────────────────────
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Top 10 Categorias")
    df_cat = run_query(f"""
        SELECT
            CASE
                WHEN LOWER(COALESCE(categoria,'')) LIKE 'conjunto%' THEN 'Conjunto'
                WHEN LOWER(COALESCE(categoria,'')) LIKE 'vestido%'  THEN 'Vestido'
                ELSE COALESCE(categoria, 'Sem categoria')
            END AS categoria,
            SUM(preco_total) AS receita,
            SUM(quantidade)  AS unidades
        FROM {ITENS}
        WHERE categoria IS NOT NULL
          AND DATE(data_pedido) BETWEEN '{data_inicio}' AND '{data_fim}'
          AND pedido_id IN (
              SELECT pedido_id FROM {PEDIDOS}
              WHERE {STATUS_FATURADO.replace('AND ','')} {EXCLUIR_LOJAS} {canal_sql}
          )
        GROUP BY 1
        ORDER BY 2 DESC
        LIMIT 10
    """)
    if not df_cat.empty:
        fig3 = px.bar(
            df_cat.sort_values("receita"), x="receita", y="categoria", orientation="h",
            color_discrete_sequence=["#C85DA4"],
            labels={"receita": "Receita (R$)", "categoria": ""},
        )
        fig3.update_layout(plot_bgcolor="white")
        fig3.update_xaxes(tickprefix="R$ ")
        st.plotly_chart(fig3, use_container_width=True)

with col_b:
    st.subheader("Novos Clientes por Mês")
    df_novos = run_query(f"""
        WITH primeira AS (
            SELECT documento, DATE_TRUNC(DATE(MIN(data_pedido)), MONTH) AS mes
            FROM {PEDIDOS}
            WHERE documento IS NOT NULL {STATUS_FATURADO} {EXCLUIR_LOJAS} {canal_sql}
            GROUP BY 1
        )
        SELECT mes, COUNT(*) AS novos_clientes
        FROM primeira
        WHERE mes BETWEEN '{data_inicio}' AND '{data_fim}'
        GROUP BY 1
        ORDER BY 1
    """)
    if not df_novos.empty:
        df_novos["mes"] = pd.to_datetime(df_novos["mes"])
        fig4 = px.bar(
            df_novos, x="mes", y="novos_clientes",
            color_discrete_sequence=["#8B2FC9"],
            labels={"mes": "Mês", "novos_clientes": "Novos Clientes"},
        )
        fig4.update_layout(plot_bgcolor="white")
        st.plotly_chart(fig4, use_container_width=True)

# ── Forma de pagamento ─────────────────────────────────────────────────────────
st.subheader("Formas de Pagamento")
df_pg = run_query(f"""
    SELECT
        forma_pagamento,
        COUNT(DISTINCT pedido_id) AS pedidos,
        SUM(valor_pagamento)      AS total
    FROM {PAGAMENTOS}
    WHERE DATE(data_pedido) BETWEEN '{data_inicio}' AND '{data_fim}'
      AND status_pagamento IS NOT NULL
      AND pedido_id IN (
          SELECT pedido_id FROM {PEDIDOS}
          WHERE {STATUS_FATURADO.replace('AND ','')} {EXCLUIR_LOJAS} {canal_sql}
      )
    GROUP BY 1
    ORDER BY 3 DESC
""")
if not df_pg.empty:
    fig5 = px.bar(
        df_pg, x="forma_pagamento", y="total",
        color_discrete_sequence=["#C85DA4"],
        labels={"forma_pagamento": "Forma de Pagamento", "total": "Total (R$)"},
    )
    fig5.update_layout(plot_bgcolor="white")
    fig5.update_yaxes(tickprefix="R$ ")
    st.plotly_chart(fig5, use_container_width=True)
