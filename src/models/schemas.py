"""Modelos Pydantic para o sistema de análise de decisões do STF."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MinistroRelator(BaseModel):
    nome: str = Field(..., description="Nome do Ministro Relator")


class TemaRepercussaoGeral(BaseModel):
    numero: int = Field(..., description="Número do Tema de Repercussão Geral")
    descricao: str = Field(..., description="Descrição do tema")


class ArtigoConstitucional(BaseModel):
    artigo: str = Field(..., description="Artigo da CF/88 citado (ex: 'art. 5º, XXXV')")
    descricao: str = Field(default="", description="Descrição resumida do artigo")


class DecisaoSTF(BaseModel):
    numero_processo: str = Field(..., description="Número do processo (ex: 'HC 161.450')")
    classe: str = Field(..., description="Classe processual (RE, ADI, ADPF, etc.)")
    ministro_relator: MinistroRelator
    data_julgamento: str = Field(..., description="Data do julgamento (YYYY-MM-DD)")
    temas: list[TemaRepercussaoGeral] = Field(default_factory=list)
    artigos_citados: list[ArtigoConstitucional] = Field(default_factory=list)
    precedentes_citados: list[str] = Field(
        default_factory=list,
        description="Números de processos citados como precedente",
    )
    voto_texto: str = Field(default="", description="Texto extraído do Voto")
    dispositivo_texto: str = Field(default="", description="Texto extraído do Dispositivo")


class ExtractionResult(BaseModel):
    """Resultado da extração de um PDF via Docling."""
    arquivo: str
    texto_completo: str
    voto: str
    dispositivo: str
    metadata: dict = Field(default_factory=dict)


