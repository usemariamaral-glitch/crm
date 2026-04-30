PROJECT_ID = "datalake-488518"
DATASET    = "mari_amaral"

def T(nome: str) -> str:
    return f"`{PROJECT_ID}.{DATASET}.{nome}`"

CLIENTES   = T("trusted_clientes")
PEDIDOS    = T("trusted_pedidos")
ITENS      = T("trusted_itens_pedido")
PAGAMENTOS = T("trusted_pagamentos")
PRODUTOS   = T("trusted_produtos")

PERIODOS = [
    "Últimos 30 dias",
    "Últimos 90 dias",
    "Últimos 12 meses",
    "Este ano",
    "Tudo",
]

# Exclui documentos das lojas próprias (aparecem indevidamente como clientes)
EXCLUIR_LOJAS = f"""
    AND documento NOT IN (
        SELECT documento FROM {CLIENTES}
        WHERE UPPER(COALESCE(nome_completo, '')) LIKE '%M A CONFEC%'
           OR UPPER(COALESCE(nome_completo, '')) LIKE '%N S CONFEC%'
    )
"""

# Apenas pedidos com status faturado
STATUS_FATURADO = "AND UPPER(COALESCE(status_pedido, '')) = 'FATURADO'"
