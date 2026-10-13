# Integração inicial com a NVIDIA

Estado em 12 de outubro de 2026: adaptador implementado e testado com uma chave temporária fornecida pelo usuário. A chave foi recebida por entrada oculta nos processos de teste, mantida em memória e usada apenas no cabeçalho de autenticação da NVIDIA. Não foi incluída em arquivos, configuração, Git, auditoria ou pacote de entrega.

O padrão do programa continua sendo FakeModel offline. Este incremento permite geração real com habilitação explícita. O [benchmark posterior](18-benchmark-modelos.md) selecionou provisoriamente FAST/PRIMARY e atualizou o exemplo NVIDIA. O P0-A segue em validação: rodadas reais e correções estão no documento 23; faltam verificação das condições da conta e critérios restantes; não há memória persistente.

## Resultado observado

| Verificação real | Resultado |
|---|---|
| Consulta ao catálogo `/v1/models` | HTTP 200. A consulta sozinha não garante que todos os modelos listados aceitem geração. |
| `meta/llama-3.1-8b-instruct` | HTTP 410; não usado na configuração entregue. |
| `mistralai/mistral-7b-instruct-v0.3` | HTTP 404, apesar de aparecer no catálogo; não usado. |
| Nemotron Lightning com raciocínio ativo e limite de 128 tokens | HTTP 200, mas sem texto final: o orçamento foi gasto em raciocínio. |
| `nvidia/nemotron-3.5-lightning-30b-a3b`, raciocínio desativado | HTTP 200 e texto final: “Teste da Mist concluído.” |
| Geração pelo Core/CLI da Mist | Resposta real, `simulated: false`, com aprovação e conclusão na auditoria. |
| Apresentação após ajuste da identidade | “Sou a Mist, sua assistente.” |
| Pergunta seguinte sobre o modelo | Respondeu a família Nemotron, sem reproduzir o ID exato. Precisão de metadados ainda requer avaliação. |
| Entrada `local_only` no fluxo real | `GUARD_BLOCKED`, sem alteração do histórico e sem chamada ao adaptador. |

No teste final, os dois turnos reais levaram aproximadamente 542 ms e 757 ms no Gateway. São observações pontuais, não benchmark nem garantia de latência. Os testes usaram perguntas sintéticas; histórico dos chats do projeto e materiais privados não foram enviados.

No teste inicial, o exemplo usou Lightning nos dois papéis para validar transporte. Após o benchmark, a configuração usa Super com raciocínio ativado para FAST e Kimi K3 para PRIMARY. A escolha e os limites estão no [documento 18](18-benchmark-modelos.md).

## Executar

Depois de instalar a aplicação, ou com Pydantic disponível no ambiente, execute na raiz do repositório:

```sh
PYTHONPATH=src python -m mist --config-dir examples/nvidia --allow-external --ask-api-key
```

O programa solicita a chave com entrada oculta e não a salva. Se não houver terminal capaz de ocultar a entrada, recusa a leitura. Alternativamente, o processo pode receber `NVIDIA_API_KEY` pelo ambiente; não existe carregamento automático de `.env`.

Para uma interação curta:

```sh
PYTHONPATH=src python -m mist --config-dir examples/nvidia --allow-external --ask-api-key --message "Olá, Mist"
```

Com o pacote instalado, use `mist` no lugar de `PYTHONPATH=src python -m mist`. `examples/nvidia` é um diretório do repositório, não um recurso embutido no pacote instalado; indique seu caminho completo se executar de outro diretório.

`--allow-external` autoriza o envio do contexto permitido da sessão ao serviço configurado. Uma configuração NVIDIA sem essa opção falha antes da geração. Para informações que devem ficar no computador, use `/local TEXTO`; o modo NVIDIA bloqueia essas interações. Não copie credenciais para o campo de conversa.

Revogar a chave de teste é uma ação do usuário no painel NVIDIA. Nenhuma chave persistente foi criada pela Mist.

## Configuração e fronteira de envio

O exemplo contém os três documentos JSON: `settings.json`, `constitution.json` e `personality.json`. As regras de autonomia zero e de ferramentas desabilitadas continuam obrigatórias.

O adaptador aceita somente:

- provedor lógico `nvidia`;
- `external: true`;
- destino lógico `nvidia-integrate`, mapeado no código para `https://integrate.api.nvidia.com/v1/chat/completions`;
- destino presente na lista permitida da Guarda;
- habilitação explícita na inicialização e credencial válida no formato esperado.

O host e o caminho são fixos. Não há URL arbitrária configurável, redirecionamento, proxy de ambiente, fallback ou tentativa automática. A conexão HTTPS verifica certificado e nome do host. A chave vai apenas no cabeçalho `Authorization: Bearer`; o corpo contém modelo, mensagens, limite de saída, temperatura, streaming desativado e a opção de raciocínio quando configurada. Sensibilidade, identificadores de auditoria e autorização interna não são enviados como campos da conversa.

A Guarda verifica o envelope final, incluindo histórico, instruções e metadados do modelo. `local_only`, destino proibido e padrões reconhecidos de credenciais bloqueiam o envio. A detecção por padrões continua limitada: não garante identificar todo dado sensível. A aplicação confia no código Python do próprio processo; o adaptador não é uma sandbox para extensões.

## Limites e erros

`provider_timeout_seconds` é 120 segundos no exemplo selecionado pelo benchmark (era 45 na integração inicial). É usado como timeout das operações de conexão/leitura; há também um prazo decrescente durante a leitura do corpo. Não é garantia rígida de tempo total para DNS, conexão e cabeçalhos. A interação é síncrona; Ctrl+C fecha a conexão, registra cancelamento quando a auditoria está disponível e não incorpora o turno ao histórico. Cancelamento local não garante que o serviço remoto interrompa uma geração já recebida.

`max_output_tokens` é 4.096 no exemplo atual e pode variar de 1 a 4.096. O benchmark e as rodadas de identidade v1/v2/v3 usaram 2.048; v3 registrou um esgotamento desse teto no PRIMARY, sem resposta visível. A revisão v4 testa o aumento, sem retries automáticos. Super usa `enable_thinking: true`, e Kimi omite o parâmetro, conforme os perfis testados. Lightning com `false` foi verificado na integração inicial. Outros modelos precisam de validação própria. O corpo recebido é limitado a 1 MB; o texto final, a 32.000 caracteres.

| Situação | Resultado exibido |
|---|---|
| Chave ausente/formato inválido ou HTTP 401/403 | `PROVIDER_AUTH` |
| HTTP 429 | `RATE_LIMIT` |
| HTTP 404/410/502/503/504 | `PROVIDER_UNAVAILABLE` |
| Timeout | `PROVIDER_TIMEOUT` |
| Falha de conexão ou outros status, inclusive 202/redirect | `PROVIDER_FAILURE` |
| JSON inválido, corpo excessivo, texto vazio, saída truncada ou chamada de ferramenta | `INVALID_RESPONSE` |

Respostas pendentes HTTP 202 não são consultadas novamente nesta versão. Erros não exibem corpo HTTP, cabeçalhos ou detalhes da exceção. Texto que reproduza a própria chave é recusado. Chamadas de ferramentas e funções retornadas pela API também são recusadas; texto sugerindo ações não ganha autorização para executá-las.

A auditoria continua gravando apenas metadados. Falhas antes do envio impedem a chamada; falhas depois impedem entrega e atualização do histórico. Timeout/limite do serviço não mudam automaticamente modelo, destino ou sensibilidade.

## Verificação

**47 testes automatizados passaram** em Linux/Python 3.14.7/Pydantic 2.13.5: 29 do núcleo offline, 15 do adaptador/integração/uso e três da infraestrutura de benchmark. A suíte não utiliza a chave real nem rede; usa uma chave sintética e transporte controlado para verificar TLS/destino, corpo, erros HTTP, ausência de retries/redirects, timeouts, fechamento, conteúdo inválido, ferramentas, bloqueios, opt-in, auditoria, histórico e leitura oculta. O benchmark real não integra a suíte automática.

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
```

Além dessa suíte, os testes reais acima foram executados manualmente e a entrada instalada foi verificada com transporte simulado. A configuração offline continua executável sem chave e sem acesso à rede. Os testes reais não fazem parte de uma execução automática para evitar envio ou consumo de cota involuntários.

## Referências e próximas verificações

O endpoint e o formato de Chat Completions seguem a [referência oficial NVIDIA](https://docs.api.nvidia.com/nim/reference/llm-apis). A opção de raciocínio foi consultada na [documentação do Nemotron Lightning](https://docs.nvidia.com/nim/large-language-models/2.0.10/get-started/advanced/get-started-nemotron-3.5-lightning.html). O catálogo e a documentação mostraram divergências de disponibilidade; uma resposta real é necessária para verificar cada modelo.

Antes de considerar P0-A concluído: ampliar a avaliação de identidade com tarefas inéditas, validar cotas/termos/política de dados da conta e completar os casos aplicáveis do documento 12. A escolha provisória já tem critérios e experimento explícitos no documento 18; não estabelece gratuidade ilimitada ou qualidade geral.
