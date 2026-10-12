# Contratos entre módulos

**Estado:** especificação técnica proposta. Os nomes principais vieram da Fase 4.3; campos, estados e assinaturas abaixo organizam a implementação, não representam código já existente.

Pydantic é a biblioteca proposta. Versão, configuração de validação e API Python definitivas serão fechadas na implementação. Rejeitar campos inesperados nas fronteiras críticas e validar tipos/limites.

## ConversationMessage

| Campo | Regra proposta |
|---|---|
| role | Papel reconhecido; entrada da CLI só cria mensagem de usuário. |
| content | Texto dentro do limite configurado. |
| message_id | Identificador da aplicação, não livremente escolhido pelo modelo. |
| source | Origem e referências quando houver conteúdo recuperado. |
| sensitivity | Classificação preservada durante montagem. |
| created_at | Momento da mensagem. |

Papéis privilegiados não são aceitos apenas porque o usuário enviou JSON com role=system. A aplicação constrói mensagens de instrução a partir da identidade validada.

## GenerationRequest

| Campo | Regra proposta |
|---|---|
| request_id | Identificador de correlação. |
| messages | Sequência validada, com orçamento de contexto. |
| mode | AUTO, FAST ou PRIMARY, se essa estratégia for adotada. |
| parameters | Lista permitida e limites compatíveis com o modelo. |
| context_metadata | Referências/origem necessárias para políticas, sem credenciais. |

O request lógico pode ser resolvido para um destino pelo roteador. O **envelope de envio** posterior fixa provedor, modelo, endpoint, parâmetros e payload exatos. Aprovação de saída vale sobre esse envelope final, não apenas sobre a mensagem original.

## GenerationResponse

| Campo | Regra proposta |
|---|---|
| request_id | Correlação com requisição. |
| status | Resultado reconhecido: sucesso, erro ou cancelamento quando suportado. |
| text | Texto normalizado; não afirmar sucesso com resposta inválida. |
| provider/model | Valores realmente utilizados. |
| duration | Medição da aplicação. |
| usage | Tokens/uso quando fornecidos; ausente não equivale a zero. |
| error | Código normalizado e mensagem segura quando houver falha. |

Resposta não contém instruções executáveis nem permissões. Metadados específicos podem ser acrescentados por contrato versionado, sem acoplar o Core ao formato do provedor.

## ProviderConfig e ModelConfig

ProviderConfig: identificador, destino/endpoint autorizado, referência ao segredo operacional, limites de chamada, política de envio e capacidades verificadas de integração.

ModelConfig: ID interno, ID exato do provedor, papel rápido/principal quando aplicável, capacidades, orçamento de contexto e parâmetros permitidos.

Referência ao segredo é o nome do mecanismo configurado, nunca o valor. Capacidade não verificada é distinta de false. Modelo/provedor inválido bloqueia a configuração afetada antes de enviar.

## RouterDecision

Proposta adicional para tornar roteamento testável: modo solicitado, modelo/provedor resolvidos, motivo por regra e indicação de seleção manual ou automática.

Não registrar o prompt completo como justificativa. Decisão manual ainda obedece capacidades e política de envio.

## GuardDecision

| Campo | Regra proposta |
|---|---|
| outcome | Permitido ou bloqueado; erro de avaliação resulta em bloqueio. |
| request_id | Correlação. |
| destination | Destino/modelo avaliados. |
| payload_binding | Referência interna ou impressão digital do envelope exato. |
| policy_version | Política aplicada. |
| reason_code | Motivo sem copiar segredos. |
| approval_handle | Identificador interno de aprovação quando permitido. |

A aplicação deve impedir criação de aprovação a partir de JSON gerado pelo modelo. Hash sozinho não prova autorização: é preciso conferir emissão, validade e vínculo no caminho de envio.

Mecanismo de expiração, uso único e armazenamento do handle são propostas a fechar. Uma assinatura criptográfica não é obrigatória num monólito apenas para aparentar segurança.

Se a política permitir sanitização, gerar envelope novo e obter decisão válida para ele.

## AuditEvent

Proposta: event_id, request_id, timestamp, phase, provider, model, outcome, reason_code, policy_version, duration e usage permitido.

Não copiar objetos de request/response automaticamente para log. Não incluir chave, conteúdo de memória, header de autenticação ou prompt por padrão. A persistência do evento obrigatório antecede envio.

## MemoryItem e RetrievalResult — P0-B

MemoryItem: ID, tipo, conteúdo/resumo, source_timestamp, provenance_link, origem, estado epistêmico, escopo, sensibilidade, ciclo de vida, versão, vínculos e datas operacionais. Confiança opcional quando justificável.

RetrievalResult: itens e versões selecionados, referências, razão/pontuação, filtros aplicados e orçamento usado. Exclusões/substituições e local-only são respeitados.

Os campos conceituais não fixam o schema SQLite. Provenance_link pode ser uma referência interna, não necessariamente uma URL pública.

## Interfaces propostas

| Interface | Entrada | Saída |
|---|---|---|
| Core.handle | Entrada validada e estado de sessão | Resultado para UI |
| Identity.resolve | Contexto, correções e preferências | Diretrizes comportamentais |
| Router.select | Modo, tarefa e configuração | RouterDecision |
| Guard.evaluate | Envelope final e política | GuardDecision |
| Audit.record_required | Metadados permitidos | Sucesso de persistência ou falha |
| Gateway.generate | Envelope e aprovação válida | GenerationResponse |
| Provider.generate | Payload aprovado e parâmetros resolvidos | Resposta específica normalizada |
| Memory.retrieve | Consulta, escopo e orçamento | RetrievalResult |
| Memory.apply_change | Candidato/correção validado | Resultado versionado |

Essas assinaturas são conceituais; síncrono/assíncrono, tipos finais e streaming estão pendentes. O único caminho de rede de geração deve atravessar verificações obrigatórias.

## Taxonomia de erros proposta

CONFIGURATION_ERROR, INVALID_INPUT, UNKNOWN_MODEL, UNSUPPORTED_CAPABILITY, AUTHENTICATION_ERROR, RATE_LIMIT, TIMEOUT, CONNECTION_ERROR, INVALID_RESPONSE, GUARD_BLOCKED, GUARD_FAILURE, AUDIT_FAILURE, AUTHORIZATION_DENIED e MEMORY_UNAVAILABLE.

Código é estável para testes; mensagem pública é segura. Erros não incluem dump de ambiente ou headers. Classificação exata de exceções HTTP fica no adaptador.

## Validação e evolução

Versionar contratos que mudem comportamento entre módulos. Testar substituição de provedor e limites de importação. Exemplos devem ser sintéticos; Pydantic valida estrutura, não a veracidade de conteúdo nem a autorização de transmissão.

