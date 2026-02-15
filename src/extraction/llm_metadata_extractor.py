"""
Extração de metadados estruturados de decisões do STF via LLM.

Recebe o texto extraído pelo Docling e usa o OpenAI para identificar:
- Número do processo e classe processual
- Ministro Relator
- Temas de Repercussão Geral
- Artigos Constitucionais citados
- Precedentes citados
"""

from __future__ import annotations

import json
import os

from openai import OpenAI

from src.models.schemas import (
    ArtigoConstitucional,
    DecisaoSTF,
    MinistroRelator,
    TemaRepercussaoGeral,
)

EXTRACTION_PROMPT = """Você é um especialista em direito constitucional brasileiro.
Analise o texto a seguir, extraído de uma decisão do STF, e retorne APENAS um JSON válido com os seguintes campos:

{
  "numero_processo": "número do processo (ex: HC 161.450, RE 1.513.210)",
  "classe": "classe processual (RE, ADI, ADPF, HC, MS, etc.)",
  "ministro_relator": "nome completo do Ministro(a) Relator(a)",
  "data_julgamento": "data do julgamento no formato YYYY-MM-DD (se encontrada, senão 'N/D')",
  "temas": [
    {"numero": 0, "descricao": "descrição do tema principal tratado na decisão"}
  ],
  "artigos_citados": [
    {"artigo": "art. X, inciso Y", "descricao": "descrição breve do artigo"}
  ],
  "precedentes_citados": ["RE 123.456", "ADI 789"],
  "voto_resumo": "resumo do voto do relator em até 3 parágrafos",
  "dispositivo_resumo": "resumo do dispositivo (decisão final) em até 2 parágrafos"
}

REGRAS:
- Extraia APENAS informações presentes no texto. Não invente.
- Se um campo não puder ser identificado, use string vazia ou lista vazia.
- Para temas de repercussão geral, use numero=0 se o número não for mencionado.
- Liste TODOS os artigos constitucionais citados no texto.
- Liste TODOS os precedentes (outros processos) citados.
- Retorne SOMENTE o JSON, sem texto adicional.

TEXTO DA DECISÃO:
"""


def extract_metadata_from_text(
    full_text: str,
    voto_text: str,
    dispositivo_text: str,
    filename: str,
) -> DecisaoSTF:
    """Extrai metadados estruturados do texto de uma decisão usando o LLM.

    Args:
        full_text: Texto completo extraído pelo Docling.
        voto_text: Texto do Voto (se extraído por regex).
        dispositivo_text: Texto do Dispositivo (se extraído por regex).
        filename: Nome do arquivo PDF de origem.

    Returns:
        DecisaoSTF com metadados estruturados.
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    model_id = os.getenv("OPENAI_MODEL_ID", "gpt-4o")

    # Envia sempre o texto completo para o LLM extrair metadados
    context_text = full_text[:30000]
    if voto_text:
        context_text += f"\n\n=== SEÇÃO VOTO (extraída) ===\n{voto_text[:8000]}"
    if dispositivo_text:
        context_text += f"\n\n=== SEÇÃO DISPOSITIVO (extraída) ===\n{dispositivo_text[:4000]}"

    raw_json = None
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": "Você extrai metadados estruturados de decisões do STF. Responda SOMENTE com JSON válido."},
                    {"role": "user", "content": EXTRACTION_PROMPT + context_text},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            raw_json = response.choices[0].message.content
            if raw_json:
                break
        except Exception as e:
            print(f"    [RETRY {attempt+1}/3] Erro na chamada LLM: {e}")

    if not raw_json:
        raise ValueError(f"LLM retornou resposta vazia após 3 tentativas para {filename}")

    data = json.loads(raw_json)

    # Converte para modelos Pydantic
    temas = []
    for t in data.get("temas", []):
        if t.get("descricao"):
            temas.append(TemaRepercussaoGeral(
                numero=t.get("numero", 0),
                descricao=t["descricao"],
            ))

    artigos = []
    for a in data.get("artigos_citados", []):
        if a.get("artigo"):
            artigos.append(ArtigoConstitucional(
                artigo=a["artigo"],
                descricao=a.get("descricao", ""),
            ))

    precedentes = [p for p in data.get("precedentes_citados", []) if p]

    # Usa o texto do voto/dispositivo extraído pelo Docling se disponível,
    # senão usa o resumo do LLM
    final_voto = voto_text if voto_text else data.get("voto_resumo", "")
    final_dispositivo = dispositivo_text if dispositivo_text else data.get("dispositivo_resumo", "")

    return DecisaoSTF(
        numero_processo=data.get("numero_processo", filename.replace(".pdf", "")),
        classe=data.get("classe", "N/D"),
        ministro_relator=MinistroRelator(
            nome=data.get("ministro_relator", "N/D")
        ),
        data_julgamento=data.get("data_julgamento", "N/D"),
        temas=temas,
        artigos_citados=artigos,
        precedentes_citados=precedentes,
        voto_texto=final_voto,
        dispositivo_texto=final_dispositivo,
    )
