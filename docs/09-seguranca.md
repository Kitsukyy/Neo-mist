# Segurança, privacidade e autorização

## Fronteiras de confiança

Aplicação/configuração controlam políticas. Modelo gera conteúdo, sem autoridade técnica. Mensagens, memória, páginas, arquivos e respostas podem conter instruções maliciosas ou informações sensíveis.

A Guarda protege o **envio de dados**. O Authorizer controla **execução de ações**. São responsabilidades diferentes.

## Guarda obrigatória

A avaliação combina classificação/origem dos dados, política por destino e detecção de possíveis segredos. Um detector não garante encontrar todo dado sensível.

Aprovação identifica payload final, destino e política aplicada. Mudança de conteúdo ou endpoint exige nova avaliação. Todos os caminhos externos, incluindo futuros embeddings e ferramentas, seguem a mesma fronteira.

Falha de avaliação bloqueia. Nenhum modo manual ou fallback ignora a Guarda.

## Política por destino

Taxonomia final está pendente. Como detalhamento proposto:

| Classe | Política proposta |
|---|---|
| Permitido externamente | Somente para destinos configurados e parâmetros autorizados. |
| Sensível | Exige política explícita; bloquear quando não for possível avaliar. |
| Exclusivamente local | Não transmitir a APIs, embeddings ou ferramentas remotas. |
| Credencial operacional | Usar apenas na autenticação apropriada; nunca como contexto. |

Armazenamento local não implica permissão de envio. Política de “API permitida” não habilita acesso externo a todo arquivo da máquina.

Sanitização, se existir, produz novo payload e nova avaliação. Não alterar silenciosamente o sentido de uma solicitação para permitir seu envio.

## Autonomia zero

P0-A não tem executor de ferramentas. O autorizador nega todas as propostas de ações estruturadas. Texto do usuário/modelo não muda esse estado.

Chamadas de geração realizadas pelo fluxo autorizado são o escopo permitido. Nenhuma resposta pode habilitar shell, editar arquivos, iniciar tarefas em segundo plano ou mudar permissões.

Futuros níveis de autonomia dependem de contratos por ferramenta, risco, tarefa, efeitos, limites, cancelamento e registro. A visão prevê níveis 0–3; semântica exata dos níveis ampliados permanece para especificação futura.

## Prompt injection

Separar origem e instruções reduz confusão, mas não garante resistência universal do modelo. A garantia técnica é impedir que texto altere políticas ou execute ações não autorizadas.

Não concatenar páginas como se fossem instruções confiáveis. Conteúdo recuperado é citado/identificado conforme origem. No núcleo inicial, a ausência de ferramentas reduz a superfície de execução.

## Auditoria

Registrar ID operacional, horário, fase, destino/modelo, decisão, código de motivo, duração, status e metadados de uso quando disponíveis. Não registrar prompt/resposta integral, chave, header de autenticação ou conteúdo de memória por padrão.

Auditoria obrigatória antes da transmissão precisa ser persistida com sucesso. Se falhar, não chamar adaptador. Após transmissão, uma falha de registro de resultado é comunicada e bloqueia novos envios até recuperação; o evento passado não pode ser desfeito.

Logs técnicos opcionais não substituem a auditoria. Append-only é a direção para eventos críticos; mecanismo, retenção e garantias contra alteração ficam pendentes. Não chamar um arquivo local de “à prova de adulteração” sem evidência.

## Credenciais

Sem defaults sensíveis, sem valores reais em documentação, sem segredos versionados. Ausência de chave gera erro sem eco. Referência de variável pode ser pública; valor não.

Ambiente, arquivo local excluído do Git ou cofre do sistema estão em avaliação. Não foi decidido um cofre específico nem criptografia em repouso.

O usuário informou que as chaves antigas expiraram. Não reutilizar o legado para preencher configurações.

## Memória e exclusão

Conteúdo local-only é filtrado no contexto e bloqueado novamente no caminho de envio. Índices, resumos, caches e backups são parte do desenho de privacidade.

Definir retenção e reconciliação de exclusões antes de declarar P0-B concluído. Auditoria de uma exclusão usa metadados mínimos, não copia o dado excluído.

## Verificação

Testar spy de adaptadores: zero chamadas em bloqueio, falha da Guarda, falha prévia de auditoria e tentativa de alteração de destino/payload.

Testar fallbacks, injeções, logs e autorização fora do modelo. Testes de estilo não substituem testes de segurança. Veja [validação](12-validacao.md).

