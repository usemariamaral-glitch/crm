import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from utils import run_query, fmt_brl, fmt_num, CSS, fone_whatsapp
from config import PEDIDOS, CLIENTES

st.set_page_config(page_title="Matriz RFM | CRM", page_icon="🎯", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)
st.title("🎯 Matriz RFM")
st.markdown("Segmentação de clientes por **R**ecência · **F**requência · **V**alor Monetário")

with st.sidebar:
    st.header("Informações")
    st.markdown("""
    **Segmentos:**
    - 🏆 **Champions** — compram muito, frequentes e recentes
    - 💛 **Loyal** — muito frequentes e valiosos
    - 🌱 **Promising** — recentes mas pouca frequência
    - ⚠️ **At Risk** — eram bons, sumiram
    - 😴 **Hibernating** — pouco engajamento
    - ❌ **Lost** — muito tempo sem comprar
    """)

SQL_RFM = f"""
WITH pedidos AS (
    SELECT documento, pedido_id, total_pedido, data_pedido
    FROM {PEDIDOS}
    WHERE documento IS NOT NULL AND total_pedido > 0
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
    s.r, s.f, s.m,
    CONCAT(CAST(s.r AS STRING), CAST(s.f AS STRING), CAST(s.m AS STRING)) AS rfm_code,
    CASE
        WHEN s.r >= 4 AND s.f >= 4                           THEN 'Champions'
        WHEN s.r >= 3 AND s.f >= 3                           THEN 'Loyal Customers'
        WHEN s.r >= 4 AND s.f <= 2                           THEN 'Promising'
        WHEN s.r >= 3 AND s.f <= 2                           THEN 'Potential Loyalist'
        WHEN s.r <= 2 AND s.f >= 3                           THEN 'At Risk'
        WHEN s.r = 1  AND s.f >= 3                           THEN 'Cannot Lose Them'
        WHEN s.r <= 2 AND s.f <= 2 AND s.m >= 3             THEN 'About to Sleep'
        WHEN s.r = 1  AND s.f = 1                           THEN 'Lost'
        ELSE                                                      'Hibernating'
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

# ── Resumo por segmento ───────────────────────────────────────────────────────
resumo = (
    df.groupby("segmento")
    .agg(clientes=("documento", "count"), receita=("valor", "sum"), freq_media=("frequencia", "mean"))
    .reset_index()
    .sort_values("receita", ascending=False)
)

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

# KPIs rápidos
col1, col2, col3 = st.columns(3)
col1.metric("Total de Clientes", fmt_num(len(df)))
col2.metric("Champions", fmt_num(len(df[df.segmento == "Champions"])))
col3.metric("Em Risco (At Risk + Cannot Lose)", fmt_num(len(df[df.segmento.isin(["At Risk", "Cannot Lose Them"])])))

st.divider()

# ── Gráficos ──────────────────────────────────────────────────────────────────
col_l, col_r = st.columns([2, 1])

with col_l:
    st.subheader("Scatter: Frequência vs Valor (por Recência)")
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

# ── Tabela de resumo ──────────────────────────────────────────────────────────
st.subheader("Resumo por Segmento")
resumo_fmt = resumo.copy()
resumo_fmt["receita"]    = resumo_fmt["receita"].apply(fmt_brl)
resumo_fmt["freq_media"] = resumo_fmt["freq_media"].round(1)
resumo_fmt.columns = ["Segmento", "Clientes", "Receita Total", "Freq. Média"]
st.dataframe(resumo_fmt, hide_index=True, use_container_width=True)

st.divider()

# ── Explorar segmento ─────────────────────────────────────────────────────────
st.subheader("Explorar Segmento")
segmento_sel = st.selectbox("Selecione o segmento", sorted(df["segmento"].unique()))
df_seg = df[df["segmento"] == segmento_sel].copy()
df_seg["whatsapp"] = df_seg.apply(lambda r: fone_whatsapp(r.ddd, r.telefone), axis=1)

st.markdown(f"**{fmt_num(len(df_seg))} clientes** no segmento *{segmento_sel}*")

colunas_exib = ["nome_completo", "email", "whatsapp", "recencia_dias", "frequencia", "valor"]
st.dataframe(
    df_seg[colunas_exib].rename(columns={
        "nome_completo": "Nome",
        "email": "E-mail",
        "whatsapp": "WhatsApp",
        "recencia_dias": "Dias s/ comprar",
        "frequencia": "Pedidos",
        "valor": "Total Gasto (R$)",
    }),
    hide_index=True, use_container_width=True,
)

csv = df_seg[["nome_completo", "email", "whatsapp", "recencia_dias", "frequencia", "valor"]].to_csv(index=False).encode("utf-8")
st.download_button(
    f"⬇️ Baixar lista '{segmento_sel}' (CSV)",
    data=csv,
    file_name=f"rfm_{segmento_sel.lower().replace(' ', '_')}.csv",
    mime="text/csv",
)
