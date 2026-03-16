from typing import List, Optional, Any, Dict
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests

app = FastAPI(
    title="Middleware TJDFT Jurisprudência",
    version="1.0.1",
    description="Middleware para traduzir consultas simples em chamadas compatíveis com a API pública de jurisprudência do TJDFT.",
    servers=[
        {
            "url": "https://middleware-tjdft-gpt.onrender.com",
            "description": "Produção"
        }
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TJDFT_API_URL = "https://jurisdf.tjdft.jus.br/api/v1/pesquisa"


def adicionar_filtro(termos_acessorios: List[Dict[str, Any]], campo: str, valor: Optional[str]):
    if valor is not None and str(valor).strip() != "":
        termos_acessorios.append({
            "campo": campo,
            "valor": valor
        })


@app.get("/")
def raiz():
    return {
        "ok": True,
        "mensagem": "Middleware TJDFT no ar.",
        "docs": "/docs",
        "openapi": "/openapi.json",
        "endpoint_principal": "/tjdft/jurisprudencia"
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/tjdft/jurisprudencia")
def pesquisar_jurisprudencia(
    q: str = Query(..., description="Termo principal da pesquisa"),
    pagina: int = Query(0, ge=0, description="Número da página, começando em 0"),
    tamanho: int = Query(10, ge=1, le=50, description="Quantidade de resultados por página"),
    processo: Optional[str] = Query(None, description="Número do processo"),
    relator: Optional[str] = Query(None, description="Nome do relator"),
    revisor: Optional[str] = Query(None, description="Nome do revisor"),
    relator_designado: Optional[str] = Query(None, description="Nome do relator designado"),
    orgao_julgador: Optional[str] = Query(None, description="Descrição do órgão julgador"),
    classe_cnj: Optional[str] = Query(None, description="Classe processual CNJ"),
    data_julgamento: Optional[str] = Query(None, description="Data do julgamento no formato YYYY-MM-DD"),
    data_publicacao: Optional[str] = Query(None, description="Data da publicação no formato YYYY-MM-DD"),
    base: Optional[str] = Query(None, description="Base de dados da decisão"),
    subbase: Optional[str] = Query(None, description="Subbase de dados"),
    origem: Optional[str] = Query(None, description="Origem da decisão"),
    uuid: Optional[str] = Query(None, description="UUID da decisão"),
    identificador: Optional[str] = Query(None, description="Identificador da decisão"),
):
    termos_acessorios: List[Dict[str, Any]] = []

    adicionar_filtro(termos_acessorios, "processo", processo)
    adicionar_filtro(termos_acessorios, "nomeRelator", relator)
    adicionar_filtro(termos_acessorios, "nomeRevisor", revisor)
    adicionar_filtro(termos_acessorios, "nomeRelatorDesignado", relator_designado)
    adicionar_filtro(termos_acessorios, "descricaoOrgaoJulgador", orgao_julgador)
    adicionar_filtro(termos_acessorios, "descricaoClasseCnj", classe_cnj)
    adicionar_filtro(termos_acessorios, "dataJulgamento", data_julgamento)
    adicionar_filtro(termos_acessorios, "dataPublicacao", data_publicacao)
    adicionar_filtro(termos_acessorios, "base", base)
    adicionar_filtro(termos_acessorios, "subbase", subbase)
    adicionar_filtro(termos_acessorios, "origem", origem)
    adicionar_filtro(termos_acessorios, "uuid", uuid)
    adicionar_filtro(termos_acessorios, "identificador", identificador)

    payload: Dict[str, Any] = {
        "query": q,
        "pagina": pagina,
        "tamanho": tamanho
    }

    if termos_acessorios:
        payload["termosAcessorios"] = termos_acessorios

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    try:
        resposta = requests.post(
            TJDFT_API_URL,
            json=payload,
            headers=headers,
            timeout=60
        )
        resposta.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=502,
            detail=f"Erro ao consultar a API do TJDFT: {str(e)}"
        )

    try:
        dados = resposta.json()
    except ValueError:
        raise HTTPException(
            status_code=502,
            detail="A API do TJDFT retornou uma resposta que não é JSON válido."
        )

    registros = dados.get("registros", [])
    resultados_limpos = []

    for item in registros:
        resultados_limpos.append({
            "sequencial": item.get("sequencial"),
            "base": item.get("base"),
            "subbase": item.get("subbase"),
            "uuid": item.get("uuid"),
            "identificador": item.get("identificador"),
            "processo": item.get("processo"),
            "relator": item.get("nomeRelator"),
            "revisor": item.get("nomeRevisor"),
            "relator_designado": item.get("nomeRelatorDesignado"),
            "orgao_julgador": item.get("descricaoOrgaoJulgador"),
            "descricao_orgao": item.get("descricaoOrgao"),
            "data_publicacao": item.get("dataPublicacao"),
            "ementa": item.get("ementa"),
            "inteiro_teor": item.get("inteiroTeor"),
            "possui_inteiro_teor": item.get("possuiInteiroTeor"),
            "versao": item.get("versao"),
            "codigo_classe_cnj": item.get("codigoClasseCnj"),
            "codigo_sistj_orgao_julgador": item.get("codigoSistjOrgaoJulgador"),
            "marcadores": item.get("marcadores"),
            "jurisprudencia_em_foco": item.get("jurisprudenciaEmFoco"),
        })

    return {
        "fonte": "TJDFT",
        "termo_pesquisado": q,
        "pagina": pagina,
        "tamanho": tamanho,
        "total_resultados": dados.get("hits"),
        "agregacoes": dados.get("agregações", {}),
        "paginacao": dados.get("paginação", {}),
        "quantidade_resultados_na_pagina": len(resultados_limpos),
        "resultados": resultados_limpos,
        "payload_enviado_ao_tjdft": payload
    }
