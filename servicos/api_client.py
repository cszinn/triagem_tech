"""
servicos/api_client.py — Cliente HTTP para a API de estoque/triagem.
Centraliza todas as chamadas REST em funções reutilizáveis.
Inclui tradução e formatação amigável de erros da API.
"""

import requests
import re

session = requests.Session()
usa_cookies = False

def configurar_sessao_com_cookies(cookies_dict):
    global usa_cookies
    if cookies_dict:
        for k, v in cookies_dict.items():
            session.cookies.set(k, v)
        usa_cookies = True

def _chave_ordenacao_natural(texto: str):
    """Gera chave para ordenação natural (ex: iPhone 5 antes de iPhone 11)."""
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', str(texto))]


def _ordenar_por_gravidade(lista: list, hierarquia: list) -> list:
    """Filtra lixo (como CARREGANDO...) e ordena baseando-se em uma hierarquia definida."""
    # 1. Filtra itens indesejados
    limpos = [i for i in lista if i.strip().upper() not in ("CARREGANDO...", "EXELENTE")]
    
    # 2. Ordena de acordo com o índice na lista hierarquia
    def peso(item):
        val = item.strip().upper()
        if val in hierarquia:
            return hierarquia.index(val)
        return 999  # Itens desconhecidos/novos vão pro final
        
    return sorted(limpos, key=peso)

_HIERARQUIA_ESTADO = ["EXCELENTE", "EXELENTE", "BOM", "RAZOAVEL", "RASOAVEL", "RUIM", "SUCATA"]
_HIERARQUIA_CONDICAO = ["EXCELENTE", "LIGA", "LIGA PARCIALMENTE", "NAO LIGA", "NÃO LIGA", "BLOQUEADO"]
_HIERARQUIA_ACESSO = ["DESBLOQUEADO", "BLOQUEADO POR SENHA", "BLOQUEADO", "BLOQUEADO POR OPERADORA", "ICLOUD ATIVO", "FRP ATIVO", "N/A"]

def _tratar_erro_api(response):
    """Analisa a resposta HTTP de erro e levanta uma Exception com mensagem amigável."""
    status = response.status_code
    msg_api = ""
    
    # Tenta extrair a mensagem específica retornada pelo backend
    try:
        dados = response.json()
        if "mensagem" in dados:
            msg_api = dados["mensagem"]
        elif "title" in dados:
            msg_api = dados["title"]
        elif "errors" in dados:
            # Pega o primeiro erro de validação (ex: ModelState no .NET)
            for k, v in dados["errors"].items():
                if isinstance(v, list) and len(v) > 0:
                    msg_api = f"{k}: {v[0]}"
                    break
    except Exception:
        msg_api = response.text.strip()
        if len(msg_api) > 100:
            msg_api = msg_api[:100] + "..."

    # Dicionário de tradução amigável
    erros_amigaveis = {
        400: "Requisição Inválida (Verifique se não deixou campos obrigatórios vazios ou digitou algo errado).",
        401: "Não Autorizado. Faça login novamente.",
        403: "Acesso Negado.",
        404: "Recurso não encontrado no servidor.",
        408: "Tempo de requisição esgotado (Timeout).",
        422: "Entidade Não Processável (Erro de validação nos dados enviados).",
        500: "Erro Interno no Servidor (API falhou ao processar).",
        502: "Bad Gateway (Servidor da API está fora do ar ou reiniciando).",
        503: "Serviço Indisponível (API em manutenção).",
        504: "Gateway Timeout (O banco de dados pode estar lento)."
    }

    traducao = erros_amigaveis.get(status, f"Erro {status} desconhecido.")
    
    if msg_api:
        raise Exception(f"{traducao}\nDetalhe: {msg_api}")
    else:
        raise Exception(traducao)


def _fazer_requisicao(metodo, url, **kwargs):
    """Wrapper para tratar conexão e timeouts globalmente."""
    try:
        if usa_cookies:
            response = session.request(metodo, url, verify=False, **kwargs)
        else:
            response = requests.request(metodo, url, verify=False, **kwargs)
        if not response.ok:
            _tratar_erro_api(response)
        return response.json() if response.text else {}
    except requests.exceptions.Timeout:
        raise Exception("O servidor demorou muito para responder (Timeout). Verifique a internet.")
    except requests.exceptions.ConnectionError:
        raise Exception("Falha de conexão: O servidor parece estar offline ou o endereço está errado.")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Erro na requisição: {str(e)}")


def carregar_dominios(api_url: str) -> dict:
    url = f"{api_url}/triagem/dominios"
    dados = _fazer_requisicao("GET", url, timeout=10)

    return {
        "marcas": sorted([item["nome"] for item in dados.get("marcas", [])], key=_chave_ordenacao_natural),
        "modelos": sorted([item["nome"] for item in dados.get("modelos", [])], key=_chave_ordenacao_natural),
        "cores": sorted([item["nome"] for item in dados.get("cores", [])], key=_chave_ordenacao_natural),
        "estados_fisicos": _ordenar_por_gravidade([item["nome"] for item in dados.get("estadosFisicos", [])], _HIERARQUIA_ESTADO),
        "condicoes": _ordenar_por_gravidade([item["nome"] for item in dados.get("condicoesFuncionamento", [])], _HIERARQUIA_CONDICAO),
        "acessos": _ordenar_por_gravidade([item["nome"] for item in dados.get("estadosAcesso", [])], _HIERARQUIA_ACESSO),
        "avarias": sorted([item["nome"] for item in dados.get("avarias", [])], key=_chave_ordenacao_natural),
        "caixas": sorted([item["nome"] for item in dados.get("caixasRecebimentos", [])], key=_chave_ordenacao_natural),
    }


def carregar_modelos(api_url: str, marca: str) -> list:
    url = f"{api_url}/triagem/marcas/{marca}/modelos"
    dados = _fazer_requisicao("GET", url, timeout=8)

    lista_real = dados.get("value", dados.get("data", dados)) if isinstance(dados, dict) else dados
    nomes = [item.get("nome", "") for item in lista_real if isinstance(item, dict)]
    return sorted(nomes, key=_chave_ordenacao_natural)


def carregar_modelos_fisicos(api_url: str, modelo: str) -> list:
    url = f"{api_url}/triagem/modelos/{modelo}/modelos-fisicos"
    dados = _fazer_requisicao("GET", url, timeout=8)

    lista_real = dados.get("value", dados.get("data", dados)) if isinstance(dados, dict) else dados
    nomes = [item.get("nome", "") for item in lista_real if isinstance(item, dict)]
    return sorted(nomes, key=_chave_ordenacao_natural)


def salvar_triagem(api_url: str, payload: dict) -> dict:
    url = f"{api_url}/triagem/triagem"
    return _fazer_requisicao("POST", url, json=payload, timeout=15)


def buscar_triagem(api_url: str, item_id: int) -> dict:
    url = f"{api_url}/triagem/triagem/{item_id}"
    return _fazer_requisicao("GET", url, timeout=8)


def atualizar_triagem(api_url: str, item_id: int, payload: dict) -> dict:
    url = f"{api_url}/triagem/triagem/{item_id}"
    return _fazer_requisicao("PUT", url, json=payload, timeout=15)


def cadastrar_avaria(api_url: str, nome: str) -> dict:
    url = f"{api_url}/triagem/avarias"
    payload = {"nome": nome}
    return _fazer_requisicao("POST", url, json=payload, timeout=10)
