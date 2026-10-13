# Requisitos

Os IDs REQ deste documento são novos e organizam a especificação recuperada. Não há correspondência numérica automática com os 36 critérios históricos, cujo texto integral não ficou disponível.

**P0-A** e **P0-B** são marcos do núcleo mínimo. **P1–P3** expressam evolução posterior; seu calendário permanece aberto. Detalhamentos adicionais são propostas técnicas, identificados abaixo.

## Núcleo e configuração

| ID | Requisito | Marco |
|---|---|---|
| REQ-C01 | Configuração central tipada e validada antes de inicializar. | P0-A |
| REQ-C02 | Um contrato por etapa: entrada, contexto, envio, resposta e auditoria. | P0-A |
| REQ-C03 | Interface de terminal separada do Core. | P0-A |
| REQ-C04 | Erros normalizados; falhas comuns não corrompem a sessão. | P0-A |
| REQ-C05 | Histórico e contexto temporário com limite configurável. | P0-A |
| REQ-C06 | Nenhum segredo no código, configurações públicas ou logs. | P0-A |
| REQ-C07 | Testes sem rede e sem credenciais. | P0-A |
| REQ-C08 | Tarefas manuais locais em 0.5.0; checkpoints/cancelamento de execução futuros. | P1 / futuro |
| REQ-C09 | Interfaces e documentação evoluem com o código. | Todos |

## Gateway

| ID | Requisito | Marco |
|---|---|---|
| REQ-G01 | Interface única independente de provedor. | P0-A |
| REQ-G02 | FakeModel determinístico e pelo menos um adaptador real validado. | P0-A |
| REQ-G03 | Modelos identificados por configuração; capacidades verificadas. | P0-A |
| REQ-G04 | Timeout e tentativas limitadas; erros de configuração, rede, autenticação, cota e resposta distinguíveis. | P0-A |
| REQ-G05 | Roteamento por regras e seleção manual dentro dos modelos configurados. | P0-A |
| REQ-G06 | Fallback explícito, limitado e com nova avaliação do destino. | P0-A |
| REQ-G07 | Propostas AUTO, FAST e PRIMARY documentadas; nenhum terceiro LLM só para roteamento. | P0-A |
| REQ-G08 | Streaming e saída estruturada somente quando implementados e compatíveis. | Evolução do Gateway |
| REQ-G09 | Adaptador local intercambiável. | Futuro |

Não é obrigatório implementar fallback entre provedores para concluir o primeiro fluxo. Se existir, REQ-G06 é obrigatório. Streaming não é requisito bloqueador inicial.

## Identidade e comportamento

| ID | Requisito | Marco |
|---|---|---|
| REQ-I01 | Constituição versionada, controlada pela aplicação e independente do modelo. | P0-A |
| REQ-I02 | Separar Constituição, personalidade e preferências. | P0-A |
| REQ-I03 | Adaptar temperamento, comunicação, relacionamento e iniciativa. | P0-A |
| REQ-I04 | Preservar identidade central e limites durante adaptação. | P0-A |
| REQ-I05 | Correções explícitas orientam imediatamente a sessão. | P0-A |
| REQ-I06 | Não afirmar ações inexistentes; expressar falhas e limitações. | P0-A |
| REQ-I07 | Combinar observação e esclarecimento relevante. | P0-A/P0-B |
| REQ-I08 | Preferências entre sessões com origem, atualização e exclusão. | P0-B |
| REQ-I09 | Avaliar consistência entre modelos e sessões. | P0-B e evolução |
| REQ-I10 | Mudanças permanentes de identidade exigem processo explícito. | Todos |

Precisão de conteúdo e estilo são avaliados por cenários. Permissões e bloqueios são impostos pelo código; prompts não os substituem.

## Segurança e observabilidade

| ID | Requisito | Marco |
|---|---|---|
| REQ-S01 | Guarda obrigatória sobre payload final e destino externo. | P0-A |
| REQ-S02 | Aplicar políticas de sensibilidade/local-only, além de detectar segredos. | P0-A |
| REQ-S03 | Falha da Guarda ou auditoria obrigatória impede envio. | P0-A |
| REQ-S04 | Nível zero bloqueia execução de ferramentas, independentemente do texto. | P0-A |
| REQ-S05 | Conteúdo externo e respostas são dados não confiáveis para autorização. | Todos |
| REQ-S06 | Auditoria de decisões, destinos, erros e resultados sem conteúdo sensível por padrão. | P0-A |
| REQ-S07 | Limites e permissões fora do alcance do modelo. | Todos |
| REQ-S08 | Controle de retenção, exclusão e restauração de dados. | P0-B |
| REQ-S09 | Auditoria de aprovações/recusas e cancelamento de ferramentas. | Futuro |

## Memória

| ID | Requisito | Marco |
|---|---|---|
| REQ-M01 | Armazenamento persistente local, sem importação do legado. | P0-B |
| REQ-M02 | Contrato único com origem, data e estado epistêmico. | P0-B |
| REQ-M03 | Recuperação lexical e metadados; razão e escopo dos resultados. | P0-B |
| REQ-M04 | Orçamento de itens/contexto determinístico e configurável. | P0-B |
| REQ-M05 | Ciclo de candidatos antes de persistir. | P0-B |
| REQ-M06 | Inferências e hipóteses nunca viram fatos por repetição. | P0-B |
| REQ-M07 | Deduplicação exata, versões e tratamento de contradições. | P0-B |
| REQ-M08 | Consultar, corrigir, atualizar e excluir memórias e derivados. | P0-B |
| REQ-M09 | Schema e migrations versionados; recuperação após falhas. | P0-B |
| REQ-M10 | Exportação em formato aberto e testes de restauração. | P0-B/evolução |
| REQ-M11 | Memórias episódicas, semânticas, preferências e escopo de projeto. | P0-B inicial |
| REQ-M12 | Cadastro e tarefas locais em 0.5.0; relações/consolidação de episódios futuras. | P1 |
| REQ-M13 | Procedimentos com evidência de resultado. | P2 |
| REQ-M14 | Embeddings só após avaliação; modelo/dimensão/versão registrados. | Futuro |

## Capacidades futuras

Ferramentas declarativas, busca web, arquivos com escopo, execução isolada de código, Git/APIs/desktop; autonomia por risco/tarefa; percepção multimodal; voz; painéis e GUI; estado emocional simulado; experimentos e melhoria controlada.

Cada capacidade depende de autorização verificável, orçamento de execução, contratos de erro e avaliação. Nenhuma está habilitada apenas por estar nesta lista.

## Qualidade e propostas não funcionais

Diretrizes: instalação reproduzível, dependências controladas, ausência de dependências circulares, logs estruturados, testes unitários e de integração offline, manutenção documental.

Português do Brasil é a proposta de idioma principal para conteúdo e avaliação. O limite histórico de cerca de 500 linhas por módulo e a meta de p95 ≤ 300 ms em 10 mil memórias são hipóteses de engenharia, não exigências aprovadas. Antes de usar a meta, definir hardware, operação, cache e custos incluídos.

