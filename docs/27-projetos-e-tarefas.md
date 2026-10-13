# Projetos e tarefas locais — Mist 0.5.0

Em 13/10/2026, o usuário escolheu organizar projetos e tarefas como o primeiro
recurso de P1. A implementação oferece cadastro com nome/objetivo, tarefas,
status, prioridade, prazo, progresso, arquivamento e retomada pela CLI.
Atualizações são comandos explícitos do usuário, com fonte, data e revisão.
Marcar uma tarefa como concluída registra essa declaração; não comprova que
a Mist executou ou verificou o trabalho.

## Começar

```sh
PYTHONPATH=src python -m mist --memory-dir runtime/memory
```

Exemplo fictício, digitado na sessão:

```text
/projects create aurora "Projeto Aurora" "Preparar uma apresentação"
/projects use aurora
/projects add aurora Revisar o roteiro
/projects add aurora Preparar os exemplos
/projects tasks
/projects progress
```

`create` não muda o projeto atual. `use` seleciona o cadastro ativo, limpa o
contexto transitório e usa seu identificador como escopo das memórias. Uma
declaração reconhecida, como `O prazo é sexta-feira`, será capturada no escopo
selecionado pela política de memória existente. Memórias globais continuam
disponíveis conforme os filtros do documento 25.

O ID de cadastro é estável e distingue projetos; o nome pode mudar. Identificadores
aceitam letras ASCII, números, ponto, hífen e sublinhado, até 80 caracteres;
`global`, `.` e `..` são reservados. Nome até 200 caracteres, objetivo até 2.000.
Use aspas para nomes/objetivos com espaços no cadastro. O comando anterior
`/project NOME` continua selecionando um escopo livre, inclusive sem cadastro;
`/projects use ID` valida o cadastro e seu estado. `/project global` sai do escopo.

## Atualizar e acompanhar

`/projects tasks` mostra o UUID completo de cada tarefa. Substitua `UUID` pelo
identificador exibido; cada operação também informa o projeto, impedindo usar
a tarefa de outro projeto por engano.

```text
/projects task aurora UUID andamento
/projects priority aurora UUID alta
/projects due aurora UUID 2026-10-20
/projects edit-task aurora UUID Revisar roteiro e exemplos
/projects task aurora UUID concluida
/projects progress aurora
/projects rename aurora Aurora revisada
/projects objective aurora Preparar a versão final da apresentação
```

Estados: `pendente`, `andamento`, `bloqueada`, `concluida`/`concluída` e
`cancelada`. Prioridades: `baixa`, `normal` e `alta`. O prazo usa uma data válida
AAAA-MM-DD; `due ... none` remove o prazo. Não há agendamento, notificação ou
inferência de datas relativas. A prioridade não reordena a lista: tarefas ficam
na ordem de criação, para preservar uma leitura estável.

O percentual é concluídas dividido pelas tarefas não canceladas. Exemplo:
uma concluída, uma bloqueada e uma cancelada resulta em 50%. Se não houver
tarefa elegível, a Mist informa ausência de percentual. Não interpreta ausência
de tarefas como trabalho concluído. O status pode ser corrigido explicitamente.

## Arquivar, retomar e excluir uma tarefa

```text
/projects archive aurora
/projects list
/projects show aurora
/projects reopen aurora
/projects use aurora
/projects delete-task aurora UUID
```

Arquivamento preserva tarefas e memórias, permite consulta e bloqueia seleção
via `use` e atualizações de tarefas até a reabertura. Se for o projeto atual,
a sessão volta ao escopo global e limpa o contexto. Não equivale a excluir
memórias, e o seletor antigo de escopo livre continua disponível. O cadastro
não possui exclusão permanente neste incremento.

`delete-task` remove o registro e seu texto do catálogo atual. Cancelamento
apenas muda o status, mantendo o conteúdo. Memórias que mencionam uma tarefa
são registros independentes e têm os próprios comandos de correção/exclusão;
não criar uma relação de derivação que ainda não existe. Exportações/cópias
anteriores podem conservar conteúdo excluído.

## Privacidade e armazenamento

Cadastros e tarefas são `local_only`, sem operação de liberação externa neste
incremento. Seus nomes, objetivos e títulos não são montados automaticamente
nos envelopes dos modelos. A conversa continua usando apenas a memória
recuperada conforme sua política. As operações `/projects` são atendidas
localmente, sem chamar LLM, enviar dados, executar tarefas ou interpretar uma
resposta do modelo como comando. A Guarda e a autonomia zero permanecem.

`projects.sqlite3`, schema 1, fica no diretório privado da memória. O catálogo
é anexado à conexão que já mantém o lock exclusivo; fecha com essa sessão.
Identidade do armazenamento deve coincidir com o registro sobrevivente de
memória. O schema de memória continua 1; um armazenamento 0.4.x existente pode
receber o catálogo novo sem importar dados antigos como projetos.

Alterações de registros e auditoria de metadados participam da mesma transação;
journal DELETE, synchronous FULL, secure_delete e chaves estrangeiras. Auditoria
conserva IDs, horários, operação e revisão, sem nome, objetivo ou título. Falha
de auditoria/commit reverte a alteração. Inicialização cancelada libera o lock.
Arquivo inseguro, schema desconhecido, catálogo de outra identidade ou corrupção
impedem inicialização com esse diretório; não realizar envio para contornar isso.
Permissões 0700/0600 e controle de arquivos regulares não são criptografia.

Limites locais: mil cadastros, mil tarefas por projeto e dez mil tarefas totais;
títulos até 500 caracteres. Entradas com controles ou padrões reconhecidos de
credenciais são recusadas. O detector não garante identificar todo segredo.
CLI/Core seguem síncronos, uma instância por diretório.

## Exportação e cópias

```text
/projects export runtime/projects-export.json
```

Cria um arquivo JSON novo, privado, até 20 MB, com **todos** os projetos,
tarefas e fontes, inclusive projetos arquivados. Não sobrescreve arquivo
existente, não inclui memórias e não fornece importação/restauração automática.
Falha detectada durante a gravação/commit limpa o arquivo novo quando ele ainda
é o criado pela operação. Encerramento abrupto do processo ou falha física
durante exportação pode deixar arquivo parcial, que não deve ser usado como
cópia completa. Não há limpeza automática de cópias externas ou antigas.

`/memory backup`, `/memory restore` e `--recover-memory` operam somente sobre
memória. Restauração de memória não reduz versões do catálogo nem ressuscita
tarefa excluída. Recuperação de catálogo corrompido e importação de JSON não
estão implementadas. Para uma cópia do armazenamento completo, encerrar a Mist
e copiar o diretório privado inteiro, preservando `memory.sqlite3`,
`registry.sqlite3` e `projects.sqlite3`. Uma cópia antiga do catálogo pode conter
tarefas depois excluídas; não prometer a mesma proteção de tombstones da memória.

## Validação e próximos incrementos

166 testes na fonte: os 141 anteriores e 25 novos para projetos, CLI e falhas.
Persistência entre sessões, fontes/revisões, isolamento por projeto, progresso,
arquivamento, validação de datas/segredos, limites, auditoria/commit, exclusão,
arquivos privados, schema/namespace e cancelamento cobertos. Spy de provedor
confirma ausência de conteúdo do catálogo no envelope externo; saída do modelo
com texto de comando não altera cadastro. Resultados locais de instalação
constam no [documento 21](21-instalacao-validada.md), em Python 3.11.16 e
3.14.7. Um [fluxo fictício](../validation/projects/README.md) em quatro processos
isolados por versão também confirmou persistência/arquivamento e 50% de
progresso após marcar uma de duas tarefas como concluída.

Não foi utilizada chave nem realizada chamada NVIDIA nesta entrega. A avaliação
textual 0.4.1 do documento 26 permanece histórica; não avalia gestão automática
de projetos. Relações, consolidação automática de episódios, planejamento por
conversa, interface visual, execução de ferramentas e verificação real de tarefas
são incrementos posteriores, com escopo e política próprios.
