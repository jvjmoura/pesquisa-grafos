"""
Entry point interativo do sistema de análise de decisões do STF.

Uso:
  # Modo interativo (chat com o time de agentes):
  python main.py

  # Pergunta única:
  python main.py --query "Quais decisões citam o art. 5º da Constituição?"

  # Usar apenas o agente analista (sem revisão):
  python main.py --analyst-only

  # Usar apenas o agente revisor para testar uma resposta:
  python main.py --review "Texto a ser revisado..."

  # Ver relatório agregado de qualidade:
  python main.py --quality-report
"""

from __future__ import annotations

import argparse
import sys

from dotenv import load_dotenv

load_dotenv()

from rich.console import Console
from rich.panel import Panel

from src.agents.analyst_agent import create_analyst_agent
from src.agents.reviewer_agent import create_reviewer_agent
from src.agents.team import create_stf_team
from src.graph.neo4j_client import Neo4jClient

console = Console()


def check_neo4j() -> bool:
    """Verifica conexão com Neo4j e se há dados."""
    try:
        with Neo4jClient() as client:
            if not client.verify_connection():
                return False
            count = client.get_node_count()
            if count == 0:
                console.print(
                    "[yellow]⚠ Neo4j conectado mas sem dados. "
                    "Execute primeiro:[/yellow]\n"
                    "  python -m scripts.ingest --pdf-dir data/decisions"
                )
                return False
            console.print(f"[green]✓ Neo4j conectado ({count} nós no Knowledge Graph)[/green]")
            return True
    except Exception as e:
        console.print(f"[red]✗ Erro ao conectar ao Neo4j: {e}[/red]")
        console.print("  Verifique as credenciais no arquivo .env")
        return False


def run_interactive(use_team: bool = True) -> None:
    """Modo interativo de chat."""
    if use_team:
        agent = create_stf_team()
        title = "Equipe de Análise STF (Analista + Revisor)"
    else:
        agent = create_analyst_agent()
        title = "Agente Analista STF"

    console.print(
        Panel(
            f"[bold cyan]{title}[/bold cyan]\n\n"
            "Faça perguntas sobre as 4 decisões do STF mapeadas no Knowledge Graph.\n"
            "Digite [bold]'sair'[/bold] ou [bold]'exit'[/bold] para encerrar.\n\n"
            "[dim]Exemplos de perguntas:[/dim]\n"
            "  • Resuma a decisão HC 161.450\n"
            "  • Quais decisões citam o art. 5º da CF?\n"
            "  • Quais conexões existem entre as decisões sobre direitos fundamentais?\n"
            "  • Que processos citam o mesmo precedente?",
            title="[bold]Sistema Neuro-Simbólico de Análise Jurídica[/bold]",
            border_style="cyan",
        )
    )

    while True:
        try:
            query = console.input("\n[bold green]Você:[/bold green] ").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if not query:
            continue
        if query.lower() in ("sair", "exit", "quit", "q"):
            break

        console.print("\n[dim]Processando...[/dim]\n")

        try:
            response = agent.run(query)
            if response and response.content:
                print(response.content)
            else:
                console.print("[yellow]Nenhuma resposta gerada.[/yellow]")
        except Exception as e:
            console.print(f"[red]Erro: {e}[/red]")

    console.print("\n[dim]Encerrando...[/dim]")


def run_single_query(query: str, use_team: bool = True) -> None:
    """Executa uma pergunta única."""
    if use_team:
        agent = create_stf_team()
    else:
        agent = create_analyst_agent()

    console.print(f"\n[bold green]Pergunta:[/bold green] {query}\n")
    console.print("[dim]Processando...[/dim]\n")

    try:
        response = agent.run(query)
        if response and response.content:
            print(response.content)
        else:
            console.print("[yellow]Nenhuma resposta gerada.[/yellow]")
    except Exception as e:
        console.print(f"[red]Erro: {e}[/red]")


def run_review(text: str) -> None:
    """Executa revisão de um texto com o Agente Revisor."""
    reviewer = create_reviewer_agent()

    prompt = (
        "Revise a seguinte resposta, verificando se todas as afirmações "
        "estão fundamentadas nos dados do Knowledge Graph:\n\n"
        f"{text}"
    )

    console.print("\n[bold yellow]Revisando resposta...[/bold yellow]\n")

    try:
        response = reviewer.run(prompt)
        if response and response.content:
            print(response.content)
        else:
            console.print("[yellow]Nenhuma resposta gerada.[/yellow]")
    except Exception as e:
        console.print(f"[red]Erro: {e}[/red]")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sistema Neuro-Simbólico de Análise de Decisões do STF"
    )
    parser.add_argument(
        "--query", "-q",
        type=str,
        help="Pergunta única (sem modo interativo)",
    )
    parser.add_argument(
        "--analyst-only",
        action="store_true",
        help="Usar apenas o Agente Analista (sem revisão)",
    )
    parser.add_argument(
        "--review",
        type=str,
        help="Texto para revisão pelo Agente Revisor",
    )
    parser.add_argument(
        "--skip-check",
        action="store_true",
        help="Pular verificação de conexão com Neo4j",
    )
    parser.add_argument(
        "--quality-report",
        action="store_true",
        help="Exibe relatório agregado de qualidade das revisões",
    )
    args = parser.parse_args()

    console.print("\n[bold]Sistema Neuro-Simbólico de Análise de Decisões do STF[/bold]")
    console.print("[dim]Agno + Docling + Neo4j | QuaLLM-KG Context Engineering[/dim]\n")

    if not args.skip_check:
        if not check_neo4j():
            sys.exit(1)

    if args.quality_report:
        from src.quality.monitor import print_quality_report
        print_quality_report()
        return

    if args.review:
        run_review(args.review)
    elif args.query:
        run_single_query(args.query, use_team=not args.analyst_only)
    else:
        run_interactive(use_team=not args.analyst_only)


if __name__ == "__main__":
    main()
