import streamlit as st
import pandas as pd
from io import BytesIO
from utils import run_query, fmt_brl, fmt_num, CSS, fone_whatsapp, periodo_para_data
from config import PEDIDOS, CLIENTES

st.set_page_config(page_title="Exportação | CRM", page_icon="📤", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)
st.title("📤 Exportação para WhatsApp")
st.markdown("Monte listas segmentadas de clientes para disparos via WhatsApp.")

# ── Construtor de filtros ─────────────────────────────────────────────────────
with st.expander("⚙️ Configurar Filtros da Base", expanded=True):
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Última compra**")
        dias_min = st.number_input("Mínimo de dias sem comprar", min_value=0, value=0)
        dias_max = st.number_input("Máximo de dias sem comprar", min_value=0, value=9999)

    with col2:
        st.markdown("**Valor gasto**")
        valor_min = st.number_input("Gasto mínimo (R$)", min_value=0.0, value=0.0, step=50.0)
        valor_max = st.number_input("Gasto máximo (R$)", min_value=0.0, value=9999999.0, step=100.0)

    with col3:
        st.markdown("**Comportamento**")
        freq_min = st.number_input("Mínimo de pedidos", min_value=1, value=1)
        freq_max = st.number_input("Máximo de pedidos", min_value=1, value=9999)

    col4, col5 = st.columns(2)
    with col4:
        st.markdown("**Objetivo da campanha**")
        objetivo = st.selectbox(
            "Tipo de ação",
            ["Reativação (inativos)", "Recompra (ativos)", "VIPs / Champions", "Aniversariantes do mês", "Personalizado"],
        )
    with col5:
        st.markdown("**Canal de origem**")
        canal_opcao = st.selectbox("Filtrar por canal", ["Todos", "E-commerce", "Loja Física"])

# Presets por objetivo
PRESETS = {
    "Reativação (inativos)":   dict(dias_min=90,  dias_max=9999, freq_min=1,  freq_max=9999, valor_min=0),
    "Recompra (ativos)":       dict(dias_min=30,  dias_max=89,   freq_min=1,  freq_max=9999, valor_min=0),
    "VIPs / Champions":        dict(dias_min=0,   dias_max=9999, freq_min=3,  freq_max=9999, valor_min=500),
    "Aniversariantes do mês":  None,
    "Personalizado":           None,
}

if PRESETS[objetivo] and objetivo != "Personalizado":
    p = PRESETS[objetivo]
    dias_min, dias_max   = p["dias_min"], p["dias_max"]
    freq_min             = p["freq_min"]
    valor_min            = p["valor_min"]

# ── Query ─────────────────────────────────────────────────────────────────────
canal_sql = ""
if canal_opcao == "E-commerce":
    canal_sql = "AND origem_sistema = 'ECOM'"
elif canal_opcao == "Loja Física":
    canal_sql = "AND origem_sistema = 'ERP'"

if objetivo == "Aniversariantes do mês":
    SQL = f"""
        SELECT
            c.documento,
            c.nome_completo,
            c.email,
            c.ddd,
            c.telefone,
            c.data_nascimento,
            c.cidade,
            c.estado,
            m.total_pedidos,
            m.total_gasto,
            m.ultima_compra,
            m.canais
        FROM {CLIENTES} c
        JOIN (
            SELECT
                documento,
                COUNT(DISTINCT pedido_id)        AS total_pedidos,
                SUM(total_pedido)                AS total_gasto,
                MAX(DATE(data_pedido))           AS ultima_compra,
                STRING_AGG(DISTINCT loja, ' / ') AS canais
            FROM {PEDIDOS}
            WHERE documento IS NOT NULL {canal_sql}
            GROUP BY documento
        ) m USING (documento)
        WHERE EXTRACT(MONTH FROM c.data_nascimento) = EXTRACT(MONTH FROM CURRENT_DATE())
          AND c.data_nascimento IS NOT NULL
        ORDER BY EXTRACT(DAY FROM c.data_nascimento)
    """
else:
    SQL = f"""
        WITH metricas AS (
            SELECT
                documento,
                COUNT(DISTINCT pedido_id)                               AS total_pedidos,
                SUM(total_pedido)                                       AS total_gasto,
                MAX(DATE(data_pedido))                                  AS ultima_compra,
                DATE_DIFF(CURRENT_DATE(), MAX(DATE(data_pedido)), DAY)  AS dias_sem_comprar,
                STRING_AGG(DISTINCT loja, ' / ' ORDER BY loja)         AS canais
            FROM {PEDIDOS}
            WHERE documento IS NOT NULL {canal_sql}
            GROUP BY documento
        )
        SELECT
            c.documento,
            c.nome_completo,
            c.email,
            c.ddd,
            c.telefone,
            c.data_nascimento,
            c.cidade,
            c.estado,
            m.total_pedidos,
            m.total_gasto,
            m.ultima_compra,
            m.dias_sem_comprar,
            m.canais
        FROM metricas m
        JOIN {CLIENTES} c USING (documento)
        WHERE m.dias_sem_comprar BETWEEN {dias_min} AND {dias_max}
          AND m.total_pedidos    BETWEEN {freq_min} AND {freq_max}
          AND m.total_gasto      >= {valor_min}
          AND m.total_gasto      <= {valor_max}
        ORDER BY m.total_gasto DESC
    """

if st.button("🔍 Gerar Lista", type="primary"):
    with st.spinner("Buscando clientes..."):
        df = run_query(SQL)

    if df.empty:
        st.warning("Nenhum cliente encontrado com esses filtros.")
    else:
        df["whatsapp"] = df.apply(lambda r: fone_whatsapp(r.ddd, r.telefone), axis=1)
        df["primeiro_nome"] = df["nome_completo"].apply(lambda n: str(n).split()[0] if pd.notna(n) else "")

        st.success(f"✅ **{fmt_num(len(df))} clientes** encontrados.")

        # KPIs rápidos
        c1, c2, c3 = st.columns(3)
        c1.metric("Clientes na lista", fmt_num(len(df)))
        c2.metric("Com WhatsApp",      fmt_num(df[df.whatsapp != ""].shape[0]))
        if "total_gasto" in df.columns:
            c3.metric("Gasto médio",   fmt_brl(df["total_gasto"].mean()))

        st.divider()

        # Preview
        colunas_preview = ["nome_completo", "primeiro_nome", "email", "whatsapp", "cidade", "canais"]
        if "dias_sem_comprar" in df.columns:
            colunas_preview.append("dias_sem_comprar")
        if "data_nascimento" in df.columns:
            colunas_preview.append("data_nascimento")
        colunas_preview += ["total_pedidos", "total_gasto"]

        st.dataframe(
            df[colunas_preview].rename(columns={
                "nome_completo":    "Nome Completo",
                "primeiro_nome":    "Primeiro Nome",
                "email":            "E-mail",
                "whatsapp":         "WhatsApp (55DDD...)",
                "cidade":           "Cidade",
                "canais":           "Canais",
                "dias_sem_comprar": "Dias s/ comprar",
                "data_nascimento":  "Aniversário",
                "total_pedidos":    "Pedidos",
                "total_gasto":      "Total Gasto (R$)",
            }),
            hide_index=True, use_container_width=True,
        )

        # Downloads
        col_dl1, col_dl2 = st.columns(2)

        with col_dl1:
            csv_bytes = df[colunas_preview].to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Baixar CSV",
                data=csv_bytes,
                file_name=f"lista_{objetivo.lower()[:20].replace(' ', '_')}.csv",
                mime="text/csv",
            )

        with col_dl2:
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df[colunas_preview].to_excel(writer, index=False, sheet_name="Lista")
            st.download_button(
                "⬇️ Baixar Excel",
                data=output.getvalue(),
                file_name=f"lista_{objetivo.lower()[:20].replace(' ', '_')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        st.info("""
        **💡 Dica para WhatsApp:**
        A coluna `WhatsApp` já está no formato correto para a maioria das plataformas de disparo:
        `55` + DDD + Número (ex: `5562999887766`).
        """)
