"""
Agente Analista: consulta o Knowledge Graph Neo4j ANTES de gerar resumos.

Segue o princípio de integração em tempo de inferência do QuaLLM-KG:
o agente DEVE consultar o grafo para fundamentar cada afirmação.
"""

from __future__ import annotations

import os

from agno.agent import Agent
from agno.models.openai import OpenAIChat

from src.tools.graph_tools import (
    buscar_conexoes_multihop,
    buscar_decisao,
    buscar_por_artigo,
    buscar_por_tema,
    listar_todas_decisoes,
)

ANALYST_INSTRUCTIONS = [
    "Você é um analista jurídico especializado em decisões do Supremo Tribunal Federal (STF).",
    "",
    "REGRAS OBRIGATÓRIAS:",
    "1. ANTES de responder qualquer pergunta, você DEVE consultar o Knowledge Graph usando suas tools.",
    "2. NUNCA afirme algo que não esteja fundamentado nos dados retornados pelas tools.",
    "3. Se a informação não estiver no grafo, diga explicitamente: 'Esta informação não consta nas 4 decisões mapeadas.'",
    "4. Ao citar uma decisão, SEMPRE inclua: número do processo, ministro relator e classe processual.",
    "5. Ao analisar conexões entre decisões, use a tool 'buscar_conexoes_multihop' para identificar:",
    "   - Processos que citam o mesmo precedente",
    "   - Processos sobre o mesmo tema de repercussão geral",
    "   - Processos que citam os mesmos artigos constitucionais",
    "   - Cadeias de precedentes",
    "",
    "FLUXO DE TRABALHO:",
    "a) Para perguntas sobre uma decisão específica: use 'buscar_decisao' com o número do processo.",
    "b) Para perguntas sobre temas: use 'buscar_por_tema'.",
    "c) Para perguntas sobre artigos da CF: use 'buscar_por_artigo'.",
    "d) Para perguntas sobre relações entre decisões: use 'buscar_conexoes_multihop'.",
    "e) Para visão geral: use 'listar_todas_decisoes' primeiro.",
    "",
    "FORMATO DA RESPOSTA:",
    "- Estruture em seções claras com markdown.",
    "- Cite explicitamente os dados do grafo que fundamentam cada afirmação.",
    "- Ao final, liste as fontes consultadas (processos e dados do KG usados).",
    "",
    "Responda sempre em português brasileiro.",
]


def create_analyst_agent() -> Agent:
    """Cria e retorna o Agente Analista configurado."""
    model_id = os.getenv("OPENAI_MODEL_ID", "gpt-4o")

    return Agent(
        name="Analista Jurídico STF",
        role="Analisa decisões do STF com base exclusiva nos dados do Knowledge Graph",
        model=OpenAIChat(id=model_id),
        tools=[
            buscar_decisao,
            listar_todas_decisoes,
            buscar_por_tema,
            buscar_por_artigo,
            buscar_conexoes_multihop,
        ],
        instructions=ANALYST_INSTRUCTIONS,
        add_datetime_to_context=True,
        markdown=True,
    )
