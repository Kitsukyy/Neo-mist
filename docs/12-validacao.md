# Validação, testes e aceitação

**Estado:** plano de verificação do P0-A completo. A suíte atual contém 132 testes, incluindo memória local 0.4.0; veja ambiente, cobertura e limitações no [estado de aceitação](20-avaliacao-identidade.md). Geração real e benchmark foram executados, com resultados em [integração](17-integracao-nvidia.md) e [seleção de modelos](18-benchmark-modelos.md). A aceitação completa do marco continua pendente.

Separar garantias determinísticas (código/políticas) de avaliações probabilísticas (qualidade de modelos). Os IDs VAL são novos; não pretendem reconstruir a lista histórica de 36 critérios truncada.

## Aceitação do P0-A

| ID | Cenário | Resultado esperado | Requisitos |
|---|---|---|---|
| VAL-A01 | Configuração/Constituição inválida. | Inicialização afetada falha com diagnóstico seguro. | C01, I01 |
| VAL-A02 | Entrada com papel/tipo/limite inválido. | Rejeitada antes do adaptador. | C02, G01 |
| VAL-A03 | Conversa com FakeModel sem rede/chaves. | Fluxo completo e resultado identificado como simulado. | C07, G02 |
| VAL-A04 | Modelo ou capacidade não configurados. | Erro claro, nenhuma chamada incompatível. | G03 |
| VAL-A05 | Guarda bloqueia payload. | Zero chamadas externas. | S01, S02 |
| VAL-A06 | Guarda lança erro ou fica indisponível. | Zero chamadas externas. | S03 |
| VAL-A07 | Auditoria obrigatória falha antes do envio. | Zero chamadas externas. | S03, S06 |
| VAL-A08 | Payload/destino mudam após aprovação. | Aprovação inválida; zero envios com decisão antiga. | S01 |
| VAL-A09 | Fallback recuperável permitido. | Novo destino passa por Guarda/auditoria. | G06 |
| VAL-A10 | Bloqueio de privacidade com alternativa disponível. | Não aciona fallback para contornar bloqueio. | S03, G06 |
| VAL-A11 | Resposta propõe comando ou permissão. | Nenhum executor; autorização negada. | S04, S07 |
| VAL-A12 | Logs recebem falha com texto/chave sintéticos. | Não expõem chave, prompt ou headers. | C06, S06 |
| VAL-A13 | Timeout/cota/conexão/resposta inválida. | Erros normalizados, tentativas limitadas. | C04, G04 |
| VAL-A14 | Trocar FakeModel por adaptador compatível. | Core não muda para conhecer API. | G01, G02 |
| VAL-A15 | Pedido atual corrige estilo. | Comportamento da sessão reflete a correção. | I03, I05 |
| VAL-A16 | Provedor real validado com entrada sintética. | Resposta normalizada, configuração/capacidades registradas. | G02, G03 |
| VAL-A17 | Falha de auditoria após resposta externa. | Erro comunicado; suspende novos envios até recuperação. | S03, S06 |
| VAL-A18 | Histórico excede orçamento. | Limite aplicado por política explícita, sem envio excessivo. | C05 |

As referências C/G/I/S correspondem ao sufixo dos IDs REQ em [requisitos](03-requisitos.md). A15 combina teste de regras de configuração com avaliação de resposta; não promete garantia universal de tom.

## Aceitação do P0-B

| ID | Cenário | Resultado esperado | Requisitos |
|---|---|---|---|
| VAL-B01 | Inicialização nova. | Banco vazio, sem importação do legado. | M01 |
| VAL-B02 | Memória sem origem/data/estado. | Persistência rejeitada. | M02 |
| VAL-B03 | Modelo gera candidato incompleto. | Não escreve diretamente; validação bloqueia. | M05 |
| VAL-B04 | Hipótese é recuperada repetidamente. | Mantém estado; não vira confirmação por acesso. | M06 |
| VAL-B05 | Informação declarada e inferida sobre o mesmo tema. | Origens e sustentação distinguíveis. | M02, M06 |
| VAL-B06 | Duplicata exata no escopo definido. | Deduplicação preserva fontes pertinentes. | M07 |
| VAL-B07 | Correção ou contradição. | Histórico/vigência explícitos; conflito não resolvido arbitrariamente. | M07 |
| VAL-B08 | Busca lexical por projeto/estado. | Resultados explicáveis e filtrados. | M03 |
| VAL-B09 | Muitas memórias candidatas ao contexto. | Orçamento e seleção determinísticos. | M04 |
| VAL-B10 | Item local-only relevante à busca. | Não aparece no payload externo. | S02, M03 |
| VAL-B11 | Exclusão solicitada. | Conteúdo/índices/caches/derivados fora de uso. | M08 |
| VAL-B12 | Restauração de backup anterior à exclusão. | Dado excluído não reaparece ativo. | S08, M09 |
| VAL-B13 | Migração interrompida. | Recuperação consistente sem sucesso fictício. | M09 |
| VAL-B14 | Exportação/restauração. | Origem, escopo e versões permitidas preservados. | M10 |
| VAL-B15 | Preferência corrigida entre sessões. | Versão vigente aplicada; anterior não prevalece. | I08 |
| VAL-B16 | Rede/embeddings indisponíveis. | Recuperação lexical local continua quando banco está íntegro. | M03 |

B12 exige mecanismo e política de retenção implementados. Não pode ser marcado aprovado apenas por apagar um registro SQLite.

## Estratégia de testes

Unitários para contratos, roteador, políticas, autorização e memória. Integração para fluxo ponta a ponta e falhas. Spies contam envios, verificam envelope real e inspecionam metadados.

Offline é o padrão da suíte. Testes com API real são explicitamente identificados e usam dados sintéticos. Não precisam enviar conversas pessoais para comprovar integração.

Verificar limites de importação/dependências circulares. Testes de segurança não devem se limitar a analisar a resposta textual do modelo.

## Avaliação comportamental

Cenários em português para concisão, profundidade, coerência, adaptação, correções, distinção de hipótese, fundamentação de discordância e iniciativa adequada.

Registrar ID exato do modelo, provedor, parâmetros, versão de política/perfil, data, cenário e resultado. Amostras finitas detectam regressões; não provam consistência universal.

## Experimentos técnicos

| Experimento | Pergunta | Evidência |
|---|---|---|
| Contratos | Pydantic é ergonômico e suficientemente eficiente? | Validação/erros com casos representativos. |
| Provedores | API/cotas/capacidades atendem ao núcleo? | Catálogo/configuração e testes reais sintéticos. |
| Modelos | Qual candidato atende melhor ao papel principal? | Mesmos cenários e métricas de qualidade/latência. |
| SQLite/FTS5 | Recupera com qualidade no volume esperado? | Dataset e gabarito versionados. |
| Exclusão/restauração | Derivados e backups respeitam a remoção? | Cenários de restauração e inspeção. |
| Guarda | Todos os caminhos externos aplicam política? | Contagem de chamadas e envelopes finais. |

Esses experimentos são a organização atual; não reconstrução literal dos seis experimentos da seção histórica não recuperada.

## Métricas de memória e desempenho

Medir recall@k/precision@k com gabarito, erros de escopo, uso indevido de hipótese, itens excluídos recuperados, latência p50/p95 e custo de montagem.

Comparar com baseline lexical, mas não aceitar um baseline ruim apenas porque outro método o iguala. Alvo absoluto exige dataset e justificativa.

A meta histórica p95 ≤ 300 ms em 10 mil memórias é proposta. Antes de fixá-la: hardware, armazenamento, cache frio/quente, operação, tokens e custo de embedding incluído/excluído.

O número de cerca de 500 linhas por módulo é orientação proposta de manutenção, não limite mecânico de aceitação.

## Definição de concluído

Um marco só termina com comportamento demonstrado, testes relevantes executados, erros/falhas verificados, documentação atualizada e pendências materiais registradas.

Documentação publicada não marca P0-A/P0-B concluídos. Verificação de links e coerência documental só comprova integridade da documentação.

## Validação adicional: saída estruturada

A camada opcional de contrato JSON passou na suíte de 57 testes em 12/10/2026, incluindo transporte NVIDIA simulado dos dois modelos selecionados. Ver [comportamento, limites e evidência](19-saida-estruturada.md). Esses testes não encerram a avaliação ampla de identidade ou os critérios pendentes de P0-A. Não houve nova avaliação real dos modelos nesta etapa.

## Matriz de aceitação atualizada

A avaliação local da identidade e a classificação dos critérios implementados, condicionais e pendentes estão no [documento 20](20-avaliacao-identidade.md). As rodadas reais v1/v2 e a regressão direcionada v3 estão no [documento 23](23-avaliacao-real-identidade.md); o fluxo com FakeModel não mede qualidade dos modelos.

## Verificação da distribuição instalada

A revisão 0.3.0 passou com 75 testes usando instalações isoladas, sem modo editável, em Python 3.11.16 e 3.14.7 no Linux. O comando instalado e as configurações empacotadas foram verificados fora do checkout. Consulte [pacote e evidências](21-instalacao-validada.md). Não houve nova chamada real à NVIDIA.

## Condições NVIDIA e entrada oculta na avaliação

As fontes públicas e as pendências da conta foram registradas no [documento 22](22-condicoes-nvidia.md). O runner passou a aceitar chave por entrada oculta; dois novos testes verificam encaminhamento sem exibição e recusa de leitura com eco. Aquela revisão passou com 68 testes em Python 3.11.16 e 3.14.7. Posteriormente, a avaliação real foi executada com autorização renovada do usuário; os registros históricos foram preservados e a revisão histórica tinha 75 testes; a revisão de memória 0.4.0 contém 130.

## Memória local 0.4.0

O [documento 25](25-memoria-persistente.md) relaciona implementação e validação do P0-B: 48 testes novos e experimento lexical sintético com dez mil itens. A política de exclusão depende do registro sobrevivente e não promete apagar cópias externas. Conversas reais com memória não foram avaliadas nesta entrega.
