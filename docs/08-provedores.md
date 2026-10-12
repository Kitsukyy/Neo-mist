# Gateway, modelos e provedores

## Disponibilidade relatada

| Provedor | Informação recuperada | Estado |
|---|---|---|
| NVIDIA NIM | Usuário possui acesso e relata vários modelos gratuitos. | Acesso relatado; catálogo/cotas precisam de confirmação. |
| Token Harbor | Usuário possui API com DeepSeek V4.1 Flash, MiMo V2.6 Flash e Claude Haiku 5.5. | Nomes relatados; IDs e condições não verificados aqui. |

Os chats também mencionam candidatos como Nemotron 3 Ultra/Super/Nano, GPT-OSS 120B, Kimi K3 e GLM 5.3/Flash. Essas referências são histórico de pesquisa, não garantia de que tais nomes/versões existem no catálogo acessível nem seleção para implementação.

Não escolher por tamanho, reputação ou suposição de estilo. Comparar os modelos realmente disponíveis.

## Papéis e seleção

O documento mestre propõe dois papéis:

- **Rápido:** conversa cotidiana, baixa complexidade e prioridade de latência.
- **Principal:** tarefas que exigem análise, planejamento ou maior profundidade.

| Modo proposto | Comportamento |
|---|---|
| AUTO | Escolha por regras explícitas entre modelos configurados. |
| FAST | Escolha manual do rápido. |
| PRIMARY | Escolha manual do principal. |

AUTO é o padrão proposto. A seleção manual tem prioridade se a configuração for válida. Modelo ausente não deve ser substituído silenciosamente sem política declarada.

DeepSeek V4.1 Flash/Token Harbor é a indicação de rápido na síntese do assistente. Não foi localizada confirmação explícita do usuário para esse papel nos trechos recuperados. O principal continua pendente.

## Roteador

Implementação inicial determinística: características da tarefa, profundidade solicitada, necessidade de planejamento e preferências explícitas. Não introduzir um terceiro LLM apenas para decidir qual responde.

Regras, palavras-chave e limiares finais não estão definidos. Testar classificações e registrar modo/modelo escolhidos sem salvar texto sensível desnecessário.

Não rotacionar indiscriminadamente entre dezenas ou centenas de modelos.

## Responsabilidade do Gateway

Normalizar mensagens, parâmetros permitidos, resposta, uso quando disponível, duração e erro. Validar capacidades e configuração. Centralizar timeouts e tentativas limitadas.

O Gateway não mantém dependência do Core em formatos proprietários. Credenciais são resolvidas pela configuração operacional e não entram no objeto conversacional.

## Capacidades

Cada modelo deve ter capacidades verificadas, distinguindo “não suporta” de “não verificado”: contexto, streaming, formatos estruturados, modalidades e ferramentas.

No P0-A, capacidade de ferramenta do provedor não habilita ferramentas da aplicação. Saída estruturada, quando usada, é validada antes de qualquer interpretação.

## Erros e tentativas

| Categoria | Tratamento esperado |
|---|---|
| Configuração/modelo inexistente | Erro claro antes do envio. |
| Credencial ausente/inválida | Não expor valor; corrigir configuração. |
| Timeout/conexão | Tentativa limitada apenas conforme política. |
| Cota/rate limit | Informar restrição; respeitar limites. |
| Resposta inválida | Erro normalizado e sem simular sucesso. |
| Guarda/auditoria/autorização | Bloqueio; sem fallback. |
| Capacidade incompatível | Recusar ou adaptar explicitamente, conforme política. |

Número de tentativas e duração de timeout são parâmetros pendentes. Retentativas podem duplicar processamento em um provedor que recebeu a primeira solicitação; não prometer execução exatamente uma vez sem suporte.

## Fallback

Precisa de alternativa configurada, falha recuperável e autorização de envio ao destino alternativo. Repetir Guarda/auditoria sobre payload final.

A exigência de APIs gratuitas não autoriza fallback pago. Esgotamento de cota pode encerrar a solicitação com explicação. FakeModel não deve mascarar uma falha real como resposta de IA normal.

## FakeModel

Determinístico, sem rede, sem credenciais e claramente identificado. Deve permitir simular respostas válidas, erros, timeouts e respostas incompatíveis para testes.

Testes contam chamadas aos adaptadores para provar bloqueios. FakeModel valida a infraestrutura, não qualidade de linguagem ou raciocínio.

## Checklist de integração

Antes de habilitar cada modelo, registrar:

1. ID exato, endpoint e autenticação.
2. Fonte oficial e data da verificação.
3. Acesso da conta, cotas, limites de taxa e condições de gratuidade.
4. Capacidades e parâmetros aceitos.
5. Retenção e uso dos dados pelo serviço.
6. Timeouts, erros reais e limites de retry.
7. Resultado de teste com conteúdo sintético e sem segredos.
8. Política de envio por destino.

Compatibilidade com formato OpenAI citada no histórico é hipótese a confirmar na integração, não justificativa para fixar URLs inventadas.

## Comparação de candidatos

Mesmos cenários em português, mesmas configurações compatíveis e registro de versão/ID. Medir qualidade, consistência da identidade, latência, disponibilidade, erros e adequação ao requisito de custo.

Não há vencedor, benchmark ou catálogo vigente documentado ainda. A documentação atual registra o que foi decidido, sem reabrir seleção de provedores.

