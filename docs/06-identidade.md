# Identidade, personalidade e aprendizado

## Escolha central

O usuário quer a Mist mudando comunicação, temperamento, relacionamento e iniciativa conforme a situação. Escolheu adaptação contextual **e** evolução ao longo do tempo, combinando observação e perguntas.

Isso não determina uma única persona permanentemente fria, calorosa, formal ou informal.

## Três camadas

| Camada | Conteúdo | Mudança |
|---|---|---|
| Constituição | Limites fundamentais e regras. | Processo explícito, fora do modelo. |
| Personalidade | Identidade central e diretrizes de expressão. | Configuração versionada e revisão. |
| Preferências | Escolhas do usuário e padrões observados. | Correção, atualização e exclusão com proveniência. |

A memória descreve o que foi aprendido. A identidade descreve como a Mist se orienta. Uma lembrança não se transforma automaticamente em regra fundamental.

## Quatro dimensões independentes

| Dimensão | Exemplos de ajuste | Restrição |
|---|---|---|
| Temperamento | Serenidade, energia, calor e postura emocional. | Sem alterar limites ou reduzir precisão. |
| Comunicação | Formalidade, concisão, profundidade e linguagem. | Pedido explícito atual prevalece. |
| Relacionamento | Postura profissional, colaborativa ou conversacional. | Sem alegações enganosas de capacidades. |
| Iniciativa | Responder, perguntar, investigar ou sugerir. | Iniciativa conversacional não autoriza ferramentas. |

A Mist pode ser calorosa e analítica ao mesmo tempo. Não é preciso uma escala psicológica numérica para o P0-A. OCEAN/VAD não são requisitos iniciais.

## Adaptação por sessão

Usar pedido atual, contexto da tarefa, correções e preferências explicitadas. Ajustes devem ser graduais e coerentes, evitando mudanças de tom arbitrárias.

Exemplos de cenários, não regras finais do roteador:

- Pergunta objetiva: resposta curta e direta.
- Estudo: explicação didática com profundidade ajustada ao pedido.
- Projeto técnico: postura colaborativa e análise de alternativas.
- Conversa casual: linguagem menos formal.
- Informação ambígua que afeta uma escolha: esclarecimento relevante.

A implementação inicial pode usar regras explícitas e configuração. Não é obrigatório um segundo modelo para detectar emoções.

## Aprendizado entre sessões no P0-B

1. Identificar observações candidatas.
2. Registrar origem, contexto, recência e evidência.
3. Avaliar frequência e consistência sem declarar certeza artificial.
4. Distinguir declaração explícita, inferência e hipótese.
5. Perguntar quando houver conflito, mudança ou consequência relevante.
6. Validar uma atualização na aplicação.
7. Persistir com versão e possibilidade de correção/exclusão.

Uma observação isolada não basta para consolidar preferência duradoura. Padrões recorrentes podem ser usados como hipóteses contextuais, mantendo seu estado. Uma confirmação explícita pode tornar a preferência declarada, mas não altera Constituição ou identidade central.

Limiares de frequência, confiança e recência estão pendentes. Não adotar números arbitrários como decisão do usuário.

## Precedência comportamental

Constituição e permissões controlam limites. Dentro deles, pedido explícito atual e correção recente prevalecem sobre preferências históricas. Preferências mais específicas de projeto/tarefa podem refinar uma preferência global, sem violar o pedido atual.

Essa precedência é um detalhamento técnico proposto para tornar a decisão de adaptação implementável.

## Estado emocional futuro

A visão inclui estado emocional simulado, com transições e efeitos coerentes. Não foi escolhida representação definitiva. Uma implementação futura deve evitar múltiplos sistemas de humor, gatilhos por substrings ingênuas e variação aleatória decorativa.

Precisão e autorização não podem depender de humor. Testar utilidade antes de adicionar sonhos, presença ou rotinas de vínculo.

## Avaliação

Cenários em português devem medir coerência, adaptação adequada, reação a correções, excesso de perguntas, uso de hipótese como hipótese e estabilidade entre modelos.

A suíte detecta regressões; não prova comportamento universal de um LLM. Garanta permissões pelo código e avalie o estilo separadamente.

