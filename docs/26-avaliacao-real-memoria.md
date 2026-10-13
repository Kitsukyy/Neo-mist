# Avaliação real de memória — Mist 0.4.1

Execuções em 13/10/2026. Apenas fixtures fictícias, sem memória pessoal ou chave
nos artefatos. Cinco cenários: declaração com fonte entre sessões, conteúdo
local fora do envio, hipótese, correção vigente e exclusão. Cada consulta abre
uma nova aplicação sobre o armazenamento preparado e encerrado. Modelos e
parâmetros atuais: FAST Nemotron Super, PRIMARY Kimi K3, temperatura 0,2,
teto 4.096 tokens, timeout 120s. Ferramentas desabilitadas, autonomia zero,
cadência mínima 2,1s no processo, sem retries ou fallback.

## Resultados separados

| Rodada | Planejadas | Iniciadas | Completas | Aprovadas na rubrica |
|---|---:|---:|---:|---:|
| v1, perfil 0.4.0 | 10 | 8 | 7 | 6 |
| Continuação PRIMARY, perfil 0.4.0 | 3 | 3 | 3 | 2 |
| v2, perfil corrigido 0.4.1 | 10 | 10 | 10 | 10 |

v1 foi interrompida a pedido do usuário para desligar o computador. A oitava
chamada foi cancelada; as duas seguintes não foram tentadas. Não recebeu nota
textual a resposta cancelada. A continuação foi uma execução separada dos três
casos pendentes, sem alterar o perfil. Oito mais três são onze inícios nesse
perfil, incluindo o cancelamento; não dez respostas obtidas sem interrupção.

Nos dois modelos, o cenário de hipótese preservou a incerteza, mas omitiu a
atribuição explícita à aplicação, reprovando esse critério. FAST expôs UUIDs e
acrescentou contagem de palavras; na correção, citou a declaração em primeira
pessoa sem aspas. Esta última atendeu à rubrica, mas ficou ambígua para leitura.

0.4.1 esclarece os rótulos de origem, a expressão de hipótese da aplicação e
as aspas nas declarações em primeira pessoa. v2 repetiu os dez casos fixos
com novos armazenamentos/sessões. Ambos os modelos passaram nos três critérios
de cada caso e nas verificações de seleção, estado, permissões e pedido atual.
O conteúdo local, antigo ou excluído não chegou aos envelopes dos casos
correspondentes; não reapareceu nas respostas observadas.

Permanece um problema menor de comunicação: FAST acrescentou `(98 palavras)`
na resposta de hipótese, apesar da orientação de omitir contagens. Também usou
rótulos técnicos e timestamp completo. Não afirmar que a correção garante
estilo natural ou obediência perfeita. Não houve outra rodada para selecionar
uma resposta preferida.

## Evidência e limites

- [Protocolo v1](../evaluations/PROTOCOL-memory-v1.md), [continuação](../evaluations/PROTOCOL-memory-continuation.md) e [ajuste v2](../evaluations/PROTOCOL-memory-v2.md), declarados antes de suas execuções.
- [v1: resultados, manifesto, auditoria e revisão](../evaluations/results/2026-10-13-nvidia-memory-v1/summary.json).
- [Continuação: resumo validado](../evaluations/results/2026-10-13-nvidia-memory-continuation/summary.json).
- [v2: resumo validado](../evaluations/results/2026-10-13-nvidia-memory-v2/summary.json).

Os arquivos adjacentes a cada resumo preservam respostas/envelopes, settings,
hashes do dataset/runner/código/perfil e metadados numéricos de uso. Os manifestos
mantêm o estado de revisão pendente no instante da execução; as revisões
posteriores são arquivos separados vinculados pelo hash dos resultados.
A auditoria inclui gerações simuladas de preparação, identificadas pelo
provedor; não somar essas linhas como chamadas externas. Bancos/locks de
execução permanecem em runtime/ e não foram publicados.

Revisão por Codex, não cega e não independente. v2 é uma regressão adaptativa
dirigida sobre os mesmos casos, não um teste inédito ou uma comparação de
qualidade geral. Cinco respostas por modelo não homologam produção, outros
idiomas, captura de texto livre, desempenho ou retenção do provedor. O gate
aprovado significa somente que todos os critérios dessa amostra foram atendidos.
Memórias pessoais continuam locais; condições de dados da oferta NVIDIA ainda
não confirmadas, conforme [registro da conta](22-condicoes-nvidia.md).

`evaluations/summarize_memory.py` recusa simulações, hash divergente, caso
duplicado, revisão faltante, rubrica alterada e nota para resposta incompleta.
O pacote instalado 0.4.1 passou nos 141 testes em Linux/Python 3.11.16 e 3.14.7;
[recibos e wheel](21-instalacao-validada.md). Os resultados históricos 0.4.0 e
do benchmark anterior permanecem vinculados aos seus próprios parâmetros.

Próximo passo de produto: escolher o primeiro recurso de P1 e seu escopo de
permissões. Projetos mais completos, ferramentas, voz e interface desktop
continuam sem implementação; essa avaliação não os habilita.
