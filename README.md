# Sistema Neuro-Simbólico de Análise de Decisões do STF

Sistema de IA Agêntica que utiliza **Agno**, **Docling** e **Neo4j Aura** para análise neuro-simbólica de decisões do Supremo Tribunal Federal, seguindo os princípios de Context Engineering do artigo **QuaLLM-KG 2026**.

## Arquitetura

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│   Docling    │────▶│  Neo4j Aura  │◀────│  Agente Analista │
│ (OCR + PDF)  │     │  (KG cloud)  │     │  (Agno + Tools)  │
└─────────────┘     └──────────────┘     └────────┬────────┘
                                                  │
                                    ┌─────────────┼─────────────┐
                                    ▼                           ▼
                           ┌────────────────┐      ┌────────────────────┐
                           │ Revisor LLM    │      │ Checker Cypher     │
                           │ (GPT-4o+Tools) │      │ (Python+Cypher)    │
                           └───────┬────────┘      └──────────┬─────────┘
                                   │                          │
                                   └──────────┬───────────────┘
                                              ▼
                                    ┌──────────────────┐
                                    │ Quality Monitor   │
                                    │ (Compara + Log)   │
                                    └──────────────────┘
```

### Componentes

| Componente | Tecnologia | Função |
|---|---|---|
| **Extração** | Docling + OCR macOS | Processa PDFs (inclusive com fontes encriptadas) |
| **Metadados** | OpenAI GPT-4o | Identifica processo, ministro, temas, artigos, precedentes |
| **Knowledge Graph** | Neo4j Aura (cloud) | Mapeia decisões e relações estruturadas |
| **Agente Analista** | Agno + OpenAI | Consulta o KG antes de gerar respostas |
| **Agente Revisor** | Agno + OpenAI | Verifica fidelidade aos dados do grafo |
| **Checker Determinístico** | Python + Cypher | Valida claims via queries diretas ao KG (sem LLM) |
| **Quality Monitor** | Python + JSON | Compara verificadores, calcula scores, loga resultados |
| **Pipeline** | Python sequencial | Analista → Revisor → Checker → Monitor |

### Schema do Knowledge Graph

```
(:Processo_STF) -[:RELATADO_POR]-> (:Ministro_Relator)
(:Processo_STF) -[:TRATA_DE]-> (:Tema_Repercussao_Geral)
(:Processo_STF) -[:CITA_ARTIGO]-> (:Artigo_Constitucional)
(:Processo_STF) -[:CITA_PRECEDENTE]-> (:Processo_STF)
```

## Setup

### 1. Pré-requisitos

- Python 3.10+
- Conta no [Neo4j Aura](https://console.neo4j.io) (plano Free)
- Chave de API da OpenAI

### 2. Instalar dependências

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configurar variáveis de ambiente

```bash
cp .env.example .env
```

Edite `.env` com:
- `OPENAI_API_KEY` — sua chave da OpenAI
- `NEO4J_URI` — URI do Aura (`neo4j+s://xxxx.databases.neo4j.io`)
- `NEO4J_PASSWORD` — senha gerada pelo Aura

### 4. Ingerir PDFs das decisões

Coloque os PDFs em `data/decisions/` e execute:

```bash
python -m scripts.ingest --pdf-dir data/decisions
```

O pipeline: **Docling (OCR)** → **LLM (metadados)** → **Neo4j (grafo)**.

### 5. Executar o sistema

```bash
# Modo interativo (Analista + Revisor):
python main.py

# Pergunta única com revisão:
python main.py --query "Quais conexões existem entre as decisões?"

# Apenas Analista (sem revisão):
python main.py --analyst-only --query "Resuma o HC 215.763"

# Revisar um texto específico:
python main.py --review "O HC 215.763 foi relatado pelo Ministro Barroso..."

# Relatório agregado de qualidade:
python main.py --quality-report --skip-check
```

## Princípios QuaLLM-KG Aplicados

1. **Context Engineering (CE):** Docling + OCR extrai texto de alta qualidade dos PDFs do STF
2. **Knowledge Graph:** Neo4j Aura mapeia relações estruturadas entre decisões
3. **Integração em Tempo de Inferência:** Agente consulta o KG ANTES de gerar respostas
4. **Raciocínio Multi-hop:** Queries Cypher de 2-3 hops para conexões entre decisões
5. **Verificação Neuro-Simbólica:** Agente Revisor compara respostas com dados do grafo
6. **Quality-by-Design (Seção 5):** Monitor extrai métricas quantitativas e mantém log JSONL
7. **Verificação Dupla:** Checker determinístico (Cypher) valida o Revisor LLM, comparando scores

## Estrutura do Projeto

```
├── main.py                             # Entry point interativo
├── requirements.txt                    # Dependências Python
├── .env.example                        # Template de variáveis de ambiente
├── data/decisions/                     # PDFs das decisões do STF
├── src/
│   ├── models/schemas.py              # Modelos Pydantic
│   ├── extraction/
│   │   ├── docling_extractor.py       # Extração PDF via Docling + OCR
│   │   └── llm_metadata_extractor.py  # Extração de metadados via LLM
│   ├── graph/
│   │   ├── neo4j_client.py            # Cliente Neo4j
│   │   └── schema.py                  # Schema KG + ingestão
│   ├── tools/
│   │   └── graph_tools.py            # Tools Agno para consulta ao KG
│   ├── quality/
│   │   ├── monitor.py                # Quality Monitor (métricas + log JSONL)
│   │   └── checker.py                # Checker Determinístico (Cypher direto)
│   └── agents/
│       ├── analyst_agent.py           # Agente Analista
│       ├── reviewer_agent.py          # Agente Revisor
│       └── team.py                    # Pipeline Analista → Revisor → Checker → Monitor
├── logs/
│   └── quality_log.jsonl              # Log acumulativo de métricas
└── scripts/
    └── ingest.py                      # Pipeline de ingestão (PDF → KG)
```
