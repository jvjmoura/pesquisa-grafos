"""
Tools customizadas do Agno para consultas ao Knowledge Graph Neo4j.

Essas tools são usadas pelo Agente Analista para consultar o grafo
ANTES de gerar qualquer resumo (integração em tempo de inferência).
"""

from __future__ import annotations

import json
import os

from neo4j import GraphDatabase


def _get_driver():
    """Cria um driver Neo4j a partir das variáveis de ambiente."""
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "stf_password_2026")
    return GraphDatabase.driver(uri, auth=(user, password))


def _run_query(query: str, params: dict | None = None) -> list[dict]:
    """Executa query Cypher e retorna resultados."""
    driver = _get_driver()
    try:
        with driver.session() as session:
            result = session.run(query, params or {})
            return [record.data() for record in result]
    finally:
        driver.close()


def buscar_decisao(numero_processo: str) -> str:
    """Busca uma decisão do STF pelo número do processo no Knowledge Graph.

    Args:
        numero_processo: Número do processo (ex: 'HC 161.450', 'RE 1.513.210').

    Returns:
        JSON com dados da decisão: processo, ministro relator, temas, artigos citados,
        voto e dispositivo.
    """
    query = """
    MATCH (p:Processo_STF {numero: $numero})
    OPTIONAL MATCH (p)-[:RELATADO_POR]->(m:Ministro_Relator)
    OPTIONAL MATCH (p)-[:TRATA_DE]->(t:Tema_Repercussao_Geral)
    OPTIONAL MATCH (p)-[:CITA_ARTIGO]->(a:Artigo_Constitucional)
    OPTIONAL MATCH (p)-[:CITA_PRECEDENTE]->(prec:Processo_STF)
    RETURN p.numero AS processo,
           p.classe AS classe,
           p.data_julgamento AS data_julgamento,
           p.voto_texto AS voto,
           p.dispositivo_texto AS dispositivo,
           m.nome AS ministro_relator,
           collect(DISTINCT {numero: t.numero, descricao: t.descricao}) AS temas,
           collect(DISTINCT {artigo: a.artigo, descricao: a.descricao}) AS artigos,
           collect(DISTINCT prec.numero) AS precedentes_citados
    """
    results = _run_query(query, {"numero": numero_processo})

    if not results or results[0].get("processo") is None:
        return json.dumps(
            {"erro": f"Decisão '{numero_processo}' não encontrada no Knowledge Graph."},
            ensure_ascii=False,
        )

    row = results[0]
    # Remove nulos de collect
    row["temas"] = [t for t in row.get("temas", []) if t.get("numero") is not None]
    row["artigos"] = [a for a in row.get("artigos", []) if a.get("artigo") is not None]
    row["precedentes_citados"] = [p for p in row.get("precedentes_citados", []) if p is not None]

    return json.dumps(row, ensure_ascii=False, default=str)


def listar_todas_decisoes() -> str:
    """Lista todas as decisões do STF presentes no Knowledge Graph.

    Returns:
        JSON com lista resumida de todas as decisões: número, classe, ministro relator e data.
    """
    query = """
    MATCH (p:Processo_STF)
    OPTIONAL MATCH (p)-[:RELATADO_POR]->(m:Ministro_Relator)
    RETURN p.numero AS processo,
           p.classe AS classe,
           m.nome AS ministro_relator,
           p.data_julgamento AS data_julgamento
    ORDER BY p.data_julgamento
    """
    results = _run_query(query)
    return json.dumps(results, ensure_ascii=False, default=str)


def buscar_por_tema(descricao_tema: str) -> str:
    """Busca decisões do STF relacionadas a um tema de repercussão geral.

    Args:
        descricao_tema: Termo ou descrição do tema a buscar (busca parcial, case-insensitive).

    Returns:
        JSON com decisões que tratam do tema encontrado.
    """
    query = """
    MATCH (p:Processo_STF)-[:TRATA_DE]->(t:Tema_Repercussao_Geral)
    WHERE toLower(t.descricao) CONTAINS toLower($termo)
    OPTIONAL MATCH (p)-[:RELATADO_POR]->(m:Ministro_Relator)
    RETURN p.numero AS processo,
           p.classe AS classe,
           m.nome AS ministro_relator,
           t.numero AS tema_numero,
           t.descricao AS tema_descricao,
           p.dispositivo_texto AS dispositivo
    """
    results = _run_query(query, {"termo": descricao_tema})

    if not results:
        return json.dumps(
            {"erro": f"Nenhuma decisão encontrada para o tema '{descricao_tema}'."},
            ensure_ascii=False,
        )

    return json.dumps(results, ensure_ascii=False, default=str)


def buscar_por_artigo(artigo: str) -> str:
    """Busca decisões do STF que citam um artigo da Constituição Federal.

    Args:
        artigo: Referência ao artigo constitucional (ex: 'art. 5º', 'art. 225').
                Busca parcial, case-insensitive.

    Returns:
        JSON com decisões que citam o artigo.
    """
    query = """
    MATCH (p:Processo_STF)-[:CITA_ARTIGO]->(a:Artigo_Constitucional)
    WHERE toLower(a.artigo) CONTAINS toLower($artigo)
    OPTIONAL MATCH (p)-[:RELATADO_POR]->(m:Ministro_Relator)
    RETURN p.numero AS processo,
           p.classe AS classe,
           m.nome AS ministro_relator,
           a.artigo AS artigo_citado,
           a.descricao AS artigo_descricao,
           p.dispositivo_texto AS dispositivo
    """
    results = _run_query(query, {"artigo": artigo})

    if not results:
        return json.dumps(
            {"erro": f"Nenhuma decisão encontrada que cite '{artigo}'."},
            ensure_ascii=False,
        )

    return json.dumps(results, ensure_ascii=False, default=str)


def buscar_conexoes_multihop(numero_processo: str) -> str:
    """Identifica conexões multi-hop entre decisões do STF no Knowledge Graph.

    Encontra:
    - Processos que citam o mesmo precedente
    - Processos que tratam do mesmo tema
    - Processos que citam os mesmos artigos constitucionais
    - Processos relatados pelo mesmo ministro
    - Cadeias de precedentes (A cita B, B cita C)

    Args:
        numero_processo: Número do processo de partida (ex: 'HC 161.450').

    Returns:
        JSON com todas as conexões encontradas, organizadas por tipo.
    """
    conexoes: dict = {
        "processo_origem": numero_processo,
        "mesmo_precedente": [],
        "mesmo_tema": [],
        "mesmo_artigo": [],
        "mesmo_relator": [],
        "cadeia_precedentes": [],
    }

    # 1. Processos que citam o mesmo precedente
    q1 = """
    MATCH (p1:Processo_STF {numero: $numero})-[:CITA_PRECEDENTE]->(prec:Processo_STF)<-[:CITA_PRECEDENTE]-(p2:Processo_STF)
    WHERE p1 <> p2
    RETURN p2.numero AS processo, prec.numero AS precedente_comum
    """
    r1 = _run_query(q1, {"numero": numero_processo})
    conexoes["mesmo_precedente"] = r1

    # 2. Processos que tratam do mesmo tema
    q2 = """
    MATCH (p1:Processo_STF {numero: $numero})-[:TRATA_DE]->(t:Tema_Repercussao_Geral)<-[:TRATA_DE]-(p2:Processo_STF)
    WHERE p1 <> p2
    RETURN p2.numero AS processo, t.descricao AS tema_comum
    """
    r2 = _run_query(q2, {"numero": numero_processo})
    conexoes["mesmo_tema"] = r2

    # 3. Processos que citam os mesmos artigos constitucionais
    q3 = """
    MATCH (p1:Processo_STF {numero: $numero})-[:CITA_ARTIGO]->(a:Artigo_Constitucional)<-[:CITA_ARTIGO]-(p2:Processo_STF)
    WHERE p1 <> p2
    RETURN DISTINCT p2.numero AS processo, collect(DISTINCT a.artigo) AS artigos_comuns
    """
    r3 = _run_query(q3, {"numero": numero_processo})
    conexoes["mesmo_artigo"] = r3

    # 4. Processos relatados pelo mesmo ministro
    q4 = """
    MATCH (p1:Processo_STF {numero: $numero})-[:RELATADO_POR]->(m:Ministro_Relator)<-[:RELATADO_POR]-(p2:Processo_STF)
    WHERE p1 <> p2
    RETURN p2.numero AS processo, m.nome AS relator_comum
    """
    r4 = _run_query(q4, {"numero": numero_processo})
    conexoes["mesmo_relator"] = r4

    # 5. Cadeia de precedentes (2 hops)
    q5 = """
    MATCH (p1:Processo_STF {numero: $numero})-[:CITA_PRECEDENTE]->(p2:Processo_STF)-[:CITA_PRECEDENTE]->(p3:Processo_STF)
    RETURN p2.numero AS intermediario, p3.numero AS precedente_indireto
    """
    r5 = _run_query(q5, {"numero": numero_processo})
    conexoes["cadeia_precedentes"] = r5

    # 6. Processos que citam ESTE processo como precedente
    q6 = """
    MATCH (p2:Processo_STF)-[:CITA_PRECEDENTE]->(p1:Processo_STF {numero: $numero})
    RETURN p2.numero AS processo_que_cita
    """
    r6 = _run_query(q6, {"numero": numero_processo})
    conexoes["citado_por"] = r6

    return json.dumps(conexoes, ensure_ascii=False, default=str)


def obter_dados_grafo_completo() -> str:
    """Retorna todos os dados estruturados do Knowledge Graph para validação.

    Usado pelo Agente Revisor para comparar respostas com os dados reais.

    Returns:
        JSON com todos os nós e relações do grafo.
    """
    query = """
    MATCH (p:Processo_STF)
    OPTIONAL MATCH (p)-[:RELATADO_POR]->(m:Ministro_Relator)
    OPTIONAL MATCH (p)-[:TRATA_DE]->(t:Tema_Repercussao_Geral)
    OPTIONAL MATCH (p)-[:CITA_ARTIGO]->(a:Artigo_Constitucional)
    OPTIONAL MATCH (p)-[:CITA_PRECEDENTE]->(prec:Processo_STF)
    RETURN p.numero AS processo,
           p.classe AS classe,
           p.data_julgamento AS data_julgamento,
           p.voto_texto AS voto,
           p.dispositivo_texto AS dispositivo,
           m.nome AS ministro_relator,
           collect(DISTINCT {numero: t.numero, descricao: t.descricao}) AS temas,
           collect(DISTINCT a.artigo) AS artigos_citados,
           collect(DISTINCT prec.numero) AS precedentes_citados
    ORDER BY p.data_julgamento
    """
    results = _run_query(query)

    # Limpa nulos dos collects
    for row in results:
        row["temas"] = [t for t in row.get("temas", []) if t.get("numero") is not None]
        row["artigos_citados"] = [a for a in row.get("artigos_citados", []) if a is not None]
        row["precedentes_citados"] = [p for p in row.get("precedentes_citados", []) if p is not None]

    return json.dumps(results, ensure_ascii=False, default=str)
