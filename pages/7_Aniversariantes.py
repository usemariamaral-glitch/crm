import streamlit as st
import pandas as pd
from datetime import date
from utils import run_query, fmt_num, CSS, fone_whatsapp
from config import PEDIDOS, CLIENTES

st.set_page_config(page_title="Aniversariantes | CRM", page_icon="🎂", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)
st.title("🎂 Aniversariantes")
st.markdown("Gerencie os aniversariantes para ações de relacionamento personalizadas.")

MESES = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março",    4: "Abril",
    5: "Maio",    6: "Junho",     7: "Julho",     8: "Agosto",
    9: "Setembro",10: "Outubro",  11: "Novembro", 12: "Dezembro",
}

with st.sidebar:
    st.header("Filtros")
    mes_sel = st.selectbox(
        "Mês", list(MESES.keys()),
        format_func=lambda m: MESES[m],
        index=date.today().month - 1,
    )
    apenas_com_telefone = st.checkbox("Apenas com telefone cadastrado", value=True)
    apenas_clientes_ativos = st.checkbox("Apenas quem já comprou", value=True)

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
        WHERE documento IS NOT NULL
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
        EXTRACT(DAY FROM c.data_nascimento) AS dia_aniversario,
        m.total_pedidos,
        m.total_gasto,
        m.ultima_compra,
        m.dias_sem_comprar,
        m.canais
    FROM {CLIENTES} c
    {"JOIN" if apenas_clientes_ativos else "LEFT JOIN"} metricas m USING (documento)
    WHERE c.data_nascimento IS NOT NULL
      AND EXTRACT(MONTH FROM c.data_nascimento) = {mes_sel}
    ORDER BY EXTRACT(DAY FROM c.data_nascimento)
"""

df = run_query(SQL)

if df.empty:
    st.warning(f"Nenhum aniversariante encontrado em {MESES[mes_sel]}.")
    st.stop()

df["whatsapp"]      = df.apply(lambda r: fone_whatsapp(r.ddd, r.telefone), axis=1)
df["primeiro_nome"] = df["nome_completo"].apply(lambda n: str(n).split()[0] if pd.notna(n) else "")

if apenas_com_telefone:
    df = df[df["whatsapp"] != ""]

# ── Destaques do mês ──────────────────────────────────────────────────────────
hoje = date.today()
df["faz_aniversario_hoje"] = df["dia_aniversario"] == hoje.day
df["dias_para_aniversario"] = df["dia_aniversario"].apply(
    lambda d: int(d) - hoje.day if int(d) >= hoje.day else int(d) + (31 - hoje.day)
)

c1, c2, c3 = st.columns(3)
c1.metric(f"Aniversariantes em {MESES[mes_sel]}", fmt_num(len(df)))
c2.metric("Fazem aniversário hoje 🎉",             fmt_num(df["faz_aniversario_hoje"].sum()))
c3.metric("Com WhatsApp cadastrado",               fmt_num((df["whatsapp"] != "").sum()))

# Destaque de hoje
aniversariantes_hoje = df[df["faz_aniversario_hoje"]]
if not aniversariantes_hoje.empty:
    st.balloons()
    st.success(f"🎉 **Parabéns hoje:** " + ", ".join(aniversariantes_hoje["primeiro_nome"].tolist()))

st.divider()

# ── Tabela do mês ─────────────────────────────────────────────────────────────
st.subheader(f"Lista de Aniversariantes — {MESES[mes_sel]}")

df_exib = df[[
    "dia_aniversario", "nome_completo", "primeiro_nome",
    "email", "whatsapp", "cidade",
    "total_pedidos", "total_gasto", "ultima_compra", "dias_sem_comprar", "canais",
]].rename(columns={
    "dia_aniversario":  "Dia",
    "nome_completo":    "Nome Completo",
    "primeiro_nome":    "Primeiro Nome",
    "email":            "E-mail",
    "whatsapp":         "WhatsApp",
    "cidade":           "Cidade",
    "total_pedidos":    "Pedidos",
    "total_gasto":      "Total Gasto (R$)",
    "ultima_compra":    "Última Compra",
    "dias_sem_comprar": "Dias s/ comprar",
    "canais":           "Canais",
})

st.dataframe(df_exib, hide_index=True, use_container_width=True, height=380)

# ── Downloads ─────────────────────────────────────────────────────────────────
col_dl1, col_dl2 = st.columns(2)

with col_dl1:
    csv = df_exib.to_csv(index=False).encode("utf-8")
    st.download_button(
        f"⬇️ Baixar CSV — {MESES[mes_sel]}",
        data=csv,
        file_name=f"aniversariantes_{MESES[mes_sel].lower()}.csv",
        mime="text/csv",
    )

with col_dl2:
    from io import BytesIO
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_exib.to_excel(writer, index=False, sheet_name="Aniversariantes")
    st.download_button(
        f"⬇️ Baixar Excel — {MESES[mes_sel]}",
        data=output.getvalue(),
        file_name=f"aniversariantes_{MESES[mes_sel].lower()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

st.divider()

# ── Calendário do mês ─────────────────────────────────────────────────────────
st.subheader("Distribuição por dia do mês")
import plotly.express as px

df_dias = df.groupby("dia_aniversario").size().reset_index(name="quantidade")
df_dias["dia_aniversario"] = df_dias["dia_aniversario"].astype(int)

fig = px.bar(
    df_dias, x="dia_aniversario", y="quantidade",
    labels={"dia_aniversario": "Dia do mês", "quantidade": "Aniversariantes"},
    color_discrete_sequence=["#C85DA4"],
)
fig.update_layout(plot_bgcolor="white", xaxis=dict(tickmode="linear", dtick=1))
if hoje.month == mes_sel:
    fig.add_vline(x=hoje.day, line_dash="dash", line_color="#8B2FC9", annotation_text="Hoje")
st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── Como automatizar (webhook) ────────────────────────────────────────────────
with st.expander("⚙️ Como automatizar o disparo de aniversário?"):
    st.markdown("""
    ### Opção 1 — Plataforma de WhatsApp (recomendada)
    A maioria das ferramentas de WhatsApp Marketing (Z-API, WPPConnect, Twilio, etc.)
    permite configurar **campanhas automáticas por data**. Exporte a lista acima e importe
    na ferramenta, definindo o dia de envio como a data de aniversário.

    ### Opção 2 — Google Cloud Scheduler + Cloud Functions
    Se quiser automatização total integrada ao seu BigQuery:
    1. Crie uma **Cloud Function** em Python que roda a query de aniversariantes do dia
    2. Agende ela todo dia às 9h com o **Cloud Scheduler**
    3. A função chama a API da sua ferramenta de WhatsApp com a lista do dia

    ### Opção 3 — Planilha + Make/Zapier
    1. Exporte mensalmente a lista para Google Sheets
    2. Configure um cenário no Make ou Zapier para comparar a data de hoje com a coluna "Dia"
    3. Dispare automaticamente via WhatsApp API quando houver match

    **Sugestão de mensagem:**
    > Oi [Primeiro Nome]! 🎂 A Mari Amaral deseja um feliz aniversário pra você!
    > Como presente, você ganhou **X% de desconto** na sua próxima compra.
    > Use o cupom: ANIVERSARIO[ANO] — válido por 7 dias 💛
    """)
