"""
Schema do Knowledge Graph e funções de ingestão de dados no Neo4j.

Schema:
  (:Processo_STF {numero, classe, voto_texto, dispositivo_texto, data_julgamento})
  (:Ministro_Relator {nome})
  (:Tema_Repercussao_Geral {numero, descricao})
  (:Artigo_Constitucional {artigo, descricao})

  (Processo_STF)-[:RELATADO_POR]->(Ministro_Relator)
  (Processo_STF)-[:TRATA_DE]->(Tema_Repercussao_Geral)
  (Processo_STF)-[:CITA_ARTIGO]->(Artigo_Constitucional)
  (Processo_STF)-[:CITA_PRECEDENTE]->(Processo_STF)
"""

from __future__ import annotations

from src.graph.neo4j_client import Neo4jClient
from src.models.schemas import DecisaoSTF


CONSTRAINTS_AND_INDEXES = [
    "CREATE CONSTRAINT processo_numero IF NOT EXISTS FOR (p:Processo_STF) REQUIRE p.numero IS UNIQUE",
    "CREATE CONSTRAINT ministro_nome IF NOT EXISTS FOR (m:Ministro_Relator) REQUIRE m.nome IS UNIQUE",
    "CREATE CONSTRAINT tema_numero IF NOT EXISTS FOR (t:Tema_Repercussao_Geral) REQUIRE t.numero IS UNIQUE",
    "CREATE CONSTRAINT artigo_id IF NOT EXISTS FOR (a:Artigo_Constitucional) REQUIRE a.artigo IS UNIQUE",
    "CREATE INDEX processo_classe IF NOT EXISTS FOR (p:Processo_STF) ON (p.classe)",
    "CREATE INDEX processo_data IF NOT EXISTS FOR (p:Processo_STF) ON (p.data_julgamento)",
]


def create_schema(client: Neo4jClient) -> None:
    """Cria constraints e índices no Neo4j."""
    for stmt in CONSTRAINTS_AND_INDEXES:
        try:
            client.run_write(stmt)
        except Exception as e:
            # Ignora se constraint/index já existe
            if "already exists" not in str(e).lower():
                raise


def ingest_decision(client: Neo4jClient, decisao: DecisaoSTF) -> None:
    """Ingere uma decisão do STF no Knowledge Graph.

    Cria nós e relações para: Processo, Ministro, Temas, Artigos e Precedentes.
    """
    # 1. Cria nó Processo_STF
    client.run_write(
        """
        MERGE (p:Processo_STF {numero: $numero})
        SET p.classe = $classe,
            p.voto_texto = $voto,
            p.dispositivo_texto = $dispositivo,
            p.data_julgamento = $data
        """,
        {
            "numero": decisao.numero_processo,
            "classe": decisao.classe,
            "voto": decisao.voto_texto,
            "dispositivo": decisao.dispositivo_texto,
            "data": decisao.data_julgamento,
        },
    )

    # 2. Cria nó Ministro_Relator e relação RELATADO_POR
    client.run_write(
        """
        MERGE (m:Ministro_Relator {nome: $nome})
        WITH m
        MATCH (p:Processo_STF {numero: $numero})
        MERGE (p)-[:RELATADO_POR]->(m)
        """,
        {
            "nome": decisao.ministro_relator.nome,
            "numero": decisao.numero_processo,
        },
    )

    # 3. Cria nós Tema_Repercussao_Geral e relações TRATA_DE
    for tema in decisao.temas:
        client.run_write(
            """
            MERGE (t:Tema_Repercussao_Geral {numero: $tema_numero})
            SET t.descricao = $descricao
            WITH t
            MATCH (p:Processo_STF {numero: $numero})
            MERGE (p)-[:TRATA_DE]->(t)
            """,
            {
                "tema_numero": tema.numero,
                "descricao": tema.descricao,
                "numero": decisao.numero_processo,
            },
        )

    # 4. Cria nós Artigo_Constitucional e relações CITA_ARTIGO
    for artigo in decisao.artigos_citados:
        client.run_write(
            """
            MERGE (a:Artigo_Constitucional {artigo: $artigo})
            SET a.descricao = $descricao
            WITH a
            MATCH (p:Processo_STF {numero: $numero})
            MERGE (p)-[:CITA_ARTIGO]->(a)
            """,
            {
                "artigo": artigo.artigo,
                "descricao": artigo.descricao,
                "numero": decisao.numero_processo,
            },
        )

    # 5. Cria relações CITA_PRECEDENTE entre processos
    for precedente_numero in decisao.precedentes_citados:
        client.run_write(
            """
            MERGE (prec:Processo_STF {numero: $prec_numero})
            WITH prec
            MATCH (p:Processo_STF {numero: $numero})
            MERGE (p)-[:CITA_PRECEDENTE]->(prec)
            """,
            {
                "prec_numero": precedente_numero,
                "numero": decisao.numero_processo,
            },
        )


def ingest_all(client: Neo4jClient, decisoes: list[DecisaoSTF]) -> int:
    """Ingere uma lista de decisões no Knowledge Graph.

    Args:
        client: Cliente Neo4j.
        decisoes: Lista de decisões a serem ingeridas.

    Returns:
        Número de decisões ingeridas com sucesso.
    """
    count = 0
    for decisao in decisoes:
        try:
            ingest_decision(client, decisao)
            count += 1
            print(f"  [OK] {decisao.numero_processo}")
        except Exception as e:
            print(f"  [ERRO] {decisao.numero_processo}: {e}")
    return count
