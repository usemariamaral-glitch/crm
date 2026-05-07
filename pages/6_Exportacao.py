import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import date
from utils import run_query, fmt_brl, fmt_num, fone_whatsapp, primeiro_nome, verificar_senha
from config import PEDIDOS, CLIENTES, EXCLUIR_LOJAS, STATUS_FATURADO

st.set_page_config(page_title="Exportação | CRM", page_icon="📤", layout="wide")
if not verificar_senha():
    st.stop()
st.title("📤 Exportação para WhatsApp")
st.markdown("Monte listas segmentadas de clientes para disparos via WhatsApp.")

# ── Configuração da campanha ───────────────────────────────────────────────────
with st.expander("⚙️ Configurar Filtros da Base", expanded=True):
    col_camp, _ = st.columns([2, 1])
    with col_camp:
        nome_campanha = st.text_input("Nome da campanha (para identificar depois)", placeholder="Ex: Reativação Maio 2025")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Última compra (dias atrás)**")
        dias_min = st.number_input("Comprou há pelo menos (dias)", min_value=0, value=0)
        dias_max = st.number_input("Comprou há no máximo (dias)", min_value=0, value=9999)

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
            ["Reativação (inativos)", "Recompra (ativos)", "VIPs / Champions",
             "Aniversariantes do mês", "Segmento RFM", "Personalizado"],
        )
    with col5:
        st.markdown("**Canal de origem**")
        canal_opcao = st.selectbox("Filtrar por canal", ["Todos", "E-commerce", "Loja Física"])

    if objetivo == "Segmento RFM":
        segmento_rfm = st.selectbox("Segmento RFM", [
            "Champions", "Loyal Customers", "Promising", "Potential Loyalist",
            "At Risk", "Cannot Lose Them", "About to Sleep", "Hibernating", "Lost",
        ])

# Presets por objetivo
PRESETS = {
    "Reativação (inativos)":  dict(dias_min=90,  dias_max=9999, freq_min=1, freq_max=9999, valor_min=0),
    "Recompra (ativos)":      dict(dias_min=30,  dias_max=89,   freq_min=1, freq_max=9999, valor_min=0),
    "VIPs / Champions":       dict(dias_min=0,   dias_max=9999, freq_min=3, freq_max=9999, valor_min=500),
}

if objetivo in PRESETS:
    p = PRESETS[objetivo]
    dias_min, dias_max = p["dias_min"], p["dias_max"]
    freq_min = p["freq_min"]
    valor_min = p["valor_min"]

canal_sql = ""
if canal_opcao == "E-commerce":
    canal_sql = "AND origem_sistema = 'ECOM'"
elif canal_opcao == "Loja Física":
    canal_sql = "AND origem_sistema = 'ERP'"

# ── Query por objetivo ────────────────────────────────────────────────────────
if objetivo == "Aniversariantes do mês":
    SQL = f"""
        SELECT
            c.documento, c.nome_completo, c.email, c.ddd, c.telefone,
            c.data_nascimento, c.cidade, c.estado,
            m.total_pedidos, m.total_gasto, m.ticket_medio, m.ultima_compra, m.canais
        FROM {CLIENTES} c
        JOIN (
            SELECT
                documento,
                COUNT(DISTINCT CONCAT(pedido_id, loja)) AS total_pedidos,
                SUM(total_pedido)                     AS total_gasto,
                AVG(total_pedido)                     AS ticket_medio,
                MAX(DATE(data_pedido))                AS ultima_compra,
                STRING_AGG(DISTINCT loja, ' / ')      AS canais
            FROM {PEDIDOS}
            WHERE documento IS NOT NULL {STATUS_FATURADO} {EXCLUIR_LOJAS} {canal_sql}
            GROUP BY documento
        ) m USING (documento)
        WHERE EXTRACT(MONTH FROM c.data_nascimento) = EXTRACT(MONTH FROM CURRENT_DATE())
          AND c.data_nascimento IS NOT NULL
        ORDER BY EXTRACT(DAY FROM c.data_nascimento)
    """

elif objetivo == "Segmento RFM":
    SQL = f"""
    WITH rfm_raw AS (
        SELECT
            documento,
            DATE_DIFF(CURRENT_DATE(), MAX(DATE(data_pedido)), DAY) AS recencia_dias,
            COUNT(DISTINCT CONCAT(pedido_id, loja))                 AS frequencia,
            SUM(total_pedido)                                       AS valor,
            AVG(total_pedido)                                       AS ticket_medio
        FROM {PEDIDOS}
        WHERE documento IS NOT NULL AND total_pedido > 0
          {STATUS_FATURADO} {EXCLUIR_LOJAS} {canal_sql}
        GROUP BY documento
    ),
    scored AS (
        SELECT *,
            NTILE(5) OVER (ORDER BY recencia_dias DESC) AS r,
            NTILE(5) OVER (ORDER BY frequencia ASC)     AS f,
            NTILE(5) OVER (ORDER BY valor ASC)           AS m
        FROM rfm_raw
    ),
    segmentado AS (
        SELECT *,
            CASE
                WHEN r >= 4 AND f >= 4             THEN 'Champions'
                WHEN r >= 3 AND f >= 3             THEN 'Loyal Customers'
                WHEN r >= 4 AND f <= 2             THEN 'Promising'
                WHEN r >= 3 AND f <= 2             THEN 'Potential Loyalist'
                WHEN r <= 2 AND f >= 3             THEN 'At Risk'
                WHEN r = 1  AND f >= 3             THEN 'Cannot Lose Them'
                WHEN r <= 2 AND f <= 2 AND m >= 3 THEN 'About to Sleep'
                WHEN r = 1  AND f = 1             THEN 'Lost'
                ELSE                                   'Hibernating'
            END AS segmento
        FROM scored
    )
    SELECT
        s.documento, c.nome_completo, c.email, c.ddd, c.telefone,
        c.data_nascimento, c.cidade, c.estado,
        s.frequencia AS total_pedidos,
        s.valor      AS total_gasto,
        s.ticket_medio,
        s.recencia_dias AS dias_sem_comprar,
        s.segmento
    FROM segmentado s
    LEFT JOIN {CLIENTES} c USING (documento)
    WHERE s.segmento = '{segmento_rfm}'
    ORDER BY s.valor DESC
    """

else:
    SQL = f"""
        WITH metricas AS (
            SELECT
                documento,
                COUNT(DISTINCT CONCAT(pedido_id, loja))                 AS total_pedidos,
                SUM(total_pedido)                                       AS total_gasto,
                AVG(total_pedido)                                       AS ticket_medio,
                MAX(DATE(data_pedido))                                  AS ultima_compra,
                DATE_DIFF(CURRENT_DATE(), MAX(DATE(data_pedido)), DAY)  AS dias_sem_comprar,
                STRING_AGG(DISTINCT loja, ' / ' ORDER BY loja)         AS canais
            FROM {PEDIDOS}
            WHERE documento IS NOT NULL {STATUS_FATURADO} {EXCLUIR_LOJAS} {canal_sql}
            GROUP BY documento
        )
        SELECT
            c.documento, c.nome_completo, c.email, c.ddd, c.telefone,
            c.data_nascimento, c.cidade, c.estado,
            m.total_pedidos, m.total_gasto, m.ticket_medio,
            m.ultima_compra, m.dias_sem_comprar, m.canais
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
        df["whatsapp"]     = df.apply(lambda r: fone_whatsapp(r.ddd, r.telefone), axis=1)
        df["primeiro_nome"] = df["nome_completo"].apply(primeiro_nome)
        tag_campanha = nome_campanha.strip() if nome_campanha.strip() else objetivo
        df["campanha"]     = f"{tag_campanha} — {date.today().strftime('%d/%m/%Y')}"

        st.success(f"✅ **{fmt_num(len(df))} clientes** encontrados.")

        c1, c2, c3 = st.columns(3)
        c1.metric("Clientes na lista", fmt_num(len(df)))
        c2.metric("Com WhatsApp",      fmt_num(df[df.whatsapp != ""].shape[0]))
        if "total_gasto" in df.columns:
            c3.metric("LTV médio",     fmt_brl(df["total_gasto"].mean()))

        st.divider()

        colunas_preview = ["nome_completo", "primeiro_nome", "email", "whatsapp", "cidade"]
        if "canais" in df.columns:
            colunas_preview.append("canais")
        if "dias_sem_comprar" in df.columns:
            colunas_preview.append("dias_sem_comprar")
        if "data_nascimento" in df.columns:
            colunas_preview.append("data_nascimento")
        if "segmento" in df.columns:
            colunas_preview.append("segmento")
        colunas_preview += ["total_pedidos", "total_gasto", "ticket_medio", "campanha"]

        rename_map = {
            "nome_completo":    "Nome Completo",
            "primeiro_nome":    "Primeiro Nome",
            "email":            "E-mail",
            "whatsapp":         "WhatsApp (55DDD...)",
            "cidade":           "Cidade",
            "canais":           "Canais",
            "dias_sem_comprar": "Dias s/ comprar",
            "data_nascimento":  "Aniversário",
            "segmento":         "Segmento RFM",
            "total_pedidos":    "Pedidos",
            "total_gasto":      "LTV (R$)",
            "ticket_medio":     "Ticket Médio (R$)",
            "campanha":         "Campanha",
        }

        colunas_existentes = [c for c in colunas_preview if c in df.columns]
        df_preview = df[colunas_existentes].rename(columns=rename_map)
        st.dataframe(df_preview, hide_index=True, use_container_width=True)

        nome_arquivo = f"{tag_campanha[:30].replace(' ', '_')}_{date.today().strftime('%Y%m%d')}"
        col_dl1, col_dl2 = st.columns(2)

        with col_dl1:
            csv_bytes = df_preview.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Baixar CSV",
                data=csv_bytes,
                file_name=f"{nome_arquivo}.csv",
                mime="text/csv",
            )

        with col_dl2:
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df_preview.to_excel(writer, index=False, sheet_name="Lista")
            st.download_button(
                "⬇️ Baixar Excel",
                data=output.getvalue(),
                file_name=f"{nome_arquivo}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        st.info("""
        **💡 Dica:** A coluna **Campanha** registra o nome e a data do disparo, para você
        identificar depois quais clientes receberam qual mensagem.
        A coluna **WhatsApp** já está no formato correto: `55` + DDD + número (ex: `5562999887766`).
        """)
