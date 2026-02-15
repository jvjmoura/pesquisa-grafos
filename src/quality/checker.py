"""
Checker Determinístico: valida afirmações do Analista diretamente contra o KG via Cypher.

Diferente do Revisor LLM, este módulo NÃO usa IA para avaliar — apenas queries
Cypher e comparação de strings. Serve como baseline determinístico para validar
se o Revisor LLM está correto.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field

from src.tools.graph_tools import _run_query


@dataclass
class Claim:
    """Uma afirmação factual extraída da resposta do Analista."""
    tipo: str          # "processo", "relator", "tema", "artigo", "precedente"
    processo: str      # Processo ao qual a afirmação se refere
    valor: str         # Valor afirmado (ex: "Gilmar Mendes", "art. 312")
    verificado: bool = False
    encontrado_no_kg: bool = False


@dataclass
class CheckerResult:
    """Resultado do Checker Determinístico."""
    total_claims: int = 0
    verificados_ok: int = 0
    verificados_falha: int = 0
    score: float = 0.0
    claims: list[Claim] = field(default_factory=list)
    concordancia_llm: float = 0.0  # % de concordância com o Revisor LLM


def extrair_processos_citados(texto: str) -> list[str]:
    """Extrai números de processo do texto via regex.

    Reconhece padrões como: HC 161.450, RE 1.513.210, RHC 265.270, ADI 4.983
    """
    pattern = r'\b((?:HC|RE|RHC|ADI|ADPF|MS|AgR|ED|ARE)\s*[\d]+(?:\.[\d]+)*(?:/[A-Z]{2})?)'
    matches = re.findall(pattern, texto, re.IGNORECASE)
    # Normaliza espaços
    processos = list({re.sub(r'\s+', ' ', m.strip().upper()) for m in matches})
    return processos


def extrair_claims(texto: str, processos: list[str]) -> list[Claim]:
    """Extrai afirmações factuais verificáveis da resposta do Analista.

    Para cada processo citado, tenta identificar:
    - Ministro relator mencionado
    - Artigos citados
    - Temas mencionados
    """
    claims: list[Claim] = []

    # Para cada processo, verifica se existe no KG
    for proc in processos:
        claims.append(Claim(tipo="processo", processo=proc, valor=proc))

    # Extrai menções de ministros/relatores
    relator_patterns = [
        r'(?:relator|relatora|ministro|ministra)\s*(?::|,)?\s*([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+){1,4})',
        r'(?:Min\.|Ministro|Ministra)\s+([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+){1,3})',
    ]
    for pattern in relator_patterns:
        for match in re.finditer(pattern, texto):
            nome = match.group(1).strip()
            # Tenta associar ao processo mais próximo no texto
            pos = match.start()
            proc_mais_proximo = _processo_mais_proximo(texto, pos, processos)
            if proc_mais_proximo and nome:
                claims.append(Claim(tipo="relator", processo=proc_mais_proximo, valor=nome))

    # Extrai artigos citados
    artigo_pattern = r'(?:art\.?\s*(\d+[º°]?)(?:\s*,?\s*(?:inciso|inc\.|§|parágrafo)?\s*[IVXLCDM\d]+)?(?:\s*(?:do|da|dos|das)\s+(?:C[PF]P?|CF|Constituição))?)'
    for match in re.finditer(artigo_pattern, texto, re.IGNORECASE):
        artigo_ref = match.group(0).strip()
        pos = match.start()
        proc_mais_proximo = _processo_mais_proximo(texto, pos, processos)
        if proc_mais_proximo:
            claims.append(Claim(tipo="artigo", processo=proc_mais_proximo, valor=artigo_ref))

    # Remove claims duplicados
    seen = set()
    unique_claims = []
    for c in claims:
        key = (c.tipo, c.processo, c.valor.lower())
        if key not in seen:
            seen.add(key)
            unique_claims.append(c)

    return unique_claims


def _processo_mais_proximo(texto: str, posicao: int, processos: list[str]) -> str | None:
    """Encontra o processo citado mais próximo de uma posição no texto."""
    if not processos:
        return None

    menor_dist = float('inf')
    mais_proximo = processos[0]

    for proc in processos:
        # Busca todas as ocorrências do processo no texto
        for match in re.finditer(re.escape(proc), texto, re.IGNORECASE):
            dist = abs(match.start() - posicao)
            if dist < menor_dist:
                menor_dist = dist
                mais_proximo = proc

    return mais_proximo


def verificar_claims(claims: list[Claim]) -> list[Claim]:
    """Verifica cada claim diretamente no KG via Cypher."""
    for claim in claims:
        claim.verificado = True

        if claim.tipo == "processo":
            claim.encontrado_no_kg = _verificar_processo(claim.processo)

        elif claim.tipo == "relator":
            claim.encontrado_no_kg = _verificar_relator(claim.processo, claim.valor)

        elif claim.tipo == "artigo":
            claim.encontrado_no_kg = _verificar_artigo(claim.processo, claim.valor)

        elif claim.tipo == "tema":
            claim.encontrado_no_kg = _verificar_tema(claim.processo, claim.valor)

    return claims


def _verificar_processo(numero: str) -> bool:
    """Verifica se o processo existe no KG."""
    results = _run_query(
        "MATCH (p:Processo_STF) WHERE toUpper(p.numero) CONTAINS toUpper($n) RETURN p.numero",
        {"n": numero}
    )
    return len(results) > 0


def _verificar_relator(processo: str, nome_relator: str) -> bool:
    """Verifica se o relator do processo confere com o KG."""
    results = _run_query(
        """MATCH (p:Processo_STF)-[:RELATADO_POR]->(m:Ministro_Relator)
           WHERE toUpper(p.numero) CONTAINS toUpper($proc)
           RETURN m.nome AS nome""",
        {"proc": processo}
    )
    if not results:
        return False

    nome_kg = results[0]["nome"].lower()
    nome_claim = nome_relator.lower()
    # Verifica se o nome (ou parte dele) está contido
    return nome_claim in nome_kg or nome_kg in nome_claim


def _verificar_artigo(processo: str, artigo_ref: str) -> bool:
    """Verifica se o processo cita o artigo mencionado."""
    results = _run_query(
        """MATCH (p:Processo_STF)-[:CITA_ARTIGO]->(a:Artigo_Constitucional)
           WHERE toUpper(p.numero) CONTAINS toUpper($proc)
           RETURN a.artigo AS artigo""",
        {"proc": processo}
    )
    if not results:
        return False

    # Extrai número do artigo da referência
    num_match = re.search(r'(\d+)', artigo_ref)
    if not num_match:
        return False
    num_artigo = num_match.group(1)

    # Verifica se algum artigo no KG contém esse número
    for r in results:
        if num_artigo in r["artigo"]:
            return True
    return False


def _verificar_tema(processo: str, tema_desc: str) -> bool:
    """Verifica se o processo trata do tema mencionado."""
    results = _run_query(
        """MATCH (p:Processo_STF)-[:TRATA_DE]->(t:Tema_Repercussao_Geral)
           WHERE toUpper(p.numero) CONTAINS toUpper($proc)
           RETURN t.descricao AS descricao""",
        {"proc": processo}
    )
    if not results:
        return False

    tema_lower = tema_desc.lower()
    for r in results:
        desc_lower = r["descricao"].lower()
        # Verifica sobreposição de palavras-chave
        palavras_tema = set(tema_lower.split())
        palavras_kg = set(desc_lower.split())
        overlap = palavras_tema & palavras_kg
        if len(overlap) >= 2 or tema_lower in desc_lower or desc_lower in tema_lower:
            return True
    return False


def _detectar_claim_negativo(texto: str) -> bool:
    """Detecta se o Analista afirma que algo NÃO existe no KG."""
    padroes_negativos = [
        r"não consta",
        r"não há registro",
        r"não encontr",
        r"não foram encontrad",
        r"não exist",
        r"não possui",
        r"nenhuma decisão",
        r"nenhum registro",
        r"não consta nas \d+ decisões",
    ]
    texto_lower = texto.lower()
    return any(re.search(p, texto_lower) for p in padroes_negativos)


def _verificar_claim_negativo(query: str) -> list[Claim]:
    """Quando o Analista diz 'não existe', verifica se realmente não existe.

    Extrai termos-chave da query original e busca no KG por temas e artigos.
    Se encontrar dados, a afirmação negativa do Analista é FALSA.
    """
    claims: list[Claim] = []

    # Busca todos os temas do KG
    temas_kg = _run_query(
        """MATCH (p:Processo_STF)-[:TRATA_DE]->(t:Tema_Repercussao_Geral)
           RETURN p.numero AS processo, t.descricao AS tema"""
    )

    # Sinônimos conhecidos para matching semântico básico
    sinonimos = {
        "maconha": ["cannabis", "canábis", "marijuana", "cânhamo"],
        "cannabis": ["maconha", "canábis", "marijuana", "cânhamo"],
        "medicinal": ["medicinais", "médico", "médica", "terapêutico", "terapêutica"],
        "medicinais": ["medicinal", "médico", "médica", "terapêutico", "terapêutica"],
        "cultivo": ["plantio", "plantar", "cultivar", "plantação"],
        "drogas": ["entorpecentes", "narcóticos", "substâncias"],
        "saúde": ["sanitário", "sanitária", "médico", "médica"],
        "penal": ["criminal", "crime", "criminoso", "delito"],
        "preso": ["presa", "prisão", "detido", "detida", "encarcerado"],
        "liberdade": ["soltura", "solto", "livre", "liberação"],
    }

    # Extrai palavras-chave da query (remove stopwords comuns)
    stopwords = {
        "quais", "qual", "que", "como", "onde", "quando", "decisões", "decisão",
        "decisoes", "decisao", "sobre", "citam", "cita", "tratam", "trata",
        "são", "sao", "foram", "pode", "podem", "tem", "têm", "dos", "das",
        "do", "da", "de", "em", "no", "na", "nos", "nas", "com", "por", "para",
        "uma", "um", "os", "as", "se", "ou", "ao", "aos", "à", "às", "o", "a",
        "e", "é", "uso", "tema", "falam", "fala",
    }
    palavras_query = {
        p.lower() for p in re.findall(r'\w+', query)
        if len(p) > 2 and p.lower() not in stopwords
    }

    # Expande query com sinônimos
    palavras_expandidas = set(palavras_query)
    for p in palavras_query:
        if p in sinonimos:
            palavras_expandidas.update(sinonimos[p])

    # Verifica se algum tema do KG tem overlap com a query
    for row in temas_kg:
        tema_lower = row["tema"].lower()
        palavras_tema = set(re.findall(r'\w+', tema_lower))

        # Match exato expandido (com sinônimos)
        overlap = palavras_expandidas & palavras_tema

        # Match parcial (substring): "medicinal" match "medicinais"
        if not overlap:
            for pq in palavras_expandidas:
                for pt in palavras_tema:
                    if len(pq) >= 4 and (pq in pt or pt in pq):
                        overlap = {pq}
                        break
                if overlap:
                    break

        if len(overlap) >= 1:
            # O KG TEM dados sobre isso — o claim negativo do Analista é FALSO
            claims.append(Claim(
                tipo="negação",
                processo=row["processo"],
                valor=f"Analista negou existência, mas KG tem: {row['tema']}",
                verificado=True,
                encontrado_no_kg=False,  # A negação é INCORRETA
            ))

    # Se não encontrou nada, a negação do Analista pode estar correta
    if not claims:
        claims.append(Claim(
            tipo="negação",
            processo="N/A",
            valor="Analista negou existência — KG confirma ausência",
            verificado=True,
            encontrado_no_kg=True,  # A negação é CORRETA
        ))

    return claims


def run_checker(analyst_text: str, query: str = "") -> CheckerResult:
    """Executa o Checker Determinístico completo.

    1. Detecta se o Analista fez afirmação negativa ("não existe")
    2. Extrai processos citados via regex
    3. Extrai claims factuais (relator, artigos, temas)
    4. Verifica cada claim via Cypher direto no KG
    5. Calcula score determinístico
    """
    claims: list[Claim] = []

    # Verifica claims negativos ("não consta", "não encontrado")
    if _detectar_claim_negativo(analyst_text):
        claims_negativos = _verificar_claim_negativo(query)
        claims.extend(claims_negativos)

    # Extrai e verifica claims positivos (processos, relatores, artigos)
    processos = extrair_processos_citados(analyst_text)
    claims_positivos = extrair_claims(analyst_text, processos)
    claims_positivos = verificar_claims(claims_positivos)
    claims.extend(claims_positivos)

    total = len(claims)
    ok = sum(1 for c in claims if c.encontrado_no_kg)
    falha = total - ok
    score = (ok / total * 100) if total > 0 else 0.0

    return CheckerResult(
        total_claims=total,
        verificados_ok=ok,
        verificados_falha=falha,
        score=score,
        claims=claims,
    )


def comparar_com_llm(checker: CheckerResult, llm_score: float) -> str:
    """Gera relatório de comparação entre Checker e Revisor LLM."""
    diff = abs(checker.score - llm_score)

    lines = [
        f"\n{'=' * 55}",
        "🔍 COMPARAÇÃO: Checker Determinístico vs Revisor LLM",
        f"{'=' * 55}",
        f"  Score Checker (Cypher):  {checker.score:.1f}%",
        f"  Score Revisor (LLM):    {llm_score:.1f}%",
        f"  Diferença:              {diff:.1f}%",
    ]

    if diff <= 10:
        lines.append(f"  Concordância:           ✅ ALTA (diferença ≤ 10%)")
    elif diff <= 25:
        lines.append(f"  Concordância:           ⚠️ MODERADA (diferença ≤ 25%)")
    else:
        lines.append(f"  Concordância:           ❌ BAIXA (diferença > 25%)")

    lines.append(f"\n  Claims verificados via Cypher:")
    for c in checker.claims:
        status = "✅" if c.encontrado_no_kg else "❌"
        lines.append(f"    {status} [{c.tipo:>10}] {c.processo}: {c.valor}")

    lines.append(f"{'=' * 55}")
    return "\n".join(lines)


def checker_result_to_dict(result: CheckerResult) -> dict:
    """Converte CheckerResult para dict serializável."""
    return {
        "total_claims": result.total_claims,
        "verificados_ok": result.verificados_ok,
        "verificados_falha": result.verificados_falha,
        "score": result.score,
        "concordancia_llm": result.concordancia_llm,
        "claims": [asdict(c) for c in result.claims],
    }
