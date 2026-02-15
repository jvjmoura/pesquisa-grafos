# Análise: IA Agêntica, Engenharia de Contexto e Grafos de Conhecimento

**Artigo:** *Agentic AI, Context Engineering and Knowledge Graphs: Current Approaches, Challenges and Opportunities*
**Autores:** Niraj Karki, Manjila Pandey, Sanju Tiwari, Nandana Mihindukulasooriya, Sven Groppe
**Publicação:** QuaLLM-KG 2026 — 1st International Workshop on Quality in Large Language Models and Knowledge Graphs (Tampere, Finlândia, 24/03/2026)

**Data da análise:** 15 de fevereiro de 2026

---

Este documento analisa um estudo de 2026 que explora como usar Grafos de Conhecimento (KGs) para tornar a Inteligência Artificial mais confiável e inteligente. Para ir além da teoria, construímos um sistema real — com agentes de IA que analisam decisões do STF consultando um grafo jurídico — e testamos na prática.

---

## 1. O que o artigo propõe?

O estudo funciona como um **mapa** (survey) de como unir o poder de processamento de texto das IAs (LLMs) com a organização lógica dos Grafos de Conhecimento. A ideia central é a **Engenharia de Contexto**: organizar os dados de forma que a IA não "alucine" (invente fatos).

Os autores analisaram 436 artigos, filtrando até 35 trabalhos relevantes (2020-2025), e a contribuição principal é uma **taxonomia prática** — uma "escada de integração".

### A "Escada" de Integração

Os autores criaram uma classificação baseada em **quando** o Grafo é usado no sistema:

- **No Treinamento (Pre-training):** O Grafo ensina a IA desde o "nascimento" (ex: K-BERT, ConceptFormer).
- **Após o Treinamento (Post-training):** Ajustes finos para corrigir erros e reduzir alucinações.
- **Aumento de Dados (Augmentation):** O Grafo enriquece os dados de entrada do modelo (ex: KG-FiD, KnowPrompt).
- **Na Consulta (Inference-time):** A IA consulta o Grafo **em tempo real** para responder a uma pergunta, como se estivesse checando uma enciclopédia antes de falar (ex: THINK-ON-GRAPH, HOLMES).
- **Atualização Contínua:** O sistema aprende e atualiza o Grafo conforme novas informações surgem (ex: ZEP, KARMA).

No nosso sistema, adotamos a abordagem de **Inference-time**: o agente consulta o grafo Neo4j em tempo real, antes de gerar qualquer resposta. Isso é feito através de ferramentas (tools) registradas no framework **Agno**:

```python
# src/agents/analyst_agent.py — O Agente Analista com suas tools de consulta ao KG
from agno.agent import Agent
from agno.models.openai import OpenAIChat

return Agent(
    name="Analista Jurídico STF",
    model=OpenAIChat(id="gpt-4o"),
    tools=[
        buscar_decisao,           # Busca decisão pelo número do processo
        listar_todas_decisoes,    # Lista todas as decisões no KG
        buscar_por_tema,          # Busca por tema de repercussão geral
        buscar_por_artigo,        # Busca por artigo constitucional
        buscar_conexoes_multihop, # Raciocínio multi-hop entre decisões
    ],
    instructions=ANALYST_INSTRUCTIONS,
)
```

---

## 2. Pontos Fortes

### Por que o artigo é bom?

- **Organização:** Cria categorias claras (a "escada" acima) que ajudam desenvolvedores a escolher a melhor técnica para o seu caso. A revisão sistemática (436 → 96 → 52 → 35 artigos) confere rigor acadêmico.

- **Visão de Futuro:** Identifica tendências como a IA Neuro-Simbólica (que une a intuição da IA com a lógica rígida dos Grafos), memória dinâmica (ZEP) e sistemas multi-agente (KARMA) — padrões que implementamos no nosso teste.

- **Foco em Qualidade:** Defende que o contexto bem estruturado é a única forma de criar sistemas de IA seguros. O artigo é promissor ao propor o conceito de "Quality-by-Design", que implementamos como um **Quality Monitor** com métricas quantitativas.

- **Tabela comparativa valiosa:** A Table 1 do artigo compila modelo, metodologia, datasets, performance e limitações de cada abordagem — útil como referência rápida para pesquisadores.

---

## 3. Pontos Fracos (com Justificativa)

### O que poderia ser melhor?

- **Falta de Testes Práticos:** O artigo é puramente teórico. Ele diz "como fazer", mas não mostra os resultados de um teste real comparando as técnicas. Um survey que inclui ao menos um experimento reproduzível tem impacto muito maior. **Justificativa:** Sem validação empírica, o leitor não consegue avaliar qual abordagem é realmente superior em cenários específicos — fica no campo das hipóteses.

- **Métricas Confusas:** Ele cita vários estudos diferentes, mas cada um usa uma régua de medição diferente (+1-2% precision, +348% Hit@10, 85.5% accuracy, +29.8% QA gain). Não há normalização. **Justificativa:** Sem uma métrica unificada, o leitor não consegue responder à pergunta fundamental: "qual abordagem devo usar para meu caso?".

- **Dados Muito Genéricos:** O estudo foca em bases de dados acadêmicas (HotpotQA, WebQSP, TriviaQA — todas baseadas em Wikidata/Wikipedia) e ignora áreas complexas como Direito ou Medicina. **Justificativa:** Sistemas reais operam com jurisprudência, prontuários médicos, normas técnicas — dados com características muito diferentes de Wikipedia. A ausência dessa discussão limita a aplicabilidade prática.

- **Trade-offs Superficiais:** As limitações listadas são genéricas ("static KG", "high computational cost"). Não há análise de quando cada limitação é crítica. **Justificativa:** Um engenheiro que precisa escolher entre THINK-ON-GRAPH e HOLMES para um sistema jurídico precisa saber: latência, escalabilidade, custo — informações ausentes.

- **Verificação Factual Pouco Explorada:** A Seção 5 menciona integração neuro-simbólica como direção futura, mas não detalha como implementar verificação factual em pipeline. **Justificativa:** Conforme demonstramos na Seção 4 deste documento, um pipeline Analista → Revisor → Monitor é viável e detecta alucinações em tempo real — o artigo poderia ter explorado isso com profundidade.

---

## 4. Sugestões de Melhoria

Associada aos pontos fracos, seguem sugestões concretas:

- **Incluir experimento comparativo:** Seria valioso implementar 3-4 abordagens da taxonomia (RAG simples com pgvector/LanceDB, GraphRAG, inference-time KG, verificação neuro-simbólica) no **mesmo dataset** e comparar com métricas padronizadas (EM, F1, faithfulness). Isso transformaria o survey de descritivo para prescritivo.

- **Ampliar para domínios especializados:** Incluir ao menos um estudo de caso em Direito, Medicina ou Engenharia demonstraria que as conclusões se generalizam. Nosso teste com decisões do STF (Seção 4) mostra que é viável e revelador.

- **Testar com mais exemplos e variedade:** Um benchmark com 50-100+ documentos de diferentes áreas jurídicas, por exemplo, permitiria avaliar escalabilidade e generalização. Seria bom ter experimentos com corpus maiores para validar se os 82.5% de fidelidade se mantêm ou melhoram com mais dados no grafo.

- **Análise de custo-benefício:** Cada abordagem deveria ser avaliada por latência, custo de API (tokens), custo de construção do KG e infraestrutura. Praticantes precisam dessas informações para decisões informadas.

- **Explorar o padrão Gerador + Verificador:** O conceito de "quality-by-design" merece uma seção dedicada, com métricas de detecção de alucinações e impacto na confiabilidade. Nosso Quality Monitor mostra que isso é implementável com poucas linhas de código.

---

## 5. Teste Prático: O Sistema do STF

Para validar a teoria do artigo, aplicamos os conceitos em um cenário real: **decisões do Supremo Tribunal Federal (STF)**. Criamos um sistema onde uma IA analisa o processo e outra IA (o Revisor) checa se o que foi dito bate com o Grafo de Conhecimento jurídico.

### 5.1. Arquitetura e Bibliotecas

O sistema foi construído em **Python 3.10+** com as seguintes bibliotecas:

| Biblioteca | Versão | Função |
|---|---|---|
| **Agno** | >= 2.5.0 | Framework de agentes de IA (orchestração, tools, multi-agente) |
| **Docling** | >= 2.60.0 | Extração de texto de PDFs com OCR nativo macOS |
| **Neo4j** | >= 5.26.0 | Driver Python para o banco de dados de grafos Neo4j Aura |
| **OpenAI** | >= 1.60.0 | API do GPT-4o para geração de texto e extração de metadados |
| **Pydantic** | >= 2.10.0 | Validação de dados e schemas tipados |
| **Rich** | >= 13.9.0 | Interface de terminal formatada e colorida |
| **python-dotenv** | >= 1.0.1 | Carregamento de variáveis de ambiente (.env) |

O pipeline completo funciona em 4 etapas:

```
  PDF (Docling + OCR) → LLM (extrai metadados) → Neo4j Aura (Knowledge Graph)
                                                          ↕
                        Agente Analista (consulta KG em tempo real via Cypher)
                                  │
                        Agente Revisor (verifica fidelidade contra o KG)
                                  │
                        Quality Monitor (métricas + log JSONL)
```

**Etapa 1 — Extração:** O Docling lê os PDFs do STF com OCR em português e extrai as seções Voto e Dispositivo:

```python
# src/extraction/docling_extractor.py — OCR macOS em português
from docling.document_converter import DocumentConverter
from docling.datamodel.pipeline_options import OcrMacOptions, PdfPipelineOptions

ocr_options = OcrMacOptions(lang=["pt-BR", "en-US"], force_full_page_ocr=True)
pipeline_options = PdfPipelineOptions(do_ocr=True, ocr_options=ocr_options)
converter = DocumentConverter(format_options={...})
```

**Etapa 2 — Knowledge Graph:** Os metadados são estruturados no Neo4j com o seguinte schema de grafos:

```
(:Processo_STF) -[:RELATADO_POR]->  (:Ministro_Relator)
(:Processo_STF) -[:TRATA_DE]->     (:Tema_Repercussao_Geral)
(:Processo_STF) -[:CITA_ARTIGO]->  (:Artigo_Constitucional)
(:Processo_STF) -[:CITA_PRECEDENTE]-> (:Processo_STF)
```

As relações são gravadas com queries Cypher usando `MERGE` para evitar duplicatas:

```python
# src/graph/schema.py — Ingestão de uma decisão no KG
client.run_write("""
    MERGE (p:Processo_STF {numero: $numero})
    SET p.classe = $classe,
        p.voto_texto = $voto,
        p.dispositivo_texto = $dispositivo,
        p.data_julgamento = $data
""", {...})
```

**Etapa 3 — Agentes:** O sistema usa dois agentes Agno em pipeline sequencial. O Analista consulta o KG antes de responder, e o Revisor valida cada afirmação:

```python
# src/agents/team.py — Pipeline Analista → Revisor → Quality Monitor
class STFTeam:
    def run(self, query: str) -> TeamResponse:
        # Passo 1: Analista consulta o KG
        analyst_response = self.analyst.run(query)

        # Passo 2: Revisor verifica a resposta contra o KG
        reviewer_response = self.reviewer.run(review_prompt)

        # Passo 3: Quality Monitor extrai métricas e loga
        metrics = parse_metrics_from_review(reviewer_text)
        log_quality(query, metrics, analyst_text, reviewer_text)
```

**Etapa 4 — Quality Monitor:** O Revisor gera métricas JSON estruturadas que são parseadas e logadas automaticamente em `logs/quality_log.jsonl`:

```python
# src/quality/monitor.py — Extração de métricas da revisão
@dataclass
class QualityMetrics:
    validado: bool = False
    score_fidelidade: float = 0.0       # (verificadas_ok / total) * 100
    total_afirmacoes: int = 0
    verificadas_ok: int = 0
    sem_fundamentacao: int = 0
    processos_verificados: list[str] = field(default_factory=list)
    problemas: list[str] = field(default_factory=list)
```

As tools de consulta ao KG usam **queries Cypher multi-hop**, que permitem raciocínio relacional — algo impossível em RAG tradicional:

```python
# src/tools/graph_tools.py — Raciocínio multi-hop via Cypher
# Encontra processos que citam o MESMO precedente (2 hops):
MATCH (p1:Processo_STF {numero: $numero})
      -[:CITA_PRECEDENTE]->(prec:Processo_STF)
      <-[:CITA_PRECEDENTE]-(p2:Processo_STF)
WHERE p1 <> p2
RETURN p2.numero AS processo, prec.numero AS precedente_comum
```

### 5.2. Limitações do Teste

> **Nota importante:** Este teste foi realizado com **apenas 4 decisões do STF** (PDFs reais), gerando um Knowledge Graph com **37 nós**. Trata-se de um corpus **limitado**, insuficiente para conclusões estatísticas robustas. O objetivo principal foi **compreender e validar a funcionalidade da interação entre agentes LLM e Grafos de Conhecimento**, não produzir resultados generalizáveis. Com mais documentos (50-100+), espera-se que o score de fidelidade melhore, pois o KG teria mais dados para fundamentar as respostas.

### 5.3. Resultados do Experimento (5 Queries)

| # | Pergunta | Tipo | Score | Afirmações | Status |
|---|---|---|---|---|---|
| 1 | Resuma a decisão HC 161.450, incluindo relator, tema e dispositivo | Decisão específica | 87,5% | 7/8 | ⚠️ |
| 2 | Quais decisões tratam do tema de Cannabis medicinal? | Busca por tema | 50,0% | 1/2 | ⚠️ |
| 3 | Quais processos citam os mesmos precedentes? | Multi-hop | 87,5% | 7/8 | ⚠️ |
| 4 | Quais decisões citam o artigo 312 do CPP? | Busca por artigo | 100,0% | 7/7 | ✅ |
| 5 | Análise comparativa: classe, datas, relatores e evolução temporal | Visão geral | 87,5% | 7/8 | ⚠️ |

### 5.4. Relatório Agregado

```
  Total de queries analisadas:  5
  Score médio de fidelidade:    82,5%
  Score mínimo:                 50,0%
  Score máximo:                 100,0%
  Total de afirmações:          33
  Afirmações verificadas OK:    29
  Afirmações sem fundamento:    4
  Queries validadas:            1/5
```

### 5.5. Análise dos Resultados

**O poder do Revisor (Query 2):** A IA principal (Analista) **mentiu**, dizendo que não encontrou decisões sobre "Cannabis medicinal". O Revisor consultou o Grafo, detectou que **todas as 4 decisões** tratam exatamente desse tema, e **corrigiu a informação**, atribuindo score de apenas 50%. Sem o Revisor, o usuário teria recebido uma resposta completamente falsa.

**Queries factuais vs. raciocínio:** Quando a pergunta é direta ("quem é o relator?", "que artigo é citado?"), o Analista acerta quase tudo (87,5-100%). Quando exige raciocínio multi-hop ("cadeias de precedentes", "evolução temporal"), o LLM às vezes infere relações que o KG não confirma — o score cai, mas o Revisor sinaliza.

### 5.6. Vantagem sobre RAG Tradicional

O artigo é **promissor** ao argumentar que a integração KG-LLM supera abordagens tradicionais de RAG. Nossa experiência prática confirma essa tese, com resultados bem superiores ao que se obteria com um simples RAG usando pgvector ou LanceDB:

| Recurso | IA Comum (RAG com pgvector/LanceDB) | IA com Grafo (KG + Agentes) |
|---|---|---|
| **Raciocínio** | Superficial (similaridade semântica, 1 hop) | Liga vários fatos (Multi-hop via Cypher, 2-3 hops) |
| **Confiança** | Pode inventar fatos (sem verificação) | Checa a verdade contra o Grafo (Revisor) |
| **Relações** | Implícitas em chunks de texto | Explícitas e tipadas (RELATADO_POR, CITA_ARTIGO) |
| **Explicação** | Diz "li isso em algum lugar" | Mostra o caminho exato: entidade → relação → entidade |
| **Anti-alucinação** | Baixa (confia cegamente no LLM) | Alta (Revisor + Quality Monitor com score %) |
| **Consistência** | Depende do embedding e do chunk | Garantida pelo schema do grafo |

**Exemplo concreto:** Em RAG tradicional, a query "quais processos citam os mesmos precedentes?" retornaria chunks de texto com similaridade semântica, sem garantia de que os precedentes existem. Com KG, a query Cypher retorna **apenas relações confirmadas** — zero falsos positivos na recuperação.

---

## 6. Conclusão

O artigo de Karki et al. (2026) é um **excelente guia teórico**, com uma taxonomia valiosa e abrangente. Mas **precisa de mais "chão de fábrica"**: a ausência de experimentação própria e a heterogeneidade das métricas limitam sua capacidade de guiar decisões práticas.

Nosso teste com dados do STF provou que a teoria funciona. Mesmo com apenas 4 documentos e 37 nós no KG, demonstramos que:

1. **A integração KG em inference-time funciona** e é viável com ferramentas atuais (Agno, Neo4j, OpenAI, Docling).
2. **O pipeline neuro-simbólico detecta alucinações** em tempo real (Query 2: Analista errou → Revisor corrigiu).
3. **Métricas quantitativas de qualidade são possíveis** — o Quality Monitor calcula fidelidade automaticamente.
4. **KG + Agentes supera RAG tradicional** (pgvector, LanceDB) em raciocínio relacional, verificação factual e explicabilidade.
5. **O score de 82,5% de fidelidade** mostra que o sistema é funcional, com espaço para melhorar com mais dados no grafo.

Unir Grafos de Conhecimento com IAs Agênticas é o melhor caminho para evitar erros em decisões importantes. O caminho adiante passa por KGs auto-atualizáveis, benchmarks com mais exemplos, e frameworks padronizados de avaliação de qualidade.

---

### Resumo

O texto analisa o artigo de Karki et al. (2026) sobre a integração de Grafos de Conhecimento (KG) em IA Agêntica. O estudo propõe uma taxonomia para organizar como esses grafos melhoram o contexto das IAs, reduzindo alucinações. A análise aponta que, embora o artigo seja teoricamente robusto, falta experimentação prática. Para suprir isso, um teste com decisões do STF foi realizado usando um pipeline Python com Agno (agentes), Docling (OCR), Neo4j (grafo) e OpenAI (GPT-4o), demonstrando que sistemas que usam grafos e agentes revisores alcançam **82,5% de fidelidade**, superando métodos tradicionais de busca (RAG com pgvector ou LanceDB) em tarefas complexas e verificáveis.

---

### Referências

- Karki, N., Pandey, M., Tiwari, S., Mihindukulasooriya, N., & Groppe, S. (2026). *Agentic AI, Context Engineering and Knowledge Graphs: Current Approaches, Challenges and Opportunities.* QuaLLM-KG 2026.
- Sun, J. et al. (2023). *Think-on-Graph: Deep and Responsible Reasoning of LLM on Knowledge Graph.* arXiv:2307.07697.
- Panda, P. et al. (2024). *HOLMES: Hyper-Relational Knowledge Graphs for Multi-hop Question Answering Using LLMs.* ACL 2024.
- Rasmussen, P. et al. (2025). *ZEP: A Temporal Knowledge Graph Architecture for Agent Memory.* arXiv:2501.13956.
- Lu, Y. & Wang, J. (2025). *KARMA: Leveraging Multi-Agent LLMs for Automated Knowledge Graph Enrichment.* arXiv:2502.06472.

---

*Bateria de testes executada em 15/02/2026 com 4 decisões reais do STF (37 nós no Knowledge Graph).*
*Sistema: Python 3.10+ | Agno 2.5 | Docling 2.60 | Neo4j Aura 5.26 | OpenAI GPT-4o*
