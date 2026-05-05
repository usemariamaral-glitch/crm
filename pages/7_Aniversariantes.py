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
    canal_opcoes = ["Todos os canais", "E-commerce", "Loja Jardim América", "Loja Bernardo Sayão"]
    canal_sel = st.selectbox("Canal", canal_opcoes)
    apenas_com_telefone    = st.checkbox("Apenas com telefone cadastrado", value=True)
    apenas_clientes_ativos = st.checkbox("Apenas quem já comprou", value=True)

canal_sql = ""
if canal_sel == "E-commerce":
    canal_sql = "AND p.origem_sistema = 'ECOM'"
elif canal_sel == "Loja Jardim América":
    canal_sql = "AND LOWER(p.loja) LIKE '%jardim%'"
elif canal_sel == "Loja Bernardo Sayão":
    canal_sql = "AND LOWER(p.loja) LIKE '%bernardo%'"

SQL = f"""
    WITH metricas AS (
        SELECT
            p.documento,
            COUNT(DISTINCT CONCAT(p.pedido_id, p.loja))                    AS total_pedidos,
            SUM(p.total_pedido)                                            AS total_gasto,
            MAX(DATE(p.data_pedido))                                       AS ultima_compra,
            DATE_DIFF(CURRENT_DATE(), MAX(DATE(p.data_pedido)), DAY)       AS dias_sem_comprar,
            STRING_AGG(DISTINCT p.loja, ' / ' ORDER BY p.loja)            AS canais,
            ARRAY_AGG(p.origem_sistema ORDER BY p.data_pedido DESC LIMIT 1)[OFFSET(0)] AS ultimo_canal
        FROM {PEDIDOS} p
        WHERE p.documento IS NOT NULL {STATUS_FATURADO}
          {EXCLUIR_LOJAS.replace('AND documento', 'AND p.documento')}
          {canal_sql}
        GROUP BY p.documento
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
        m.canais,
        m.ultimo_canal
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
df["primeiro_nome"] = df["nome_completo"].apply(primeiro_nome)

if apenas_com_telefone:
    df = df[df["whatsapp"] != ""]

# ── Métricas do mês ────────────────────────────────────────────────────────────
hoje = date.today()
df["dia_aniversario"] = df["dia_aniversario"].astype(int)

c1, c2, c3 = st.columns(3)
c1.metric(f"Aniversariantes em {MESES[mes_sel]}", fmt_num(len(df)))
c2.metric("Fazem aniversário hoje",               fmt_num((df["dia_aniversario"] == hoje.day).sum()))
c3.metric("Com WhatsApp cadastrado",               fmt_num((df["whatsapp"] != "").sum()))

st.divider()

# ── Tabela do mês ──────────────────────────────────────────────────────────────
st.subheader(f"Lista de Aniversariantes — {MESES[mes_sel]}")

df_exib = df[[
    "dia_aniversario", "nome_completo", "primeiro_nome",
    "email", "whatsapp", "cidade", "canais",
    "total_pedidos", "total_gasto", "ultima_compra", "dias_sem_comprar",
]].rename(columns={
    "dia_aniversario":  "Dia",
    "nome_completo":    "Nome Completo",
    "primeiro_nome":    "Primeiro Nome",
    "email":            "E-mail",
    "whatsapp":         "WhatsApp",
    "cidade":           "Cidade",
    "canais":           "Canais",
    "total_pedidos":    "Pedidos",
    "total_gasto":      "LTV (R$)",
    "ultima_compra":    "Última Compra",
    "dias_sem_comprar": "Dias s/ comprar",
})

st.dataframe(df_exib, hide_index=True, use_container_width=True, height=380)

col_dl1, col_dl2 = st.columns(2)
with col_dl1:
    csv = df_exib.to_csv(index=False).encode("utf-8")
    st.download_button(
        f"⬇️ Baixar CSV — {MESES[mes_sel]}",
        data=csv, file_name=f"aniversariantes_{MESES[mes_sel].lower()}.csv", mime="text/csv",
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

# ── Webhook — exatamente hoje + 7 dias ────────────────────────────────────────
st.subheader("🚀 Disparo via Webhook — Aniversário daqui a 7 dias")

dia_alvo = hoje + timedelta(days=7)
st.info(f"Hoje é **{hoje.strftime('%d/%m/%Y')}**. O disparo será para quem faz aniversário em **{dia_alvo.strftime('%d/%m/%Y')}** (dia {dia_alvo.day} de {MESES[dia_alvo.month]}).")

SQL_WEBHOOK = f"""
    WITH metricas AS (
        SELECT
            p.documento,
            ARRAY_AGG(p.origem_sistema ORDER BY p.data_pedido DESC LIMIT 1)[OFFSET(0)] AS ultimo_canal
        FROM {PEDIDOS} p
        WHERE p.documento IS NOT NULL {STATUS_FATURADO}
          {EXCLUIR_LOJAS.replace('AND documento', 'AND p.documento')}
        GROUP BY p.documento
    )
    SELECT
        c.documento,
        c.nome_completo,
        c.ddd,
        c.telefone,
        EXTRACT(DAY   FROM c.data_nascimento) AS dia,
        EXTRACT(MONTH FROM c.data_nascimento) AS mes_nasc,
        m.ultimo_canal
    FROM {CLIENTES} c
    JOIN metricas m USING (documento)
    WHERE c.data_nascimento IS NOT NULL
      AND EXTRACT(MONTH FROM c.data_nascimento) = {dia_alvo.month}
      AND EXTRACT(DAY   FROM c.data_nascimento) = {dia_alvo.day}
"""

df_webhook = run_query(SQL_WEBHOOK)
df_webhook["whatsapp"]      = df_webhook.apply(lambda r: fone_whatsapp(r.ddd, r.telefone), axis=1)
df_webhook["primeiro_nome"] = df_webhook["nome_completo"].apply(primeiro_nome)
df_webhook["canal"]         = df_webhook["ultimo_canal"].apply(
    lambda c: "ecommerce" if str(c).upper() == "ECOM" else "loja"
)
df_webhook = df_webhook[df_webhook["whatsapp"] != ""]

if df_webhook.empty:
    st.warning(f"Nenhuma cliente com aniversário em {dia_alvo.strftime('%d/%m/%Y')} e WhatsApp cadastrado.")
else:
    st.success(f"**{len(df_webhook)} clientes** para disparar em {dia_alvo.strftime('%d/%m/%Y')}.")
    st.dataframe(
        df_webhook[["primeiro_nome", "nome_completo", "whatsapp", "canal"]].rename(columns={
            "primeiro_nome": "Primeiro Nome", "nome_completo": "Nome Completo",
            "whatsapp": "WhatsApp", "canal": "Canal",
        }),
        hide_index=True, use_container_width=True,
    )

    WEBHOOK_URL = st.secrets.get("webhook_url", "")
    if not WEBHOOK_URL:
        st.error("⚠️ URL do webhook não configurada. Adicione `webhook_url` nos secrets do Streamlit.")
        st.stop()

    if st.button("📲 Disparar Webhook Agora", type="primary"):
        sucesso, erro = 0, 0
        barra = st.progress(0)
        for i, (_, row) in enumerate(df_webhook.iterrows()):
            try:
                payload = {
                    "phone":     row["whatsapp"],
                    "variables": [row["primeiro_nome"]],
                    "canal":     row["canal"],
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
            st.warning(f"⚠️ {erro} falhas no envio.")

st.divider()

# ── Teste de webhook ───────────────────────────────────────────────────────────
with st.expander("🧪 Teste de Webhook (enviar para meu número)"):
    WEBHOOK_URL = st.secrets.get("webhook_url", "")
    st.markdown("""
    Envia **dois disparos de teste** para o seu número — um simulando cliente de loja
    e outro de e-commerce — para você configurar as variáveis na ferramenta.
    """)

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.markdown("**Teste 1 — Loja física**")
        st.json({"phone": "5562994919854", "variables": ["Matheus"], "canal": "loja"})
    with col_t2:
        st.markdown("**Teste 2 — E-commerce**")
        st.json({"phone": "5562994919854", "variables": ["Matheus"], "canal": "ecommerce"})

    if st.button("📲 Enviar testes agora", type="primary"):
        testes = [
            {"phone": "5562994919854", "variables": ["Matheus"], "canal": "loja"},
            {"phone": "5562994919854", "variables": ["Matheus"], "canal": "ecommerce"},
        ]
        for payload in testes:
            try:
                resp = requests.post(WEBHOOK_URL, json=payload, timeout=10)
                status = resp.status_code
                if status < 400:
                    st.success(f"✅ Teste **{payload['canal']}** enviado — status {status}")
                else:
                    st.error(f"❌ Teste **{payload['canal']}** falhou — status {status}: {resp.text[:200]}")
            except Exception as e:
                st.error(f"❌ Erro ao enviar teste **{payload['canal']}**: {e}")

with st.expander("⚙️ Como automatizar o disparo diário às 9h?"):
    st.markdown("""
    Para disparar automaticamente todo dia às 9h, use o **GitHub Actions**.
    Crie o arquivo `.github/workflows/webhook_aniversariantes.yml` no repositório:

    ```yaml
    name: Webhook Aniversariantes
    on:
      schedule:
        - cron: '0 12 * * *'   # 12:00 UTC = 09:00 BRT
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
              GOOGLE_APPLICATION_CREDENTIALS_JSON: ${{ secrets.GCP_SA_KEY }}
    ```
    """)
