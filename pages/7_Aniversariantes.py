import streamlit as st
import pandas as pd
import requests
from datetime import date, timedelta
from utils import run_query, fmt_num, fmt_brl, CSS, fone_whatsapp, primeiro_nome, verificar_senha
from config import PEDIDOS, CLIENTES, EXCLUIR_LOJAS, STATUS_FATURADO

st.set_page_config(page_title="Aniversariantes | CRM", page_icon="🎂", layout="wide")
if not verificar_senha():
    st.stop()
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
    apenas_com_telefone    = st.checkbox("Apenas com telefone cadastrado", value=True)
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
        WHERE documento IS NOT NULL {STATUS_FATURADO} {EXCLUIR_LOJAS}
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

df["whatsapp"]     = df.apply(lambda r: fone_whatsapp(r.ddd, r.telefone), axis=1)
df["primeiro_nome"] = df["nome_completo"].apply(primeiro_nome)

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
c2.metric("Fazem aniversário hoje",               fmt_num(df["faz_aniversario_hoje"].sum()))
c3.metric("Com WhatsApp cadastrado",               fmt_num((df["whatsapp"] != "").sum()))

aniversariantes_hoje = df[df["faz_aniversario_hoje"]]
if not aniversariantes_hoje.empty:
    st.balloons()
    st.success("🎉 **Parabéns hoje:** " + ", ".join(aniversariantes_hoje["primeiro_nome"].tolist()))

st.divider()

# ── Tabela do mês ──────────────────────────────────────────────────────────────
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
    "total_gasto":      "LTV (R$)",
    "ultima_compra":    "Última Compra",
    "dias_sem_comprar": "Dias s/ comprar",
    "canais":           "Canais",
})

st.dataframe(df_exib, hide_index=True, use_container_width=True, height=380)

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

# ── Calendário do mês ──────────────────────────────────────────────────────────
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

# ── Disparo de webhook — próximos 7 dias ─────────────────────────────────────
st.subheader("🚀 Disparo via Webhook — Próximos 7 dias")

proximos_7 = [(hoje + timedelta(days=i)) for i in range(8)]
condicoes = " OR ".join([
    f"(EXTRACT(MONTH FROM c.data_nascimento) = {d.month} AND EXTRACT(DAY FROM c.data_nascimento) = {d.day})"
    for d in proximos_7
])

df_webhook = run_query(f"""
    WITH metricas AS (
        SELECT documento
        FROM {PEDIDOS}
        WHERE documento IS NOT NULL {STATUS_FATURADO} {EXCLUIR_LOJAS}
        GROUP BY documento
    )
    SELECT
        c.documento,
        c.nome_completo,
        c.ddd,
        c.telefone,
        EXTRACT(DAY   FROM c.data_nascimento) AS dia,
        EXTRACT(MONTH FROM c.data_nascimento) AS mes
    FROM {CLIENTES} c
    JOIN metricas m USING (documento)
    WHERE c.data_nascimento IS NOT NULL
      AND ({condicoes})
""")

df_webhook["whatsapp"]     = df_webhook.apply(lambda r: fone_whatsapp(r.ddd, r.telefone), axis=1)
df_webhook["primeiro_nome"] = df_webhook["nome_completo"].apply(primeiro_nome)
df_webhook = df_webhook[df_webhook["whatsapp"] != ""]

st.info(f"**{len(df_webhook)} clientes** com aniversário nos próximos 7 dias e WhatsApp cadastrado.")

if not df_webhook.empty:
    st.dataframe(
        df_webhook[["primeiro_nome", "nome_completo", "whatsapp", "dia", "mes"]].rename(columns={
            "primeiro_nome": "Primeiro Nome", "nome_completo": "Nome Completo",
            "whatsapp": "WhatsApp", "dia": "Dia", "mes": "Mês",
        }),
        hide_index=True, use_container_width=True,
    )

    WEBHOOK_URL = "https://unnichat.com.br/a/start/olTsPCXC6yOLzQHwS34D"

    if st.button("📲 Disparar Webhook Agora (próximos 7 dias)", type="primary"):
        sucesso, erro = 0, 0
        barra = st.progress(0)
        for i, (_, row) in enumerate(df_webhook.iterrows()):
            try:
                payload = {
                    "phone": row["whatsapp"],
                    "variables": [row["primeiro_nome"]],
                }
                resp = requests.post(WEBHOOK_URL, json=payload, timeout=10)
                if resp.status_code < 400:
                    sucesso += 1
                else:
                    erro += 1
            except Exception:
                erro += 1
            barra.progress((i + 1) / len(df_webhook))

        if sucesso:
            st.success(f"✅ {sucesso} webhooks disparados com sucesso!")
        if erro:
            st.warning(f"⚠️ {erro} falhas no envio. Verifique a URL do webhook.")

with st.expander("⚙️ Como automatizar o disparo diário às 9h?"):
    st.markdown(f"""
    Para disparar automaticamente todo dia às 9h sem precisar abrir o sistema, use o **GitHub Actions**:

    1. No seu repositório GitHub, crie o arquivo `.github/workflows/webhook_aniversariantes.yml`
    2. Cole o conteúdo abaixo (o horário está em UTC — 12:00 UTC = 9:00 BRT):

    ```yaml
    name: Webhook Aniversariantes
    on:
      schedule:
        - cron: '0 12 * * *'
    jobs:
      disparar:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v3
          - uses: actions/setup-python@v4
            with:
              python-version: '3.11'
          - run: pip install requests google-cloud-bigquery google-auth db-dtypes
          - run: python webhook_aniversariantes.py
            env:
              GOOGLE_APPLICATION_CREDENTIALS_JSON: ${{{{ secrets.GCP_SA_KEY }}}}
    ```

    3. Adicione o segredo `GCP_SA_KEY` no GitHub (Settings → Secrets → Actions)
       com o conteúdo do arquivo JSON da sua chave de serviço.
    """)
