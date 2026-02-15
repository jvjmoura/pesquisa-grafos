"""
Pipeline de ingestão: PDF → Docling Extraction → Neo4j Knowledge Graph.

Uso:
  python -m scripts.ingest --pdf-dir data/decisions
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from src.graph.neo4j_client import Neo4jClient
from src.graph.schema import create_schema, ingest_all


def ingest_from_pdfs(client: Neo4jClient, pdf_dir: str) -> None:
    """Extrai PDFs com Docling e usa LLM para identificar metadados estruturados."""
    from src.extraction.docling_extractor import extract_all_from_directory
    from src.extraction.llm_metadata_extractor import extract_metadata_from_text
    from src.models.schemas import DecisaoSTF

    pdf_path = Path(pdf_dir)
    if not pdf_path.is_dir():
        print(f"[ERRO] Diretório não encontrado: {pdf_dir}")
        sys.exit(1)

    print(f"\n[1/5] Extraindo texto dos PDFs de {pdf_dir} com Docling...")
    extractions = extract_all_from_directory(pdf_path)
    print(f"  {len(extractions)} PDFs processados pelo Docling.")

    print("[2/5] Criando schema no Neo4j...")
    create_schema(client)

    print("[3/5] Limpando dados anteriores...")
    client.clear_database()
    create_schema(client)

    print("[4/5] Extraindo metadados estruturados via LLM (OpenAI)...")
    decisions: list[DecisaoSTF] = []
    for ext in extractions:
        print(f"  Processando: {ext.arquivo}")
        print(f"    Docling → Texto: {len(ext.texto_completo)} chars | "
              f"Voto: {len(ext.voto)} chars | Dispositivo: {len(ext.dispositivo)} chars")
        try:
            decision = extract_metadata_from_text(
                full_text=ext.texto_completo,
                voto_text=ext.voto,
                dispositivo_text=ext.dispositivo,
                filename=ext.arquivo,
            )
            decisions.append(decision)
            print(f"    LLM → Processo: {decision.numero_processo} | "
                  f"Classe: {decision.classe} | "
                  f"Relator: {decision.ministro_relator.nome}")
            print(f"    LLM → Temas: {len(decision.temas)} | "
                  f"Artigos: {len(decision.artigos_citados)} | "
                  f"Precedentes: {len(decision.precedentes_citados)}")
        except Exception as e:
            print(f"    [ERRO] Falha na extração de metadados: {e}")

    print(f"\n[5/5] Ingerindo {len(decisions)} decisões no Knowledge Graph...")
    count = ingest_all(client, decisions)

    total_nodes = client.get_node_count()
    print(f"\n✓ {count} decisões ingeridas com sucesso.")
    print(f"✓ {total_nodes} nós criados no Knowledge Graph.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pipeline de ingestão de decisões do STF no Knowledge Graph"
    )
    parser.add_argument(
        "--pdf-dir",
        type=str,
        default="data/decisions",
        help="Diretório com PDFs das decisões do STF",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Limpa o banco antes de ingerir",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  Pipeline de Ingestão – Decisões do STF → Knowledge Graph")
    print("=" * 60)

    with Neo4jClient() as client:
        if not client.verify_connection():
            print("\n[ERRO] Não foi possível conectar ao Neo4j.")
            print("Verifique as credenciais no arquivo .env")
            sys.exit(1)

        print("✓ Conectado ao Neo4j.")

        if args.clear:
            print("Limpando banco...")
            client.clear_database()

        ingest_from_pdfs(client, args.pdf_dir)

    print("\n" + "=" * 60)
    print("  Ingestão concluída!")
    print("=" * 60)


if __name__ == "__main__":
    main()
