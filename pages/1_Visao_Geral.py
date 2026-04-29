import streamlit as st
import plotly.express as px
import pandas as pd
from utils import run_query, fmt_brl, fmt_num, CSS, periodo_para_data, sidebar_periodo
from config import PEDIDOS, ITENS

st.set_page_config(page_title="Visão Geral | CRM", page_icon="📊", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)
st.title("📊 Visão Geral")

with st.sidebar:
    st.header("Filtros")
    periodo = sidebar_periodo()
    data_inicio = periodo_para_data(periodo)

filtro = f"AND DATE(data_pedido) >= '{data_inicio}'"

# ── KPIs ──────────────────────────────────────────────────────────────────────
df_kpi = run_query(f"""
    SELECT
        COUNT(DISTINCT documento)  AS total_clientes,
        COUNT(DISTINCT pedido_id)  AS total_pedidos,
        SUM(total_pedido)          AS receita_total,
        AVG(total_pedido)          AS ticket_medio,
        SUM(desconto)              AS total_desconto
    FROM {PEDIDOS}
    WHERE documento IS NOT NULL {filtro}
""")

if not df_kpi.empty:
    r = df_kpi.iloc[0]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Clientes Únicos",    fmt_num(r.total_clientes))
    c2.metric("Total de Pedidos",   fmt_num(r.total_pedidos))
    c3.metric("Receita Total",      fmt_brl(r.receita_total))
    c4.metric("Ticket Médio",       fmt_brl(r.ticket_medio))
    c5.metric("Total em Descontos", fmt_brl(r.total_desconto))

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
        WHERE documento IS NOT NULL {filtro}
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
        WHERE documento IS NOT NULL {filtro}
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

# ── Top categorias + Novos clientes ──────────────────────────────────────────
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Top 10 Categorias")
    df_cat = run_query(f"""
        SELECT
            COALESCE(categoria, 'Sem categoria') AS categoria,
            SUM(preco_total)  AS receita,
            SUM(quantidade)   AS unidades
        FROM {ITENS}
        WHERE categoria IS NOT NULL {filtro.replace('data_pedido', 'DATE(data_pedido)')}
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
            WHERE documento IS NOT NULL
            GROUP BY 1
        )
        SELECT mes, COUNT(*) AS novos_clientes
        FROM primeira
        WHERE mes >= '{data_inicio}'
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

# ── Forma de pagamento ────────────────────────────────────────────────────────
st.subheader("Formas de Pagamento")
from config import PAGAMENTOS
df_pg = run_query(f"""
    SELECT
        forma_pagamento,
        COUNT(DISTINCT pedido_id) AS pedidos,
        SUM(valor_pagamento)      AS total
    FROM {PAGAMENTOS}
    WHERE DATE(data_pedido) >= '{data_inicio}'
      AND status_pagamento IS NOT NULL
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
