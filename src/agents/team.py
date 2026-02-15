"""
Orquestração do time de agentes: Analista + Revisor + Checker + Quality Monitor.

Pipeline sequencial determinístico:
1. Analista consulta o KG e gera a resposta
2. Revisor LLM valida a resposta contra os dados do grafo
3. Checker Determinístico verifica claims via Cypher direto
4. Quality Monitor extrai métricas, compara verificadores e loga resultados
"""

from __future__ import annotations

from dataclasses import dataclass

from src.agents.analyst_agent import create_analyst_agent
from src.agents.reviewer_agent import create_reviewer_agent
from src.quality.checker import comparar_com_llm, run_checker
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
    """Pipeline sequencial: Analista → Revisor → Checker → Quality Monitor."""

    def __init__(self):
        self.analyst = create_analyst_agent()
        self.reviewer = create_reviewer_agent()

    def run(self, query: str) -> TeamResponse:
        """Executa o pipeline Analista → Revisor → Checker → Quality Monitor.

        1. O Analista consulta o KG e responde à pergunta.
        2. O Revisor LLM verifica se a resposta está fundamentada no KG.
        3. O Checker Determinístico valida claims via Cypher direto.
        4. O Quality Monitor compara verificadores, extrai métricas e loga.
        """
        # Passo 1: Analista consulta o KG
        print("  [Passo 1/4] Agente Analista consultando Knowledge Graph...")
        analyst_response = self.analyst.run(query)
        analyst_text = analyst_response.content if analyst_response and analyst_response.content else ""

        if not analyst_text:
            return TeamResponse(content="O Agente Analista não gerou resposta.")

        # Passo 2: Revisor LLM verifica a resposta
        print("  [Passo 2/4] Agente Revisor verificando fidelidade ao KG...")
        review_prompt = (
            "Revise a seguinte resposta do Agente Analista, verificando se TODAS "
            "as afirmações estão fundamentadas nos dados do Knowledge Graph das "
            "decisões do STF. Use suas tools para consultar o grafo.\n\n"
            f"=== RESPOSTA DO ANALISTA ===\n{analyst_text}"
        )
        reviewer_response = self.reviewer.run(review_prompt)
        reviewer_text = reviewer_response.content if reviewer_response and reviewer_response.content else ""

        # Passo 3: Checker Determinístico valida via Cypher
        print("  [Passo 3/4] Checker Determinístico verificando via Cypher...")
        checker_result = run_checker(analyst_text, query)

        # Passo 4: Quality Monitor extrai métricas e compara
        print("  [Passo 4/4] Quality Monitor comparando verificadores...")
        metrics = parse_metrics_from_review(reviewer_text)
        log_quality(query, metrics, analyst_text, reviewer_text, checker_result)
        quality_summary = format_quality_summary(metrics)
        comparison = comparar_com_llm(checker_result, metrics.score_fidelidade)

        # Monta resposta final
        final = f"## Análise do Agente Analista\n\n{analyst_text}"
        if reviewer_text:
            final += f"\n\n---\n\n## Revisão do Agente Revisor\n\n{reviewer_text}"
        final += f"\n\n{quality_summary}"
        final += f"\n\n{comparison}"

        return TeamResponse(content=final)


def create_stf_team() -> STFTeam:
    """Cria e retorna o pipeline sequencial Analista + Revisor + Quality Monitor."""
    return STFTeam()
