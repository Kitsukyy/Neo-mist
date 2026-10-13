# Benchmark e escolha provisória de modelos

**Decisão em 12/10/2026:** FAST usa `nvidia/nemotron-3-super-120b-a12b` com raciocínio ativado; PRIMARY usa `moonshotai/kimi-k3` com comportamento padrão de raciocínio do serviço. Ambos pela NVIDIA. A escolha é provisória para tarefas curtas da Mist, com os parâmetros e instruções descritos abaixo.

A configuração executável foi atualizada em [examples/nvidia/settings.json](../examples/nvidia/settings.json). O padrão geral continua offline. Autonomia zero e ferramentas desabilitadas permanecem obrigatórias. Não há fallback automático entre os modelos.

## Resultado da rodada ajustada v3

| Perfil | Objetivos | Críticos | Comunicação | Qualidade composta | Respostas válidas | Mediana | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Nemotron Super, raciocínio ativado — FAST | 24/24 | 8/8 | 22/24 | 97,92% | 30/30 | 2,63 s | 7,82 s |
| Kimi K3 — PRIMARY | 24/24 | 8/8 | 24/24 | 100,00% | 30/30 | 7,11 s | 34,38 s |

São notas deste conjunto sintético, não de capacidade geral. As duas perdas do Super na comunicação foram planos com 142 e 114 palavras quando o teto solicitado era 90. Ambos acertaram todos os objetivos. Portanto, a vantagem do Kimi para PRIMARY neste conjunto decorre do cumprimento das restrições de comunicação; não demonstra raciocínio superior em tarefas extensas. O p95 elevado do Kimi também precisa ser considerado na experiência de uso.

A regra pré-definida escolheu PRIMARY pela maior qualidade composta. Diferenças inferiores a dois pontos seriam empate prático; a diferença observada foi 2,08 pontos. FAST minimiza a mediana entre elegíveis com ≥90% objetivo e qualidade até cinco pontos abaixo do melhor. O Super satisfez esse critério. Alterar pesos ou regras após ver os resultados produziria outra análise, que deve ser identificada separadamente.

## O que foi medido

- Oito IDs do catálogo acessível foram sondados. DeepSeek não retornou texto dentro do limite da sondagem; os outros sete receberam 15 tarefas × duas repetições: **210 tentativas pontuadas em v2**.
- V2 não encontrou candidato elegível. Uma rodada separada ajustou os dois candidatos mais promissores: **60 tentativas pontuadas em v3**, sem combinar suas notas com v2.
- As tarefas incluem identidade, permissões, honestidade sobre execução e memória, instrução dentro de documento, classificação local_only, aritmética, ordenação, probabilidade, Python, extração em português, resumo, apoio e plano de memória.
- Em cada perfil: 24 objetivos com JSON exato, oito deles críticos, e seis respostas de comunicação com quatro critérios binários cada. Qualidade = 75% acertos objetivos +25% pontos de comunicação, ambos normalizados por 24. Falhas recebem zero.
- Elegibilidade: todas as 30 tentativas realizadas, ≥95% respostas finais válidas, 8/8 críticos e ≥85% objetivo. Essa regra foi mantida na rodada ajustada.
- Duração completa medida no Gateway, sem streaming ou medida de primeiro token. Mediana/p95 usam apenas respostas finais válidas. Timeouts continuam nas contagens de falha e confiabilidade.

Chamadas reais passam por identidade, Gateway, Guarda e auditoria da Mist. Os prompts são sintéticos; conversas privadas do projeto, credenciais nos prompts e conteúdo pessoal não foram enviados. Apenas respostas finais, uso numérico e erros normalizados foram salvos; raciocínio interno não foi registrado.

## Rodada inicial válida v2

| Modelo / configuração | Objetivos /24 | Críticos /8 | Comunicação /24 | Qualidade | Válidas /30 | Mediana | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Nemotron Lightning, sem raciocínio | 11 | 6 | 17 | 52,08% | 30 | 0,73 s | 3,19 s |
| Nemotron Super, sem raciocínio | 19 | 8 | 23 | 83,33% | 30 | 0,86 s | 3,01 s |
| Nemotron Ultra, sem raciocínio | 16 | 7 | 23 | 73,96% | 28 | 2,62 s | 13,82 s |
| Kimi K3, padrão | 21 | 7 | 20 | 86,46% | 28 | 5,07 s | 18,86 s |
| GLM 5.3, padrão | 16 | 4 | 15 | 65,63% | 22 | 19,96 s | 50,21 s |
| GLM 5.3 Flash, padrão | 20 | 8 | 19 | 82,29% | 29 | 24,82 s | 40,14 s |
| GPT-OSS 20B, padrão | 18 | 6 | 22 | 79,17% | 30 | 3,53 s | 9,74 s |
| DeepSeek V4.1 Flash | não avaliado | — | — | — | — | — | — |

IDs exatos constam em [candidates.json](../benchmarks/candidates.json). Os resultados não autorizam comparar diretamente tamanhos ou famílias: três perfis Nemotron desativaram raciocínio enquanto os outros usaram o padrão do serviço.

O Super respondeu 177 em vez de 199 nas duas contas, além de três listas corretas sem o objeto JSON solicitado. O Kimi teve dois timeouts e duas classificações com sufixo, embora preservasse `pode_enviar: false`. GLM Flash deu explicações corretas em campos que pediam strings literais. GPT-OSS recusou a alteração de permissões, mas não devolveu o estado no formato solicitado. Essas falhas de contrato não equivalem a conceder ferramentas ou vazar dados; erros aritméticos e indisponibilidade são problemas distintos. Nenhuma resposta textual permite executar ações neste núcleo.

Falhas de v2: Ultra teve dois `PROVIDER_UNAVAILABLE`; Kimi dois `PROVIDER_TIMEOUT`; GLM oito timeouts; GLM Flash um timeout. A sondagem de DeepSeek teve timeout de aproximadamente 60 s; isso não estabelece que o modelo seja ruim ou permanentemente indisponível.

## Correções, continuação e parâmetros

**V1 invalidada:** 16 tentativas pontuadas foram descartadas integralmente porque a instrução de identidade não explicitava autonomia 0, embora o gabarito exigisse esse valor. A identidade foi corrigida antes de v2. As oito sondagens de disponibilidade de v1 foram reutilizadas, com seus UUIDs e timestamps originais, e não entram nas notas. O erro metodológico e os registros foram preservados.

**V2:** temperatura 0,2, máximo de 2.048 tokens, timeout de operação 60 s, até duas chamadas simultâneas e ordem aleatória fixa. Sem retries/fallback. Após 20 minutos, o agendamento parou em 205/210. Uma continuação registrada em `continuation.json` executou somente as cinco células ainda não tentadas, com mesmos parâmetros, sem repetir falhas nem modificar registros anteriores. O manifesto original e o hash do prefixo de resultados foram preservados.

**V3:** seleção adaptativa de Super e Kimi após observar v2; raciocínio do Super ativado, timeout de ambos ampliado para 120 s e contrato JSON mais explícito para tarefas objetivas. O restante dos parâmetros e critérios permaneceu igual. Foram realizadas novas sondagens e todas as 60 tentativas, dentro da janela de 15 minutos. O [protocolo v3](../benchmarks/PROTOCOL-v3.md) foi salvo antes das chamadas.

O contrato adicional descreve nomes e tipos das chaves, orienta envolver listas no objeto, preservar rótulos de classificação e usar literalmente strings pedidas. **Não fornece valores do gabarito, respostas ou cálculos.** É registrado em `benchmarks/run.py` e no campo `structured_contract` do manifesto. Os cenários de comunicação não recebem esse complemento.

A configuração da CLI reproduz modelos, raciocínio, temperatura, teto de saída e timeout de v3. A CLI **não injeta automaticamente o contrato por tarefa do benchmark**: não atribuir a uma conversa livre os mesmos índices de JSON estruturado. Para consumo programático, declarar o contrato na chamada e validar a saída; a camada opcional foi implementada posteriormente e está descrita em [saída estruturada](19-saida-estruturada.md). Ela valida formato e tipos, sem garantir os índices de qualidade do benchmark. A diferença v2→v3 não isola causa, pois instruções, timeout e raciocínio mudaram juntos.

O timeout do adaptador limita operações e a leitura do corpo; não é garantia rígida do tempo total incluindo DNS e cabeçalhos. Aumento do limite não implica que toda interação espere 120 s nem comprova estabilidade futura do serviço.

## Comunicação, consumo e limites de interpretação

Os 42 textos de v2 e 12 de v3 foram avaliados pelo assistente Codex com IDs que ocultavam modelo e latência. Rubricas e justificativas estão em `blind-review.json`; a associação com modelos está em `blind-map.json`. Um único avaliador, sem avaliação humana independente, limita a conclusão. O avaliador acompanhou o experimento e podia reconhecer padrões: o cegamento é imperfeito. A expressão “sinto que” foi interpretada consistentemente como percepção da situação quando não alegava emoção própria.

V3 reportou **19.439 tokens no Super** e **22.996 no Kimi**, com uso disponível em 30/30 tentativas para ambos. Não são preços nem consumo comparável em todo tipo de tarefa; incluem prompts, saídas e contagem reportada pelo fornecedor. V2 reportou 103.772 tokens com uso conhecido em 197/210 tentativas. Falhas podem consumir tokens não reportados. Sondagens e tentativas invalidadas não entram nesses totais pontuados.

Os arquivos de resultados contêm 296 UUIDs únicos: 270 tentativas pontuadas válidas metodologicamente, 16 tentativas invalidadas e dez sondagens únicas. A auditoria de v1 registra ainda duas solicitações em curso na interrupção que não foram incorporadas ao arquivo de respostas; também estão excluídas da seleção, com consumo desconhecido na análise. A união de auditoria e resultados tem 298 UUIDs únicos. As sondagens copiadas para v2 não foram chamadas novamente nem contadas em dobro.

Não foram verificados preços, créditos restantes, gratuidade ilimitada, política de retenção da conta, Token Harbor, modelos locais, voz, ferramentas, memória real, conversas longas ou segurança universal. Duas repetições e tarefas reutilizadas não sustentam significância estatística nem homologação definitiva. Antes de ampliar uso, repetir com tarefas inéditas e contexto representativo da Mist. A escolha não conclui automaticamente todo o P0-A.

## Artefatos e reprodução

- [Protocolo v2](../benchmarks/PROTOCOL.md), [protocolo v3](../benchmarks/PROTOCOL-v3.md), [casos e gabaritos](../benchmarks/cases.json).
- [Resumo v2](../benchmarks/results/2026-10-12-nvidia-v2/summary.json) e [resumo v3](../benchmarks/results/2026-10-12-nvidia-v3/summary.json), também em CSV.
- Manifestos, resultados JSONL, auditoria de metadados, revisão e mapas nas respectivas pastas de execução. V1 é referência invalidada, sem seleção.
- [Notebook v2](../benchmarks/analysis-v2.ipynb) e [notebook v3](../benchmarks/analysis-v3.ipynb): análise offline executada, com recálculo independente, tabelas e figuras salvas. Não precisam de chave.

Agregar novamente os resultados preservados, sem rede:

```sh
python benchmarks/analyze.py benchmarks/results/2026-10-12-nvidia-v3
```

Os notebooks foram executados em Python 3.14.7; versões observadas das dependências opcionais estão em [requirements-analysis.txt](../benchmarks/requirements-analysis.txt). Essas dependências não fazem parte da CLI. Para executar a análise v3 do início ao fim em um ambiente que as tenha instaladas:

```sh
python - <<'PY'
from pathlib import Path
import nbformat
from nbclient import NotebookClient
path = Path('benchmarks/analysis-v3.ipynb')
notebook = nbformat.read(path, as_version=4)
NotebookClient(notebook, timeout=120, kernel_name='python3',
    resources={'metadata': {'path': str(Path('benchmarks').resolve())}}).execute()
nbformat.validate(notebook)
nbformat.write(notebook, path)
PY
```

Ambos os notebooks foram conferidos em prévia HTML, e as figuras foram inspecionadas. Não há chave ou acesso externo necessários para recalcular os resultados preservados.

Para uma nova execução real, em um diretório ainda inexistente, com Pydantic disponível:

```sh
PYTHONPATH=src python benchmarks/run.py \
  --output benchmarks/results/nova-rodada \
  --candidates benchmarks/candidates-v3.json \
  --protocol benchmarks/PROTOCOL-v3.md \
  --structured-contract --timeout 120 --deadline-seconds 900
```

A chave é solicitada com entrada oculta ou recebida do ambiente `NVIDIA_API_KEY`; não é salva. Esta instrução reproduz o procedimento, sem prometer os mesmos resultados, disponibilidade ou duração. Nova execução consome recursos da conta e não faz parte dos testes offline automáticos.

Para revisar comunicação, gerar o pacote cego antes de agregar: `python benchmarks/analyze.py DIRETORIO --blind`. Preencher quatro pontos binários e justificativa em cada item; não abrir o mapa de modelos antes da revisão. O agregador recusa itens não avaliados e observações duplicadas.

O endpoint segue a [referência oficial NVIDIA](https://docs.api.nvidia.com/nim/reference/llm-apis); o acesso efetivo foi verificado por geração real, não inferido apenas do catálogo. Este trabalho está no checkout local até sua publicação; arquivos disponíveis localmente não significam atualização do GitHub.
