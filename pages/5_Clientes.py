import streamlit as st
import pandas as pd
from utils import run_query, fmt_brl, fmt_num, CSS, fone_whatsapp, sidebar_periodo, verificar_senha
from config import PEDIDOS, CLIENTES, EXCLUIR_LOJAS, STATUS_FATURADO

st.set_page_config(page_title="Clientes | CRM", page_icon="👥", layout="wide")
if not verificar_senha():
    st.stop()
st.markdown(CSS, unsafe_allow_html=True)
st.title("👥 Base de Clientes")

with st.sidebar:
    st.header("Filtros")
    data_inicio, data_fim = sidebar_periodo()
    st.divider()
    busca_nome  = st.text_input("Buscar por nome")
    busca_email = st.text_input("Buscar por e-mail")
    busca_tel   = st.text_input("Buscar por telefone")

filtro = f"AND DATE(data_pedido) BETWEEN '{data_inicio}' AND '{data_fim}' {STATUS_FATURADO}"

SQL_CLIENTES = f"""
    WITH metricas AS (
        SELECT
            documento,
            COUNT(DISTINCT CONCAT(pedido_id, loja))                 AS total_pedidos,
            SUM(total_pedido)                                       AS total_gasto,
            AVG(total_pedido)                                       AS ticket_medio,
            MAX(DATE(data_pedido))                                  AS ultima_compra,
            MIN(DATE(data_pedido))                                  AS primeira_compra,
            DATE_DIFF(CURRENT_DATE(), MAX(DATE(data_pedido)), DAY)  AS dias_sem_comprar,
            STRING_AGG(DISTINCT loja, ' / ' ORDER BY loja)         AS canais
        FROM {PEDIDOS}
        WHERE documento IS NOT NULL {filtro} {EXCLUIR_LOJAS}
        GROUP BY documento
    )
    SELECT
        c.documento,
        c.nome_completo,
        c.email,
        CONCAT(COALESCE(CAST(c.ddd AS STRING),''), COALESCE(CAST(c.telefone AS STRING),'')) AS telefone_raw,
        c.ddd,
        c.telefone,
        c.data_nascimento,
        c.cidade,
        c.estado,
        m.total_pedidos,
        m.total_gasto,
        m.ticket_medio,
        m.ultima_compra,
        m.primeira_compra,
        m.dias_sem_comprar,
        m.canais
    FROM metricas m
    JOIN {CLIENTES} c USING (documento)
    ORDER BY m.total_gasto DESC
"""

with st.spinner("Carregando base de clientes..."):
    df = run_query(SQL_CLIENTES)

if df.empty:
    st.warning("Nenhum cliente encontrado.")
    st.stop()

df["whatsapp"] = df.apply(lambda r: fone_whatsapp(r.ddd, r.telefone), axis=1)

# ── Filtros de busca ──────────────────────────────────────────────────────────
if busca_nome:
    df = df[df["nome_completo"].str.contains(busca_nome, case=False, na=False)]
if busca_email:
    df = df[df["email"].str.contains(busca_email, case=False, na=False)]
if busca_tel:
    df = df[df["telefone_raw"].astype(str).str.contains(busca_tel, na=False)]

# ── KPIs ──────────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("Clientes encontrados",    fmt_num(len(df)))
c2.metric("Ticket médio",            fmt_brl(df["ticket_medio"].mean()))
c3.metric("Dias médios sem comprar", f"{df['dias_sem_comprar'].mean():.0f} dias" if not df.empty else "—")
c4.metric("Total de pedidos",        fmt_num(df["total_pedidos"].sum()))

st.divider()

# ── Filtros adicionais ────────────────────────────────────────────────────────
col_f1, col_f2, col_f3, col_f4 = st.columns(4)

with col_f1:
    canais_disponiveis = sorted(set(
        canal.strip()
        for canais in df["canais"].dropna()
        for canal in canais.split("/")
    ))
    canal_filtro = st.multiselect("Canal", canais_disponiveis)

with col_f2:
    min_pedidos = st.number_input("Mínimo de pedidos", min_value=1, value=1)

with col_f3:
    ordenar_por = st.selectbox("Ordenar por", ["Total Gasto", "Pedidos", "Dias sem comprar", "Nome"])

with col_f4:
    apenas_whatsapp = st.checkbox("Apenas com WhatsApp")

if canal_filtro:
    df = df[df["canais"].apply(lambda c: any(f in str(c) for f in canal_filtro))]

df = df[df["total_pedidos"] >= min_pedidos]

if apenas_whatsapp:
    df = df[df["whatsapp"] != ""]

ordem_map = {
    "Total Gasto":       ("total_gasto", False),
    "Pedidos":           ("total_pedidos", False),
    "Dias sem comprar":  ("dias_sem_comprar", False),
    "Nome":              ("nome_completo", True),
}
col_ord, asc_ord = ordem_map[ordenar_por]
df = df.sort_values(col_ord, ascending=asc_ord)

# ── Tabela ────────────────────────────────────────────────────────────────────
df_exib = df[[
    "nome_completo", "email", "whatsapp", "cidade",
    "canais", "total_pedidos", "ticket_medio", "total_gasto",
    "ultima_compra", "dias_sem_comprar",
]].rename(columns={
    "nome_completo":    "Nome",
    "email":            "E-mail",
    "whatsapp":         "WhatsApp",
    "cidade":           "Cidade",
    "canais":           "Canais",
    "total_pedidos":    "Pedidos",
    "ticket_medio":     "Ticket Médio (R$)",
    "total_gasto":      "LTV (R$)",
    "ultima_compra":    "Última Compra",
    "dias_sem_comprar": "Dias s/ comprar",
})

st.dataframe(df_exib, hide_index=True, use_container_width=True, height=420)

csv = df_exib.to_csv(index=False).encode("utf-8")
st.download_button("⬇️ Exportar tabela (CSV)", data=csv, file_name="clientes.csv", mime="text/csv")

st.divider()

# ── Ficha do cliente ──────────────────────────────────────────────────────────
st.subheader("🔍 Ficha do Cliente")

if df.empty:
    st.info("Nenhum cliente para exibir ficha.")
else:
    doc_to_nome = dict(zip(df["documento"].tolist(), df["nome_completo"].fillna("").tolist()))
    doc_sel = st.selectbox(
        "Selecione um cliente",
        options=df["documento"].tolist(),
        format_func=lambda d: doc_to_nome.get(d, str(d)),
    )

    if doc_sel:
        row = df[df["documento"] == doc_sel].iloc[0]

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"**Nome:** {row.nome_completo}")
            st.markdown(f"**E-mail:** {row.email}")
            st.markdown(f"**WhatsApp:** {row.whatsapp}")
            st.markdown(f"**Aniversário:** {row.data_nascimento}")
            st.markdown(f"**Cidade:** {row.cidade} / {row.estado}")
            st.markdown(f"**Canais:** {row.canais}")
        with col_b:
            st.metric("Total de Pedidos", fmt_num(row.total_pedidos))
            st.metric("LTV (Total Gasto)", fmt_brl(row.total_gasto))
            st.metric("Ticket Médio",     fmt_brl(row.ticket_medio))
            st.metric("Última Compra",    str(row.ultima_compra))
            st.metric("Dias sem comprar", f"{row.dias_sem_comprar} dias")

        df_hist = run_query(f"""
            SELECT
                DATE(data_pedido) AS data,
                loja,
                numero_pedido,
                status_pedido,
                total_pedido
            FROM {PEDIDOS}
            WHERE documento = '{doc_sel}'
            ORDER BY data_pedido DESC
            LIMIT 50
        """)
        if not df_hist.empty:
            st.markdown("**Histórico de Pedidos:**")
            st.dataframe(df_hist.rename(columns={
                "data": "Data", "loja": "Loja", "numero_pedido": "Nº Pedido",
                "status_pedido": "Status", "total_pedido": "Total (R$)"
            }), hide_index=True, use_container_width=True)
