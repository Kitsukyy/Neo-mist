# Registro de decisões

Este registro resolve conflitos entre propostas antigas e o estado mais recente. IDs DOC-DEC são novos identificadores desta documentação; não reproduzem IDs de documentos históricos.

## Decisões do usuário

| ID | Decisão | Consequência |
|---|---|---|
| DOC-DEC-01 | Reconstruir e reconsiderar opções técnicas. | Legado é referência, não arquitetura obrigatória. |
| DOC-DEC-02 | Combinar assistência, identidade, companhia e modularidade. | Evitar reduzir a visão a um simples wrapper de API. |
| DOC-DEC-03 | Visão híbrida, multimodal e autonomia configurável. | Projetar interfaces substituíveis, implementar por etapas. |
| DOC-DEC-04 | Começar em um computador. | Sem infraestrutura distribuída inicial. |
| DOC-DEC-05 | Começar sem dados e calibrações antigos. | Armazenamento novo, sem migração do legado. |
| DOC-DEC-06 | Interface simples para testes. | Terminal inicial, núcleo independente da apresentação. |
| DOC-DEC-07 | Dezenas de milhares de memórias. | Avaliar capacidade sem projetar para escala arbitrária. |
| DOC-DEC-08 | APIs gratuitas. | Verificar cotas; indisponibilidade não autoriza gasto pago. |
| DOC-DEC-09 | APIs externas não são impedimento. | Processamento externo configurável, sem abolir controles. |
| DOC-DEC-10 | NVIDIA NIM e Token Harbor disponíveis. | Priorizar esses adaptadores na pesquisa. |
| DOC-DEC-11 | Comunicação, temperamento, relacionamento e iniciativa adaptáveis. | Dimensões independentes e identidade central coerente. |
| DOC-DEC-12 | Adaptação contextual e evolução ao longo do tempo. | Sessão no P0-A, persistência no P0-B. |
| DOC-DEC-13 | Combinar observação e perguntas para aprender. | Perguntar quando a ambiguidade for relevante. |
| DOC-DEC-14 | Credenciais antigas expiradas; schema antigo perdido. | Não reutilizar infraestrutura ou configuração antiga. |

## Diretrizes consolidadas

| ID | Diretriz | Estado |
|---|---|---|
| DOC-DEC-15 | Monólito modular Python no Linux. | Base arquitetural. |
| DOC-DEC-16 | Dividir P0 em P0-A conversacional e P0-B memória. | Escopo vigente. |
| DOC-DEC-17 | Constituição, personalidade e preferências separadas. | Base de identidade. |
| DOC-DEC-18 | Guarda e auditoria obrigatórias antes de envio externo. | Invariante. |
| DOC-DEC-19 | Falhas da Guarda ou auditoria bloqueiam envios. | Invariante. |
| DOC-DEC-20 | Sem ferramentas no P0-A; modelo não altera permissões. | Invariante. |
| DOC-DEC-21 | Origem da memória separada de estado epistêmico. | Base P0-B. |
| DOC-DEC-22 | Testes determinísticos offline com FakeModel. | Critério de entrega. |
| DOC-DEC-23 | Regras explícitas para roteamento inicial. | Base do Gateway. |
| DOC-DEC-24 | Hash exato para deduplicação inicial. | Base P0-B. |
| DOC-DEC-25 | Sem OCEAN/VAD, embeddings ou banco vetorial no núcleo inicial. | Simplificação vigente. |

## Propostas técnicas e pontos abertos

| ID | Tema | Registro atual |
|---|---|---|
| DOC-DEC-26 | Pydantic | Proposta de validação; versão e ergonomia a verificar. |
| DOC-DEC-27 | SQLite/FTS5 | Proposta inicial para P0-B; validar disponibilidade, recuperação e migrations. |
| DOC-DEC-28 | Dois modelos e AUTO/FAST/PRIMARY | Modos implementados; configuração NVIDIA usa seleção provisória do benchmark de 12/10/2026. |
| DOC-DEC-29 | Modelo rápido | Nemotron Super com raciocínio ativado, seleção técnica provisória baseada no [benchmark](18-benchmark-modelos.md), substituindo a sugestão histórica não confirmada de DeepSeek/Token Harbor. |
| DOC-DEC-30 | Modelo principal | Kimi K3, seleção técnica provisória baseada no mesmo benchmark; tarefas extensas e condições da conta ainda requerem avaliação. |
| DOC-DEC-31 | Credenciais | Ambiente/cofre local em avaliação; mecanismo definitivo não escolhido. |
| DOC-DEC-32 | Sensibilidade e detecção | Políticas obrigatórias; taxonomia e biblioteca ainda pendentes. |
| DOC-DEC-33 | Configuração YAML | Formato e estrutura propostos; parser e versões não fechados. |
| DOC-DEC-34 | Contratos detalhados deste conjunto | Especificação proposta para implementação, sujeita a validação. |

## Revisões que substituem propostas anteriores

1. A Fase 2 incluía memória em um P0 amplo. A revisão corretiva remove a persistência de longo prazo do P0-A e a coloca no P0-B.
2. A recomendação de preservar calibrações antigas foi substituída pela escolha explícita de não migrá-las.
3. VAD/OCEAN foram considerados para refatoração no diagnóstico antigo; deixaram de ser requisitos do núcleo inicial.
4. Uma proposta arquitetural omitiu a Guarda. A revisão corretiva a restaura como passagem obrigatória.
5. “Confirmado = declarado pelo usuário” foi refinado: origem declarada não equivale a verdade objetiva verificada.
6. A lista inicial Groq/Gemini/OpenRouter foi substituída pela pesquisa dos provedores já disponíveis. Nenhuma integração adicional é obrigatória.
7. Roteador LLM e cadeias amplas de fallback do legado não são a estratégia inicial.
8. Decaimento afeta relevância; não justifica exclusão silenciosa nem promoção automática de inferências.
9. Identidade central estável não implica tom único: o usuário escolheu comportamento adaptativo.

## Processo para novas decisões

Registrar problema, alternativas, evidência, estado, impacto, critérios de aceitação e possibilidade de reversão. Mudanças fundamentais devem ter revisão explícita do responsável pelo projeto. Preferências inferidas não alteram este registro automaticamente.

Números de desempenho, limites de contexto, contagem de tentativas e pesos de avaliação só se tornam metas quando houver condições de medição definidas.

## 13/10/2026 — Memória automática

**Decisão explícita do usuário:** guardar automaticamente informações úteis, com opção de excluir. A implementação 0.4.0 começa por captura local conservadora de declarações reconhecidas, com fontes e estados, sem gravar toda conversa nem persistir respostas de modelos como fatos. Padrões de captura, orçamento e snapshots manuais são escolhas técnicas deste incremento; não são critérios universais aprovados. Conteúdo novo fica local, e permitir envio externo é operação separada. Ver [documento 25](25-memoria-persistente.md).


## 13/10/2026 — Primeiro incremento de P1

**Decisão explícita do usuário:** começar pela organização de projetos e tarefas,
antes da interface visual ou ferramentas de arquivos. A revisão 0.5.0 oferece
cadastro local, objetivo, tarefas/status/prioridade/prazo, progresso declarado,
arquivamento/retomada e exportação. IDs, limites e comandos são escolhas técnicas
do incremento. Não autoriza execução de tarefas, acesso a pastas de trabalho
nem envio automático de conteúdo do catálogo. Ver [documento 27](27-projetos-e-tarefas.md).


## 13/10/2026 — Interface visual local

**Decisões explícitas do usuário:** escolher a interface visual local como próximo
incremento; para app, usar visual inspirado no ChatGPT (alternativa de terminal
seria Claude/OpenCode). A revisão 0.6.0 implementa o app local no navegador,
com conversa central, projetos, tarefas e memórias. Servidor serial em loopback,
assets empacotados e chave somente no backend são escolhas técnicas deste
incremento. Não amplia autonomia, não autoriza ferramentas nem grava todo
histórico de chats. Ver [documento 28](28-interface-visual-local.md).
