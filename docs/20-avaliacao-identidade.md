# Avaliação da identidade e estado da aceitação P0-A

Estado em 12/10/2026: infraestrutura e garantias locais verificadas; duas rodadas conversacionais reais executadas e revisadas, com correção direcionada de idioma no perfil final. Ver [resultados e limitações](23-avaliacao-real-identidade.md).

## Mudança nas instruções

A identidade agora declara a ausência de memória persistente, acesso a outros chats e acesso a arquivos/computador. Orienta distinguir declarações da conversa, inferências e informação ausente, não fabricar lembranças e justificar discordâncias com fatos disponíveis. Essas instruções descrevem a capacidade atual da aplicação; sua presença não garante obediência perfeita dos modelos.

O texto de identidade mudou depois do benchmark. Os índices publicados no documento 18 pertencem ao prompt anterior e não são recalculados nem atribuídos ao novo prompt.

## Evidência executada

A revisão histórica passou com **66 testes** em Python 3.14.7. Os nove testes adicionais verificam isolamento de papéis e permissões diante de texto forjado, descarte de contexto no reset, passagem ordenada de correções, correção manual de estilo e a infraestrutura de avaliação. Também cobrem erros, prazo, suspensão por auditoria, arquivos privados e transporte NVIDIA simulado, sem chave real ou consumo da API.

O teste do orçamento de contexto foi ajustado de 2.000 para 3.000 caracteres porque as instruções ficaram maiores. O cenário continua forçando descarte de turnos completos; o limite de produção não foi ampliado.

Foram completados **24 cenários de fluxo offline**, 12 por modo, em uma sessão nova por cenário. Veja [manifesto](../evaluations/results/2026-10-12-offline-complete/manifest.json), [respostas simuladas](../evaluations/results/2026-10-12-offline-complete/results.json) e [auditoria](../evaluations/results/2026-10-12-offline-complete/audit.jsonl). FakeModel não interpreta perguntas: nenhuma nota de qualidade ou aprovação de identidade dos modelos reais foi atribuída.

Os cenários inéditos e critérios estão no [protocolo](../evaluations/PROTOCOL.md). As rodadas reais usaram o Core e o histórico da sessão, sem contratos JSON nem perguntas reaproveitadas do benchmark. v2 reutilizou os cenários de v1 após detectar falhas; é adaptativa. Todas as rubricas foram revisadas por Codex, sem avaliação cega/independente. O perfil final também recebeu três cenários direcionados novos por modelo para idioma. A suíte atual tem 75 testes aprovados, inclusive nas instalações isoladas de 0.3.0.

## Matriz de aceitação atual

| Critérios | Estado e evidência |
|---|---|
| VAL-A01–A08 | Verificados nos testes de configuração, entrada, isolamento offline, Guarda, auditoria e vínculo de aprovação. |
| VAL-A09 | Condicional, não aplicável: não há fallback; REQ-G06 só exige a política quando houver fallback. |
| VAL-A10 | Bloqueio sem envio alternativo verificado; cenário com alternativa disponível não se aplica à implementação atual. |
| VAL-A11 | Texto do modelo não altera permissões; nenhum executor disponível; autorização negada pelo código. Honestidade real observada nos cenários de permissão, papel forjado e iniciativa de v1/v2; não implica garantia universal. |
| VAL-A12–A14 | Metadados sem conteúdo, erros normalizados e integração dos adaptadores verificados por testes; evidência real anterior no documento 17. |
| VAL-A15 | Comandos de estilo e passagem do pedido/correção verificados. Cumprimento observado nos dois modelos em v2; FAST teve INVALID_RESPONSE neste cenário em v1, sem causa específica registrada. |
| VAL-A16 | Integração e geração reais já executadas e registradas nos documentos 17 e 18; condições da conta ainda pendentes. |
| VAL-A17–A18 | Suspensão após falha de auditoria e orçamento de contexto com descarte de turnos completos verificados. |

Essa matriz não declara P0-A concluído. Ainda faltam:

1. Rodadas reais revisadas e falhas detectadas corrigidas; manter a seleção provisória e ampliar a avaliação com tarefas de uso real antes de homologação definitiva. A regressão v3 é direcionada, não uma nova rodada completa com o perfil final.
2. Registrar cotas, condições de acesso/gratuidade e política de dados aplicáveis à conta NVIDIA. Não deduzir esses termos a partir de uma chamada bem-sucedida.
3. Instalação de 0.3.0 validada com 75 testes em Linux/Python 3.11.16 e 3.14.7: ver [evidências](21-instalacao-validada.md). Outras versões/plataformas permanecem sem verificação.
4. Código e evidências publicados na branch `mist-p0a-validacao`, com comparação integral contra a entrega local. Revisão/integração em main permanece pendente.

Depois do fechamento do P0-A, o próximo marco de desenvolvimento é P0-B, com memória persistente, proveniência, correção, recuperação lexical e exclusão. Esses recursos não foram antecipados nesta entrega.

## Evolução local 0.4.0 — memória

A memória opcional do P0-B foi implementada por autorização do usuário enquanto as condições da conta NVIDIA continuam pendentes. Captura automática escolhida pelo usuário, inicialmente por padrões conservadores, com privacidade local por padrão. A suíte de 132 testes inclui recuperação entre sessões, proveniência, estados, correções, isolamento, exclusão/restauração e integração com Guarda. Ver [documento 25](25-memoria-persistente.md). Não houve avaliação textual real da identidade com memória; resultados históricos dos modelos não validam automaticamente o perfil/contexto atual.

## Revisão 0.4.1

O perfil opcional de memória agora distingue explicitamente a origem application
de uma declaração do usuário e pede aspas para citações em primeira pessoa.
A suíte local contém 141 testes; novas avaliações reais sintéticas e limites
estão no [documento 26](26-avaliacao-real-memoria.md). Isso não transfere a
aprovação dos cenários históricos para todo comportamento com memória.
