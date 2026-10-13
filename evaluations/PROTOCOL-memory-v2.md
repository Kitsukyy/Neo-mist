# Regressão após ajuste de proveniência — 13/10/2026

Declarado antes da execução desta rodada. A rodada v1 foi interrompida pelo
usuário; a continuação separada completou os três casos PRIMARY restantes.
Ambos os modelos distinguiram hipótese de fato, mas omitiram sua origem
explícita na aplicação, reprovando um critério. FAST ainda acrescentou contagem
de palavras e UUIDs sem pedido; a citação da correção ficou ambígua sem aspas.
Esses registros permanecem preservados, sem reaproveitamento como v2 aprovada.

Mist 0.4.1 esclarece no perfil opcional de memória os rótulos user/application/
model, exige atribuição explícita da hipótese da aplicação e pede aspas para
declarações em primeira pessoa. Datas/origem podem ser explicadas; IDs técnicos
e contagens de palavras são omitidos salvo pedido. Sem alteração do schema,
dos dados, dos modelos, dos parâmetros, da recuperação ou das permissões.

Reexecutar todos os cinco casos fixos em FAST e PRIMARY uma vez: dez chamadas
novas, novos armazenamentos/sessões, mesmo dataset e rubrica do protocolo v1,
temperatura 0,2, teto 4.096, timeout 120s e sem retries/fallback. A revisão também
anota UUIDs/contagens não solicitados e ambiguidade de citação como problemas de
comunicação. Todos os critérios originais e verificações locais precisam passar;
problema material permanece descrito, mesmo se os três critérios forem atendidos.

Rodada adaptativa e dirigida, revisada pelo Codex sem cegamento/independência.
Não homologar qualidade geral, cenários inéditos ou produção a partir dela.
Execução: `PYTHONPATH=src python evaluations/run_memory.py --real --ask-api-key --output runtime/memory-real-v2`.
