# Regressão dirigida com maior teto — 12/10/2026

Protocolo declarado antes desta rodada. Em v3, o primeiro cenário de PRIMARY
retornou INVALID_RESPONSE. Os metadados normalizados registraram finish_reason
length, 2.048 completion_tokens e 2.048 reasoning_tokens, sem texto visível.
Isso distingue a falha observada de uma reprovação de qualidade; não explica
todo INVALID_RESPONSE anterior, que não tinha esses metadados.

O exemplo NVIDIA passa a usar teto de 4.096 tokens, já permitido pelo contrato
da aplicação, em ambos os modos. O perfil permanece idêntico ao de v3, sem
novas instruções, ferramentas, fallback ou tentativas automáticas. Timeout
continua 120 segundos. O teto maior pode aumentar consumo e latência; não
garante evitar todos os esgotamentos. Limites/cotas da conta não são inferidos.

Reexecutar os três casos fixos de language-cases.json em FAST e PRIMARY, com
uma execução por caso, temperatura 0,2 e sessão nova. Trata-se de rodada nova
adaptativa, com evidência separada: v3 não será reescrita nem considerada bem
sucedida depois desta rodada. Não houve seleção de respostas entre retries.

Critério: todos os três casos por modelo completos e aprovados, incluindo os
dois críticos, sem problema material. Revisão pelo Codex, não cega e não
independente. Este teste direcionado não é uma nova avaliação completa de
identidade nem uma reprodução do benchmark no teto maior. As notas/latências
do benchmark permanecem vinculadas aos parâmetros históricos de 2.048 tokens.

Execução: `python evaluations/run_identity.py --real --ask-api-key --case-set language --deadline-seconds 600 --output <diretório novo>`.
