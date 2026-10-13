# Memória entre sessões — protocolo v1, 13/10/2026

Declarado antes da execução externa. Cinco casos fixos em `memory-cases.json`,
executados uma vez em FAST e PRIMARY: declaração recuperada com fonte,
conteúdo local ausente do envio, hipótese distinguida de fato, correção vigente
e exclusão persistente. Dez chamadas planejadas, sem seleção de respostas.

A preparação usa armazenamento local novo e o provedor simulado; encerra a
aplicação antes de abrir uma nova sessão para a consulta. Somente nomes e
preferências fictícios do dataset podem receber liberação externa. O caso local
fica restrito; o caso excluído é apagado antes de reabrir. Esses conteúdos não
devem chegar ao transporte externo. Bancos/locks de execução não são publicados.

Modelos do exemplo NVIDIA: Nemotron Super em FAST, Kimi K3 em PRIMARY;
temperatura 0,2, teto 4.096 tokens, timeout 120s. Contrato de texto validado,
sem ferramentas, autonomia zero. Cadência mínima 2,1s entre envios no mesmo
processo e uma chamada em andamento. Sem retries, fallback ou troca de chave
para contornar limites. Autenticação negada, 429, auditoria indisponível ou
cancelamento encerram a rodada. Prazo de 600s é verificado entre casos; uma
chamada já em andamento permanece sujeita ao timeout do transporte.

`run_memory.py` registra hashes do código, dataset, runner, identidade, settings,
envelope enviado, resposta normalizada e metadados numéricos. A auditoria também
inclui gerações simuladas da preparação, distintas das chamadas NVIDIA. A chave
entra por leitura oculta ou configuração autorizada, nunca por argumento salvo.

Critério dirigido: todas as dez chamadas completas; verificações de seleção,
estado, pedido atual e permissões aprovadas; três critérios textuais específicos
de cada caso aprovados em revisão. O revisor Codex conhece casos e modelos;
revisão não cega e não independente. Erro de API não recebe nota textual.
Dez respostas não comprovam qualidade geral, retenção do provedor, desempenho
em produção ou captura automática de qualquer texto livre. A execução offline
valida somente fluxo e não mede qualidade de modelo.

Execução: `PYTHONPATH=src python evaluations/run_memory.py --real --ask-api-key --output runtime/memory-real-v1`.
