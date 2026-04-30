import streamlit as st
import plotly.express as px
import pandas as pd
from utils import run_query, fmt_brl, fmt_num, CSS, fone_whatsapp, verificar_senha
from config import PEDIDOS, CLIENTES, EXCLUIR_LOJAS, STATUS_FATURADO

st.set_page_config(page_title="Matriz RFM | CRM", page_icon="🎯", layout="wide")
if not verificar_senha():
    st.stop()
st.markdown(CSS, unsafe_allow_html=True)
st.title("🎯 Matriz RFM")
st.markdown("Segmentação de clientes por **R**ecência · **F**requência · **V**alor Monetário")

with st.sidebar:
    st.header("Filtros")
    canal_opcoes = ["Todos os canais", "E-commerce", "Loja Jardim América", "Loja Bernardo Sayão"]
    canal_sel = st.selectbox("Canal", canal_opcoes)

canal_sql = ""
if canal_sel == "E-commerce":
    canal_sql = "AND origem_sistema = 'ECOM'"
elif canal_sel == "Loja Jardim América":
    canal_sql = "AND LOWER(loja) LIKE '%jardim%'"
elif canal_sel == "Loja Bernardo Sayão":
    canal_sql = "AND LOWER(loja) LIKE '%bernardo%'"

SQL_RFM = f"""
WITH pedidos AS (
    SELECT documento, pedido_id, total_pedido, data_pedido
    FROM {PEDIDOS}
    WHERE documento IS NOT NULL
      AND total_pedido > 0
      {STATUS_FATURADO}
      {EXCLUIR_LOJAS}
      {canal_sql}
),
rfm_raw AS (
    SELECT
        documento,
        DATE_DIFF(CURRENT_DATE(), MAX(DATE(data_pedido)), DAY) AS recencia_dias,
        COUNT(DISTINCT pedido_id)                               AS frequencia,
        SUM(total_pedido)                                       AS valor
    FROM pedidos
    GROUP BY documento
),
scored AS (
    SELECT *,
        NTILE(5) OVER (ORDER BY recencia_dias DESC) AS r,
        NTILE(5) OVER (ORDER BY frequencia ASC)     AS f,
        NTILE(5) OVER (ORDER BY valor ASC)           AS m
    FROM rfm_raw
)
SELECT
    s.documento,
    s.recencia_dias,
    s.frequencia,
    s.valor,
    ROUND(s.valor / NULLIF(s.frequencia, 0), 2) AS ticket_medio,
    s.r, s.f, s.m,
    CONCAT(CAST(s.r AS STRING), CAST(s.f AS STRING), CAST(s.m AS STRING)) AS rfm_code,
    CASE
        WHEN s.r >= 4 AND s.f >= 4                       THEN 'Champions'
        WHEN s.r >= 3 AND s.f >= 3                       THEN 'Loyal Customers'
        WHEN s.r >= 4 AND s.f <= 2                       THEN 'Promising'
        WHEN s.r >= 3 AND s.f <= 2                       THEN 'Potential Loyalist'
        WHEN s.r <= 2 AND s.f >= 3                       THEN 'At Risk'
        WHEN s.r = 1  AND s.f >= 3                       THEN 'Cannot Lose Them'
        WHEN s.r <= 2 AND s.f <= 2 AND s.m >= 3         THEN 'About to Sleep'
        WHEN s.r = 1  AND s.f = 1                       THEN 'Lost'
        ELSE                                                  'Hibernating'
    END AS segmento,
    c.nome_completo,
    c.email,
    c.ddd,
    c.telefone,
    c.data_nascimento
FROM scored s
LEFT JOIN {CLIENTES} c USING (documento)
ORDER BY s.valor DESC
"""

with st.spinner("Calculando segmentos RFM..."):
    df = run_query(SQL_RFM)

if df.empty:
    st.warning("Nenhum dado encontrado.")
    st.stop()

COR_SEGMENTO = {
    "Champions":          "#C85DA4",
    "Loyal Customers":    "#8B2FC9",
    "Promising":          "#5BA4CF",
    "Potential Loyalist": "#6DBF82",
    "At Risk":            "#F5A623",
    "Cannot Lose Them":   "#E8453C",
    "About to Sleep":     "#9B9B9B",
    "Hibernating":        "#C0C0C0",
    "Lost":               "#808080",
}

# ── Resumo por segmento ───────────────────────────────────────────────────────
resumo = (
    df.groupby("segmento")
    .agg(
        clientes=("documento", "count"),
        receita=("valor", "sum"),
        freq_media=("frequencia", "mean"),
        ticket_medio=("ticket_medio", "mean"),
        ltv_medio=("valor", "mean"),
    )
    .reset_index()
    .sort_values("receita", ascending=False)
)

col1, col2, col3 = st.columns(3)
col1.metric("Total de Clientes", fmt_num(len(df)))
col2.metric("Champions", fmt_num(len(df[df.segmento == "Champions"])))
col3.metric("Em Risco", fmt_num(len(df[df.segmento.isin(["At Risk", "Cannot Lose Them"])])))

st.divider()

# ── Gráficos ──────────────────────────────────────────────────────────────────
col_l, col_r = st.columns([2, 1])

with col_l:
    st.subheader("Frequência vs Valor (por Recência)")
    fig = px.scatter(
        df.sample(min(5000, len(df))),
        x="frequencia", y="valor", color="segmento",
        size="recencia_dias", size_max=20,
        hover_data=["nome_completo", "recencia_dias"],
        color_discrete_map=COR_SEGMENTO,
        labels={"frequencia": "Frequência (pedidos)", "valor": "Valor Total (R$)", "segmento": "Segmento"},
    )
    fig.update_layout(plot_bgcolor="white")
    fig.update_yaxes(tickprefix="R$ ")
    st.plotly_chart(fig, use_container_width=True)

with col_r:
    st.subheader("Clientes por Segmento")
    fig2 = px.treemap(
        resumo, path=["segmento"], values="clientes",
        color="segmento", color_discrete_map=COR_SEGMENTO,
    )
    fig2.update_traces(textinfo="label+value")
    st.plotly_chart(fig2, use_container_width=True)

# ── Tabela de resumo com ticket e LTV ────────────────────────────────────────
st.subheader("Resumo por Segmento")
resumo_fmt = resumo.copy()
resumo_fmt["receita"]     = resumo_fmt["receita"].apply(fmt_brl)
resumo_fmt["ticket_medio"]= resumo_fmt["ticket_medio"].apply(fmt_brl)
resumo_fmt["ltv_medio"]   = resumo_fmt["ltv_medio"].apply(fmt_brl)
resumo_fmt["freq_media"]  = resumo_fmt["freq_media"].round(1)
resumo_fmt.columns = ["Segmento", "Clientes", "Receita Total", "Freq. Média", "Ticket Médio", "LTV Médio"]
st.dataframe(resumo_fmt, hide_index=True, use_container_width=True)

st.divider()

# ── Regras da Matriz ──────────────────────────────────────────────────────────
with st.expander("📖 Como funciona a Matriz RFM?"):
    st.markdown("""
    A Matriz RFM classifica cada cliente em três dimensões, pontuadas de **1 a 5** (5 = melhor):

    | Dimensão | O que mede | Pontuação 5 significa |
    |---|---|---|
    | **R — Recência** | Dias desde a última compra | Comprou recentemente |
    | **F — Frequência** | Número de pedidos | Compra com muita frequência |
    | **M — Monetário** | Valor total gasto | Gastou muito no total |

    **Segmentos e suas regras:**

    | Segmento | Critério | Ação recomendada |
    |---|---|---|
    | 🏆 **Champions** | R≥4 e F≥4 | Recompensar, pedir indicações |
    | 💛 **Loyal Customers** | R≥3 e F≥3 | Programa de fidelidade |
    | 🌱 **Promising** | R≥4 e F≤2 | Incentivar segunda compra |
    | 🎯 **Potential Loyalist** | R≥3 e F≤2 | Ofertas para aumentar frequência |
    | ⚠️ **At Risk** | R≤2 e F≥3 | Reativação urgente |
    | 🚨 **Cannot Lose Them** | R=1 e F≥3 | Oferta especial imediata |
    | 😴 **About to Sleep** | R≤2, F≤2, M≥3 | Lembrete + desconto |
    | ❌ **Lost** | R=1 e F=1 | Campanha de resgate agressiva |
    | 💤 **Hibernating** | Demais casos | Reativar ou remover da base |
    """)

st.divider()

# ── Explorar segmento ─────────────────────────────────────────────────────────
st.subheader("Explorar Segmento")
segmento_sel = st.selectbox("Selecione o segmento", sorted(df["segmento"].unique()))
df_seg = df[df["segmento"] == segmento_sel].copy()
df_seg["whatsapp"] = df_seg.apply(lambda r: fone_whatsapp(r.ddd, r.telefone), axis=1)

st.markdown(f"**{fmt_num(len(df_seg))} clientes** no segmento *{segmento_sel}*")

colunas_exib = ["nome_completo", "email", "whatsapp", "recencia_dias", "frequencia", "valor", "ticket_medio"]
st.dataframe(
    df_seg[colunas_exib].rename(columns={
        "nome_completo":  "Nome",
        "email":          "E-mail",
        "whatsapp":       "WhatsApp",
        "recencia_dias":  "Dias s/ comprar",
        "frequencia":     "Pedidos",
        "valor":          "LTV (R$)",
        "ticket_medio":   "Ticket Médio (R$)",
    }),
    hide_index=True, use_container_width=True,
)

csv = df_seg[["nome_completo", "email", "whatsapp", "recencia_dias", "frequencia", "valor", "ticket_medio", "segmento"]].to_csv(index=False).encode("utf-8")
st.download_button(
    f"⬇️ Baixar lista '{segmento_sel}' (CSV)",
    data=csv,
    file_name=f"rfm_{segmento_sel.lower().replace(' ', '_')}.csv",
    mime="text/csv",
)
