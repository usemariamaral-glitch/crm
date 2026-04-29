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
