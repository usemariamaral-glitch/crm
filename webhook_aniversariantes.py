"""
Script standalone para disparo automático de webhook de aniversariantes.
Roda via GitHub Actions todo dia às 9h BRT (12h UTC).
Envia para quem faz aniversário exatamente daqui a 7 dias.
"""
import os
import json
import requests
from datetime import date, timedelta
from google.oauth2 import service_account
from google.cloud import bigquery

# Credenciais via variável de ambiente (GitHub Secret)
sa_info = json.loads(os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"])
credentials = service_account.Credentials.from_service_account_info(
    sa_info, scopes=["https://www.googleapis.com/auth/bigquery"]
)
client = bigquery.Client(project="datalake-488518", credentials=credentials)

hoje     = date.today()
dia_alvo = hoje + timedelta(days=7)
print(f"Hoje: {hoje} | Disparando para aniversário em: {dia_alvo}")

WEBHOOK_URL = "https://unnichat.com.br/a/start/olTsPCXC6yOLzQHwS34D"

SQL = f"""
WITH metricas AS (
    SELECT
        p.documento,
        ARRAY_AGG(p.origem_sistema ORDER BY p.data_pedido DESC LIMIT 1)[OFFSET(0)] AS ultimo_canal
    FROM `datalake-488518.mari_amaral.trusted_pedidos` p
    WHERE p.documento IS NOT NULL
      AND UPPER(COALESCE(p.status_pedido, '')) = 'FATURADO'
      AND p.documento NOT IN (
          SELECT documento FROM `datalake-488518.mari_amaral.trusted_clientes`
          WHERE UPPER(COALESCE(nome_completo, '')) LIKE '%M A CONFEC%'
             OR UPPER(COALESCE(nome_completo, '')) LIKE '%N S CONFEC%'
      )
    GROUP BY p.documento
)
SELECT
    c.nome_completo,
    c.ddd,
    c.telefone,
    m.ultimo_canal
FROM `datalake-488518.mari_amaral.trusted_clientes` c
JOIN metricas m USING (documento)
WHERE c.data_nascimento IS NOT NULL
  AND EXTRACT(MONTH FROM c.data_nascimento) = {dia_alvo.month}
  AND EXTRACT(DAY   FROM c.data_nascimento) = {dia_alvo.day}
"""

df = client.query(SQL).to_dataframe()
print(f"{len(df)} clientes encontrados para {dia_alvo.strftime('%d/%m/%Y')}")


def fone_whatsapp(ddd, tel):
    try:
        d = str(int(float(str(ddd).strip())))
        t = str(int(float(str(tel).strip())))
        return f"55{d}{t}" if d and t else ""
    except Exception:
        return ""


def primeiro_nome(nome):
    parts = str(nome).strip().split() if nome else []
    return parts[0].capitalize() if parts else ""


sucesso = erro = 0

for _, row in df.iterrows():
    whatsapp = fone_whatsapp(row["ddd"], row["telefone"])
    if not whatsapp:
        continue

    canal = "ecommerce" if str(row["ultimo_canal"]).upper() == "ECOM" else "loja"
    nome  = primeiro_nome(row["nome_completo"])

    payload = {
        "phone":     whatsapp,
        "variables": [nome],
        "canal":     canal,
    }

    try:
        resp = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        if resp.status_code < 400:
            sucesso += 1
            print(f"  ✅ {nome} ({canal}) — {whatsapp}")
        else:
            erro += 1
            print(f"  ❌ {nome} — status {resp.status_code}: {resp.text[:100]}")
    except Exception as e:
        erro += 1
        print(f"  ❌ Erro ao enviar para {nome}: {e}")

print(f"\nFinalizado: {sucesso} enviados, {erro} erros")
