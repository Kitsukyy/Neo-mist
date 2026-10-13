# Controle preventivo de requisições NVIDIA

Mist 0.3.1 · 12/10/2026. Validação local, sem usar a API NVIDIA.

## Motivo e fontes

O usuário lembrou 40 requisições por minuto e possível bloqueio por uso repetido no limite. O [aviso oficial do fórum NVIDIA](https://forums.developer.nvidia.com/t/api-rate-limit-increase-is-not-granted-by-requesting-it-here/368420) reconhece 40 RPM numa resposta de 13/05/2026 e informa que os limites dependem do modelo, uso e tráfego. Isso não confirma a cota vigente da conta da Mist. Não foi encontrada regra oficial de banimento automático por atingir 40 RPM. A [documentação NVIDIA](https://docs.nvidia.com/rag/latest/troubleshooting.html) identifica HTTP 429 como limitação de requisições; esse código isolado não comprova banimento.

## Comportamento implementado

- Todos os adaptadores NVIDIA do mesmo processo compartilham uma fila: apenas uma geração fica em andamento.
- Os inícios dos envios são separados por pelo menos 2,1 segundos, inclusive quando a preparação do transporte leva tempo. Isso permite no máximo 29 inícios numa janela de 60 segundos; é uma escolha conservadora da aplicação, não uma cota oficial nem garantia de aceitação pela NVIDIA.
- FAST e PRIMARY, novas aplicações e novas credenciais no mesmo processo compartilham o controle. Não há multiplicação da capacidade por modelo ou chave.
- HTTP 429 pausa os próximos envios NVIDIA pelo restante do processo. Chamadas em espera recebem RATE_LIMIT sem abrir outro transporte. Não há retry, fallback nem retomada automática.
- `/reset` limpa contexto e preferências, mas não remove a pausa. Criar outra aplicação no mesmo processo também não remove a pausa.
- Ao receber 429, aguardar e verificar a conta/estado do serviço antes de iniciar outra execução. Não reiniciar repetidamente para contornar o limite. A aplicação não determina quando a NVIDIA voltará a aceitar chamadas.
- O runner de identidade encerra a rodada em RATE_LIMIT, erro de autenticação ou auditoria, preservando resultados parciais. O benchmark já encerra nesses erros.
- Falhas de transporte também ocupam o intervalo. Interromper a espera cancela o envio sem abrir a conexão.

A Guarda e a aprovação auditada continuam anteriores ao adaptador. Bloqueios por cadência são registrados como failed/rate_limit e não atualizam o histórico. O timeout configurado continua aplicado ao transporte; espera na fila/cadência pode acrescentar tempo à interação. Não há novas ferramentas, permissões, conteúdo em logs ou armazenamento de credenciais.

## Limites

O controle abrange apenas um processo. Outras execuções da Mist e outros programas na mesma conta não são coordenados. Neste estágio, usar uma única execução NVIDIA; coordenação entre processos é trabalho futuro. O estado não é persistido ao encerrar o processo. Este controle não comprova cumprimento de todos os limites de tokens, cotas ou regras dinâmicas do serviço e não encerra as pendências da conta do [documento 22](22-condicoes-nvidia.md).

As rodadas reais e manifestos anteriores permanecem intactos. Não foram refeitos benchmarks ou chamadas reais nesta revisão; seus índices não são atribuídos ao novo controle. Identidade e modelos selecionados não mudaram.

## Validação

A suíte atual contém 84 testes. Novos cenários verificam cadência entre adaptadores/modelos, preparação lenta, geração longa, despertar antecipado, contagem de falha, cancelamento, pausa após 429 entre aplicações e chamada concorrente em espera. Outro teste verifica encerramento integral da avaliação ao receber 429. Tempo e transporte simulados, sem envio externo.

Corrigida uma expectativa antiga do teste de saída estruturada: esperava 2.048 tokens enquanto o exemplo atual já utiliza 4.096. Agora confere o teto atual. Recibos antigos permanecem históricos; avaliar esta revisão pelos novos recibos de instalação 0.3.1 do [documento 21](21-instalacao-validada.md).
