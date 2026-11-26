import os
import httpx
from langchain_core.tools import tool
from pydantic import BaseModel, Field

SAAS_B2B_URL = os.getenv("SaaS_B2B_BASE_URL", "http://localhost:8002")
LIMITE_MAXIMO_CREDITOS_API = 3000

class BuscarEmpresaInput(BaseModel):
    nome: str = Field(..., min_length=2, description="Nome fantasia ou termo de busca da empresa.")

def _format_http_error(exc: Exception) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        detail = exc.response.text
        if status == 404:
            return f"Erro HTTP 404 (Não Encontrado): Recurso inexistente na API SaaS B2B. Detalhe: {detail}"
        if status == 422:
            return f"Erro HTTP 422 (Dados Inválidos): Parâmetros rejeitados pelo contrato da API. Detalhe: {detail}"
        return f"Erro HTTP {status} na API SaaS B2B: {detail}"
    if isinstance(exc, httpx.TimeoutException):
        return "Erro de Timeout: A API SaaS B2B excedeu o tempo limite de resposta (10s)."
    return f"Erro de conexão com a API SaaS B2B: {str(exc)}"

@tool(args_schema=BuscarEmpresaInput)
def buscar_empresa(nome: str) -> str:
    """Busca empresas cadastradas pelo nome fantasia (GET /empresas?nome=...) para obter empresa_id."""
    try:
        with httpx.Client(base_url=SAAS_B2B_URL, timeout=10.0) as client:
            response = client.get("/empresas", params={"nome": nome.strip()})
            response.raise_for_status()
            empresas = response.json()
            if not empresas:
                return f"RESULTADO_VAZIO: Nenhuma empresa encontrada para '{nome}'."
            return f"EMPRESAS_ENCONTRADAS: {empresas}"
    except Exception as exc:
        return _format_http_error(exc)

class ConsultarAssinaturaInput(BaseModel):
    empresa_id: int = Field(..., gt=0, description="ID numérico positivo da empresa.")

@tool(args_schema=ConsultarAssinaturaInput)
def consultar_assinatura(empresa_id: int) -> str:
    """Consulta a assinatura da empresa (GET /assinaturas/{empresa_id}), retornando assinatura_id, o plano vigente, o status da assinatura (ex.: ativa ou inativa), o saldo atual de créditos de API e o limite de usuarios."""
    try:
        with httpx.Client(base_url=SAAS_B2B_URL, timeout=10.0) as client:
            response = client.get(f"/assinaturas/{empresa_id}")
            response.raise_for_status()
            return f"ASSINATURAS_ENCONTRADAS: {response.json()}"
    except Exception as exc:
        return _format_http_error(exc)

class IncluirCreditosInput(BaseModel):
    assinatura_id: int = Field(..., gt=0, description="ID numérico positivo da assinatura.")
    creditos_api: int = Field(
        ...,
        gt=0,
        le=LIMITE_MAXIMO_CREDITOS_API,
        description="Quantidade positiva de créditos em API (máximo permitido: 3000 créditos por operação).",
    )
    motivo: str = Field(..., min_length=5, description="Motivo operacional de créditos de API.")

@tool(args_schema=IncluirCreditosInput)
def incluir_creditos_api(assinatura_id: int, creditos_api: int, motivo: str) -> str:
    """Inclui créditos extras de API em uma assinatura ativa (PATCH /assinaturas/{assinatura_id}/creditos). Limite máximo: 3000 créditos."""
    if creditos_api <= 0 or LIMITE_MAXIMO_CREDITOS_API < creditos_api:
        return f"VALIDACAO_RECUSADA: A quantidade de créditos deve ser estritamente maior que ZERO e não exceder o limite máximo de {LIMITE_MAXIMO_CREDITOS_API}."

    try:
        with httpx.Client(base_url=SAAS_B2B_URL, timeout=10.0) as client:
            response = client.patch(
                f"/assinaturas/{assinatura_id}/creditos",
                json={"creditos_api": creditos_api, "motivo": motivo.strip()},
            )
            response.raise_for_status()
            return f"CREDITOS_INCLUIDOS_SUCESSO: {response.json()}"
    except Exception as exc:
        return _format_http_error(exc)

SAAS_B2B_TOOLS = [
    buscar_empresa,
    consultar_assinatura,
    incluir_creditos_api,
]