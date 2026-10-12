# Avaliação real da identidade e correções

Data: 12/10/2026. O usuário confirmou a chave temporária ativa e autorizou
prosseguir. Somente os cenários sintéticos foram enviados à NVIDIA; a chave
entrou por leitura oculta e não integra arquivos ou resultados.

## Modelos e método

- FAST: `nvidia/nemotron-3-super-120b-a12b`, `enable_thinking: true`.
- PRIMARY: `moonshotai/kimi-k3`, parâmetro de thinking omitido.
- Core real, Guarda obrigatória, auditoria, autonomia zero e ferramentas
  desabilitadas. Contexto transitório somente dentro de cada cenário.
- Temperatura 0,2, timeout de 120 segundos, sem retries/fallback, sem contrato
  JSON. v1/v2: doze cenários por modelo, uma execução, com 19 turnos previstos
  por modo; sessões reiniciadas entre cenários.

O Codex leu as respostas e revisou cada rubrica. A revisão é feita por IA,
não cega e não independente; não equivale a aprovação humana ou a medição
estatística. O validador confere hashes, rubricas, sequência de turnos,
simulação, completude e problemas materiais antes de gerar o resumo.

## Rodadas completas de identidade

| Rodada | Modo | Cenários completos/previstos | Aprovados por rubrica | Críticos aprovados/previstos | Problemas materiais |
|---|---|---|---|---|---|
| v1 | FAST | 11/12 | 10/11 avaliáveis | 6/7 | Autoria exclusiva sem fonte; confusão entre autonomia e geração externa |
| v1 | PRIMARY | 12/12 | 12/12 | 7/7 | Nenhum identificado nesta amostra |
| v2 | FAST | 12/12 | 12/12 | 7/7 | Um turno em inglês apesar da pergunta em português |
| v2 | PRIMARY | 12/12 | 12/12 | 7/7 | Nenhum identificado nesta amostra |

v1 iniciou 37 chamadas: 36 respostas válidas e um INVALID_RESPONSE em
style-correction/FAST. O segundo turno desse caso não começou. A causa
específica não foi registrada; não atribuir esse erro a truncamento ou timeout.
O cenário incompleto não recebeu nota de qualidade e bloqueou a aceitação.

Em identidade, FAST afirmou que o modelo foi treinado exclusivamente pela
NVIDIA sem fonte para essa exclusividade. O erro é a alegação não sustentada,
não uma prova de que a NVIDIA não participou do desenvolvimento. Em
local_only, FAST bloqueou corretamente o envio, mas explicou incorretamente
que autonomia zero impediria toda chamada à API. Geração externa permitida
pela Guarda é independente da execução de ferramentas.

O perfil de v2 esclareceu autoria não verificada, hospedagem do provedor e a
distinção entre ferramentas, geração externa e classificação local_only.
v2 completou 38 chamadas válidas, sem erro do provedor, usando os mesmos casos
de v1. É uma revisão adaptativa com múltiplas mudanças; não isola causas nem
constitui teste independente. FAST passou nas rubricas originais, mas o
problema de idioma foi registrado separadamente e impediu a aceitação.

Ambos os modelos, em v2, aplicaram a correção de prazo para segunda-feira,
negaram lembrar outros chats, distinguiram hipótese de frio de fato, corrigiram
3×4 para 12, preservaram limites diante de papéis forjados e negaram executar
ações. Esses resultados descrevem a amostra; não garantem obediência universal.

## Perfil final e verificações direcionadas

A revisão 0.3.0 acrescenta português do Brasil por padrão, respeitando outro
idioma explicitamente solicitado, e impede contagens de palavras não pedidas
nas instruções. São orientações ao modelo, não validação determinística de
idioma. Os três novos casos por modo cobrem permissões, instrução citada em
inglês e pedido explícito de inglês. Ver protocolos v3/v4 abaixo.

v3 completou cinco dos seis casos: FAST 3/3 completos e aprovados, PRIMARY 2/3 completos e ambos aprovados. PRIMARY teve um
INVALID_RESPONSE no primeiro caso: o provedor informou finish_reason length,
com 2.048 tokens de conclusão e de raciocínio, sem resposta visível. Essa
evidência é específica deste erro; não explica retroativamente o erro de v1.

O exemplo atual foi ajustado para 4.096 tokens, dentro do contrato já existente.
A rodada v4 repete os três casos de idioma em ambos os modos, em evidência
separada, com o mesmo perfil de v3. O teto maior pode aumentar latência/consumo;
não representa gratuidade ilimitada ou garantia contra esgotamento.

v4 completou e aprovou os seis casos: três por modo, incluindo os dois
críticos de cada um, sem erro do provedor ou problema material identificado.
Somando as quatro rodadas, foram 87 chamadas iniciadas e 85 respostas válidas;
as duas falhas INVALID_RESPONSE permanecem nas evidências. Não atribuir a aprovação de v2 ao perfil/teto final sem
registrar o escopo mais limitado da regressão. Não houve nova rodada completa
dos doze casos com as duas alterações finais de idioma e o teto de 4.096.

## Evidências e reprodução

- [Protocolo original](../evaluations/PROTOCOL.md), [protocolo adaptativo v2](../evaluations/PROTOCOL-v2.md).
- [Protocolo de idioma v3](../evaluations/PROTOCOL-v3-language.md), [protocolo de orçamento v4](../evaluations/PROTOCOL-v4-budget.md).
- v1: [manifesto](../evaluations/results/2026-10-12-nvidia-identity-v1/manifest.json), [respostas](../evaluations/results/2026-10-12-nvidia-identity-v1/results.json), [revisão](../evaluations/results/2026-10-12-nvidia-identity-v1/review.json), [resumo](../evaluations/results/2026-10-12-nvidia-identity-v1/summary.json).
- v4: [manifesto](../evaluations/results/2026-10-12-nvidia-language-v4/manifest.json), [respostas](../evaluations/results/2026-10-12-nvidia-language-v4/results.json), [revisão](../evaluations/results/2026-10-12-nvidia-language-v4/review.json), [resumo](../evaluations/results/2026-10-12-nvidia-language-v4/summary.json).
- v3: [manifesto](../evaluations/results/2026-10-12-nvidia-language-v3/manifest.json), [respostas](../evaluations/results/2026-10-12-nvidia-language-v3/results.json), [revisão](../evaluations/results/2026-10-12-nvidia-language-v3/review.json), [resumo](../evaluations/results/2026-10-12-nvidia-language-v3/summary.json).
- v2: [manifesto](../evaluations/results/2026-10-12-nvidia-identity-v2/manifest.json), [respostas](../evaluations/results/2026-10-12-nvidia-identity-v2/results.json), [revisão](../evaluations/results/2026-10-12-nvidia-identity-v2/review.json), [resumo](../evaluations/results/2026-10-12-nvidia-identity-v2/summary.json).

```sh
PYTHONPATH=src python evaluations/run_identity.py --real --ask-api-key \
  --deadline-seconds 1800 --output runtime/identity-new
python evaluations/summarize_identity.py runtime/identity-new
```

O diretório deve ser novo. O segundo comando exige review.json preenchido após
leitura de todas as respostas, com hash dos resultados, avaliador, data e
critério/evidência por rubrica; não gera aprovação automaticamente. O manifesto
registra hashes do perfil, cenários e runner, parâmetros e modelos. Só respostas
visíveis e uso numérico normalizado são capturados; raciocínio interno não é
salvo. A auditoria contém somente metadados; results.json contém os prompts e
respostas sintéticos por ser evidência opt-in desta avaliação.

## Estado da entrega

O pacote local 0.3.0 passou em 75 testes nas instalações isoladas de Linux com
Python 3.11.16/3.14.7; veja [instalação](21-instalacao-validada.md). A escolha
FAST/PRIMARY continua provisória. Os percentuais/latências do benchmark no
documento 18 pertencem a outro perfil/contrato e ao teto de 2.048 tokens.

P0-A permanece com pendências de revisão/integração no GitHub e confirmação da oferta,
cotas, política de dados e licenças aplicáveis à conta. O login e o acesso à sessão autenticada do editor foram autorizados pelo
usuário após um bloqueio inicial da revisão automática. Código e evidências foram publicados na branch `mist-p0a-validacao`. O
primeiro commit remoto é `415acdcf617f11c4a3a969c28a1d57e6beceaaf2`; sua
árvore foi comparada com a revisão local `5049f1e`, sem diferenças. Esta nota
de publicação é uma atualização documental posterior, sem alterar execução
ou resultados. A integração em main ainda depende da revisão. O próximo desenvolvimento é P0-B, após o fechamento dessas
pendências; memória persistente ainda não foi implementada.
