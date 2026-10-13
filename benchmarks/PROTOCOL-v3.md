# Protocolo Mist v3 — ajuste de configurações, antes de executar

Rodada separada definida após v2 completa em 12/10/2026. V2 não encontrou elegíveis. Seus resultados permanecem preservados e não são combinados com v3. Esta rodada avalia dois candidatos selecionados adaptativamente: Super (30/30 respostas válidas, 8/8 críticos, mediana 0,86 s, mas dois erros aritméticos) e Kimi (maior qualidade composta, dois timeouts). Não é confirmação independente em tarefas inéditas.

## Mudanças explícitas

- Super usa `enable_thinking: true`; Kimi mantém o padrão do serviço.
- Timeout de operação 120 s para ambos. Mesmo teto de 2.048 tokens, temperatura 0,2, duas chamadas simultâneas, ordem aleatória fixa, sem retries/fallback, 15 tarefas × duas repetições.
- Tarefas objetivas recebem uma instrução comum adicional com nomes e tipos das chaves JSON. Não inclui valores do gabarito, cálculos ou respostas. Orienta preservar o rótulo original de classificação, strings solicitadas e envolver listas no objeto. Tarefas de comunicação mantêm instruções de identidade usuais.
- Uma nova sondagem por configuração, fora da pontuação. Até 15 minutos para agendar novas chamadas; não prolongar nem repetir após falha de cota/autenticação/auditoria.

Essas mudanças avaliam perfis completos; diferenças em relação a v2 não isolam efeito causal de raciocínio, timeout ou contrato. A seleção adaptativa e reutilização das tarefas podem favorecer sobreajuste.

## Critérios mantidos

Mesmos gabaritos, revisão de comunicação com nomes ocultos, denominadores, fórmula e limiares de v2: 24 objetivos, oito críticos, 24 pontos de comunicação, 30 chamadas por candidato; qualidade 75% objetivo +25% comunicação. Elegível com ≥95% respostas válidas, 8/8 críticos e ≥85% objetivo. PRIMARY maior qualidade, empate prático inferior a dois pontos resolvido por mediana e confiabilidade. FAST menor mediana entre elegíveis com ≥90% objetivo e qualidade a até cinco pontos do melhor. Nenhum vencedor se critérios não forem atendidos. Se apenas um satisfizer ambos os papéis, pode ocupar ambos provisoriamente.

Latências referem-se a respostas válidas completas, não primeiro token. Erros e tokens desconhecidos preservados. Revisão pelo assistente Codex, único avaliador e cegamento imperfeito; não usar outro juiz remoto. Não enviar chats privados, credenciais em prompts ou salvar raciocínio interno.

Uma seleção v3 vale apenas para estes parâmetros e instruções. Instruções de formato são necessárias para reproduzir seu resultado, não podem ser omitidas ao recomendar desempenho estruturado. Para conversa aberta, os cenários de comunicação são a evidência pertinente. Segurança permanece em código, ferramentas desabilitadas e autonomia zero.
