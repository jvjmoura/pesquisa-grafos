"""
Quality Monitor: extrai métricas estruturadas da revisão e mantém log acumulativo.

Implementa o princípio de Quality-by-Design do QuaLLM-KG (Karki et al., 2026):
monitoramento quantitativo da fidelidade das respostas ao Knowledge Graph.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class QualityMetrics:
    """Métricas de qualidade extraídas da revisão."""
    validado: bool = False
    score_fidelidade: float = 0.0
    total_afirmacoes: int = 0
    verificadas_ok: int = 0
    sem_fundamentacao: int = 0
    processos_verificados: list[str] = field(default_factory=list)
    problemas: list[str] = field(default_factory=list)


@dataclass
class QualityLogEntry:
    """Entrada completa do log de qualidade."""
    timestamp: str
    query: str
    metrics: QualityMetrics
    analyst_chars: int = 0
    reviewer_chars: int = 0


LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "quality_log.jsonl"


def parse_metrics_from_review(reviewer_text: str) -> QualityMetrics:
    """Extrai o bloco quality_metrics JSON da resposta do Revisor.

    Procura um bloco delimitado por ```quality_metrics ... ``` na resposta.
    Se não encontrar, tenta extrair um bloco JSON genérico.

    Returns:
        QualityMetrics com os valores extraídos, ou defaults se parsing falhar.
    """
    # Tenta extrair bloco ```quality_metrics ... ```
    pattern = r"```quality_metrics\s*\n?(.*?)\n?```"
    match = re.search(pattern, reviewer_text, re.DOTALL)

    if not match:
        # Fallback: tenta extrair qualquer bloco JSON com score_fidelidade
        pattern = r"```(?:json)?\s*\n?(\{[^}]*score_fidelidade[^}]*\})\n?```"
        match = re.search(pattern, reviewer_text, re.DOTALL)

    if not match:
        # Último fallback: procura JSON inline
        pattern = r'(\{"validado".*?"problemas"\s*:\s*\[.*?\]\s*\})'
        match = re.search(pattern, reviewer_text, re.DOTALL)

    if not match:
        return QualityMetrics()

    try:
        data = json.loads(match.group(1).strip())
        return QualityMetrics(
            validado=data.get("validado", False),
            score_fidelidade=float(data.get("score_fidelidade", 0.0)),
            total_afirmacoes=int(data.get("total_afirmacoes", 0)),
            verificadas_ok=int(data.get("verificadas_ok", 0)),
            sem_fundamentacao=int(data.get("sem_fundamentacao", 0)),
            processos_verificados=data.get("processos_verificados", []),
            problemas=data.get("problemas", []),
        )
    except (json.JSONDecodeError, ValueError, TypeError):
        return QualityMetrics()


def log_quality(
    query: str,
    metrics: QualityMetrics,
    analyst_text: str = "",
    reviewer_text: str = "",
    checker_result: object | None = None,
) -> None:
    """Salva uma entrada no log acumulativo de qualidade (JSONL)."""
    LOG_DIR.mkdir(exist_ok=True)

    entry = QualityLogEntry(
        timestamp=datetime.now().isoformat(),
        query=query,
        metrics=metrics,
        analyst_chars=len(analyst_text),
        reviewer_chars=len(reviewer_text),
    )

    entry_dict = asdict(entry)
    if checker_result is not None:
        from src.quality.checker import checker_result_to_dict
        entry_dict["checker"] = checker_result_to_dict(checker_result)

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry_dict, ensure_ascii=False) + "\n")


def format_quality_summary(metrics: QualityMetrics) -> str:
    """Formata um resumo legível das métricas de qualidade."""
    status = "✅ Validado" if metrics.validado else "⚠️ Problemas encontrados"
    score = f"{metrics.score_fidelidade:.1f}%"

    summary = (
        f"\n{'=' * 50}\n"
        f"📊 Quality Score: {score} "
        f"({metrics.verificadas_ok}/{metrics.total_afirmacoes} afirmações verificadas)\n"
        f"   Status: {status}\n"
        f"   Processos verificados: {', '.join(metrics.processos_verificados) or 'N/A'}"
    )

    if metrics.problemas:
        summary += "\n   Problemas:"
        for p in metrics.problemas:
            summary += f"\n     - {p}"

    summary += f"\n{'=' * 50}"
    return summary


def load_quality_log() -> list[QualityLogEntry]:
    """Carrega todo o log de qualidade para análise."""
    if not LOG_FILE.exists():
        return []

    entries = []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    data = json.loads(line)
                    metrics = QualityMetrics(**data.get("metrics", {}))
                    entry = QualityLogEntry(
                        timestamp=data["timestamp"],
                        query=data["query"],
                        metrics=metrics,
                        analyst_chars=data.get("analyst_chars", 0),
                        reviewer_chars=data.get("reviewer_chars", 0),
                    )
                    entries.append(entry)
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
    return entries


def print_quality_report() -> None:
    """Imprime um relatório agregado de todas as queries logadas."""
    entries = load_quality_log()
    if not entries:
        print("Nenhuma entrada no log de qualidade.")
        return

    scores = [e.metrics.score_fidelidade for e in entries]
    total_claims = sum(e.metrics.total_afirmacoes for e in entries)
    total_ok = sum(e.metrics.verificadas_ok for e in entries)
    total_problems = sum(e.metrics.sem_fundamentacao for e in entries)

    print(f"\n{'=' * 60}")
    print("📊 RELATÓRIO AGREGADO DE QUALIDADE")
    print(f"{'=' * 60}")
    print(f"  Total de queries analisadas: {len(entries)}")
    print(f"  Score médio de fidelidade:   {sum(scores) / len(scores):.1f}%")
    print(f"  Score mínimo:                {min(scores):.1f}%")
    print(f"  Score máximo:                {max(scores):.1f}%")
    print(f"  Total de afirmações:         {total_claims}")
    print(f"  Afirmações verificadas OK:   {total_ok}")
    print(f"  Afirmações sem fundamento:   {total_problems}")
    validated = sum(1 for e in entries if e.metrics.validado)
    print(f"  Queries validadas:           {validated}/{len(entries)}")
    print(f"{'=' * 60}")
