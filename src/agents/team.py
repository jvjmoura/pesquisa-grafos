"""
Orquestração do time de agentes: Analista + Revisor + Quality Monitor.

Pipeline sequencial determinístico:
1. Analista consulta o KG e gera a resposta
2. Revisor valida a resposta contra os dados do grafo
3. Quality Monitor extrai métricas, exibe score e loga resultados
"""

from __future__ import annotations

from dataclasses import dataclass

from src.agents.analyst_agent import create_analyst_agent
from src.agents.reviewer_agent import create_reviewer_agent
from src.quality.monitor import (
    format_quality_summary,
    log_quality,
    parse_metrics_from_review,
)


@dataclass
class TeamResponse:
    """Resposta do time com análise, revisão e métricas."""
    content: str


class STFTeam:
    """Pipeline sequencial: Analista → Revisor → Quality Monitor."""

    def __init__(self):
        self.analyst = create_analyst_agent()
        self.reviewer = create_reviewer_agent()

    def run(self, query: str) -> TeamResponse:
        """Executa o pipeline Analista → Revisor → Quality Monitor.

        1. O Analista consulta o KG e responde à pergunta.
        2. O Revisor verifica se a resposta está fundamentada no KG.
        3. O Quality Monitor extrai métricas, loga e exibe o score.
        """
        # Passo 1: Analista consulta o KG
        print("  [Passo 1/3] Agente Analista consultando Knowledge Graph...")
        analyst_response = self.analyst.run(query)
        analyst_text = analyst_response.content if analyst_response and analyst_response.content else ""

        if not analyst_text:
            return TeamResponse(content="O Agente Analista não gerou resposta.")

        # Passo 2: Revisor verifica a resposta
        print("  [Passo 2/3] Agente Revisor verificando fidelidade ao KG...")
        review_prompt = (
            "Revise a seguinte resposta do Agente Analista, verificando se TODAS "
            "as afirmações estão fundamentadas nos dados do Knowledge Graph das "
            "decisões do STF. Use suas tools para consultar o grafo.\n\n"
            f"=== RESPOSTA DO ANALISTA ===\n{analyst_text}"
        )
        reviewer_response = self.reviewer.run(review_prompt)
        reviewer_text = reviewer_response.content if reviewer_response and reviewer_response.content else ""

        # Passo 3: Quality Monitor extrai métricas e loga
        print("  [Passo 3/3] Quality Monitor extraindo métricas...")
        metrics = parse_metrics_from_review(reviewer_text)
        log_quality(query, metrics, analyst_text, reviewer_text)
        quality_summary = format_quality_summary(metrics)

        # Monta resposta final
        final = f"## Análise do Agente Analista\n\n{analyst_text}"
        if reviewer_text:
            final += f"\n\n---\n\n## Revisão do Agente Revisor\n\n{reviewer_text}"
        final += f"\n\n{quality_summary}"

        return TeamResponse(content=final)


def create_stf_team() -> STFTeam:
    """Cria e retorna o pipeline sequencial Analista + Revisor + Quality Monitor."""
    return STFTeam()
