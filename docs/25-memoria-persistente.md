# Memória persistente — Mist 0.4.0

13/10/2026. O usuário escolheu guardar automaticamente informações úteis, com opção de excluir. A implementação preserva conteúdo, fontes, datas, escopo, estado epistêmico e versões. Não importa o legado e não grava toda conversa. Modelos não escrevem no banco nem executam comandos de memória.

## Usar no terminal

```sh
PYTHONPATH=src python -m mist --memory-dir runtime/memory
```

Sem `--memory-dir`, o funcionamento anterior permanece disponível sem persistência. Ao habilitar o diretório, a captura automática fica ligada por padrão. O diretório precisa ser privado (0700), com arquivos 0600, sem links. Memória neste incremento exige Linux, SQLite >=3.42 com FTS5 e Python >=3.11. Não há criptografia do banco: permissões locais não substituem criptografia de disco.

Exemplos de declarações reconhecidas automaticamente: `Meu nome é Aurora`, `Prefiro respostas curtas`, `Meu objetivo é aprender Python`. Em um projeto selecionado, também `O prazo é sexta-feira` e `Decidimos usar uma interface simples`. Somente padrões delimitados em português, numa única linha de até mil caracteres; perguntas, citações, blocos de código e segredos reconhecidos são ignorados. Isso é um critério inicial conservador, não extração semântica universal. Informações fora desses padrões podem ser guardadas explicitamente.

```text
/memory remember Informação que quero guardar
/memory list
/memory find prazo
/memory show ID
/memory replace ID Novo conteúdo
/memory delete ID
/memory archive ID
/memory accept ID
/project aurora
/project global
```

`ID` é o identificador mostrado pela Mist, não a palavra literal. A CLI avisa quando uma declaração foi guardada ou virou candidata. A declaração pode ser persistida mesmo se a geração posterior falhar; nesse caso não existe resposta bem-sucedida no histórico transitório. `settings.json` pode incluir `memory: {automatic: false, max_items: 5, max_chars: 2500}` para desativar captura automática ou alterar o orçamento. O JSON real exige aspas nas chaves; os valores são validados.

## Fontes, estados e conflitos

- Tipos iniciais: semântica, episódica e preferência; projeto é escopo, não um banco separado.
- Origem, UUID da sessão/mensagem e horário da fonte são distintos dos horários de gravação/atualização.
- Estados: declarado, inferido e hipótese. Uma declaração atribuída ao usuário não é verificação independente; frequência de busca não promove estado.
- Sugestões de modelo ficam candidatas e não são automaticamente aceitas. Não há extração por LLM neste incremento.
- Deduplicação por conteúdo NFC, quebras de linha normalizadas e espaços externos removidos, preservando caixa e espaços internos. Tipo, estado, escopo, política e vínculos participam da identidade de deduplicação. Fontes distintas são preservadas, até o limite validado.
- Nome, objetivo, estilo e prazo de projeto têm posições lógicas para detectar conflito exato. Nova declaração incompatível fica candidata; não substitui silenciosamente a vigente. `/memory accept ID` resolve explicitamente.
- `Correção: meu nome é Luna` e `/memory replace` criam nova versão do mesmo item. A versão anterior sai da busca corrente; derivados ficam arquivados. Textos antigos permanecem no histórico de versões até exclusão explícita.
- Não há detecção infalível de contradições entre textos livres ou cálculo fictício de confiança.

## Recuperação e privacidade

FTS5 usa consulta de termos literais, palavras comuns filtradas, ordenação BM25 e desempate por ID. Projeto atual inclui suas memórias e as globais; outro projeto não entra. Candidatas, arquivadas e expiradas não são recuperadas como vigentes. Preferência de estilo vigente pode ser selecionada mesmo sem correspondência lexical; pedido explícito atual e `/style` têm precedência.

Cada item entra no contexto como **dados em mensagem de usuário**, com referência, versão, origem, horário, estado e razão de seleção. Não é mensagem privilegiada nem autorização. Limites padrão: cinco itens e 2.500 caracteres da representação completa, sujeitos também ao orçamento total da conversa. Itens inteiros são descartados se não couberem; nenhum campo de proveniência é truncado silenciosamente. A aplicação pode remover turnos antigos completos para respeitar o orçamento.

Memórias automáticas e correções ficam `local_only`. Dados e preferências locais são filtrados antes da montagem de chamadas externas; a Guarda continua conferindo o payload final. Uma resposta derivada de memória local permanece local no histórico transitório. Para liberar um item deliberadamente:

```text
/memory allow-external ID
/memory local ID
```

Permissão não é multiplicada por modelo. Derivados de item local não podem ser liberados enquanto a fonte permanecer local. Voltar a classificação para local também restringe derivados. Correção automática não herda liberação externa do texto anterior. Restauro cria itens locais, exigindo nova liberação quando necessário. A oferta/condições NVIDIA do [documento 22](22-condicoes-nvidia.md) continuam pendentes; não foram enviadas memórias pessoais a serviços externos nesta entrega.

## Exclusão, exportação e recuperação

`/memory delete ID` remove conteúdo de todas as versões, fontes, índice FTS e derivados transitivos. A CLI limpa o contexto da sessão para retirar respostas baseadas no conteúdo excluído. O registro sobrevivente conserva apenas IDs e horários de exclusão; não conserva texto ou hash do conteúdo. Arquivamento é reversível conceitualmente, mas não equivale a apagar. Neste incremento não há comando de desarquivamento automático.

```text
/memory export runtime/memory-export.json
/memory backup runtime/memory-backup.json
/memory restore runtime/memory-backup.json
```

Exportação e backup usam o mesmo snapshot JSON privado, incluindo fontes e versões dos itens sobreviventes; nunca sobrescrevem arquivo existente. São manuais, sem agenda nem retenção automática. O operador mantém ou remove as cópias conforme sua necessidade; arquivos antigos podem conter conteúdo depois excluído. Não há promessa de apagar cópias externas, snapshots do sistema, SSD ou backups históricos de imediato.

`memory.sqlite3` contém os dados e auditoria de metadados. `registry.sqlite3` mantém identidade do armazenamento, exclusões e últimas versões/status conhecidos. Conservar esse registro separado é obrigatório para restaurar. Restaurar um snapshot do mesmo armazenamento respeita exclusões e versões mais recentes, sem sobrescrever revisão vigente. Snapshot de outro armazenamento ou sem registro sobrevivente é rejeitado; nunca recriar uma identidade para contornar exclusão. A restauração é um merge validado, não uma substituição indiscriminada.

Para recuperar após corrupção do banco principal, encerrar a Mist e executar:

```sh
PYTHONPATH=src python -m mist --memory-dir runtime/memory \
  --recover-memory runtime/memory-backup.json
```

Esse modo não lê chave, não inicia conversa e não faz rede. Valida JSON, prepara banco temporário, reaplica o registro sobrevivente e só então troca o banco principal. Falha de validação preserva o banco anterior. Registro corrompido/perdido exige intervenção; não restaurar dados excluídos com base apenas no backup antigo. Para mudança de máquina, transportar o diretório privado completo preservando o registro, com a aplicação encerrada. Não importar uma exportação em um armazenamento de identidade diferente.

Snapshots são limitados a 20 MB, dez mil itens e cem mil versões; exceder os limites falha sem afirmar sucesso. Operações simultâneas de outras instâncias da Mist no mesmo diretório são recusadas. Não existe cache de memória persistente adicional. Uma aplicação com memória indisponível falha antes do provedor; iniciar sem o diretório permite conversa explicitamente sem memória.

## Integridade e evidência

Schema 1 e migração inicial transacional. Conteúdo, FTS e auditoria de metadados são atualizados na mesma transação; exclusões e versões do registro separado participam da transação SQLite em journal DELETE e synchronous FULL. A [documentação SQLite](https://www.sqlite.org/lang_attach.html) descreve a atomicidade entre bancos anexados sob essas condições. A [opção secure-delete do FTS5](https://www.sqlite.org/fts5.html#the_secure_delete_configuration_option) é usada junto de `PRAGMA secure_delete`; não garante eliminação de cópias fora do banco.

A suíte contém 132 testes: 48 novos para memória e integração, além dos 84 anteriores. Verifica persistência, fontes/dedup, hipótese, conflito, correção, escopo, validade, orçamento, credenciais, privacidade de derivados, falhas de auditoria, rollback, interrupção de processo antes do commit, migração interrompida, recuperação, restauração antiga e CLI offline. São garantias de fluxo/política, não homologação da qualidade textual de um LLM.

`tools/verify_memory.py` gera dez mil registros e cem consultas por âncoras sintéticas únicas. Gabarito determinístico, filtros locais/projeto, medição da recuperação incluindo registro SQLite. Conexão aquecida e cache do sistema não controlado; montagem do corpus excluída da latência. Relatórios finais em `validation/memory/`. Esse cenário favorável não demonstra qualidade semântica, cache frio, hardware de produção ou a proposta histórica de p95 <=300ms em uso geral.

A avaliação real dirigida foi executada no documento 26. Próximas avaliações: conversas inéditas com lembranças/correções, critérios de utilidade e ampliação da captura para textos livres, sob política de envio definida. Embeddings, importação do legado, projetos completos e execução de ferramentas continuam fora desta entrega.

## Revisão 0.4.1

A suíte atual tem 141 testes: os 132 da entrega de memória, seis para o runner
sintético (incluindo continuação fixa) e três para integridade da revisão. Os
registros 0.4.0 permanecem históricos. O armazenamento e sua política não mudaram.
O perfil esclarece origens user/application/model e a citação de declarações.
Avaliação externa com dados fictícios em [documento 26](26-avaliacao-real-memoria.md);
nenhuma memória pessoal foi enviada. A sondagem lexical anterior continua
vinculada ao armazenamento inalterado, sem atribuir seu desempenho ao novo perfil.

## Ligação com projetos 0.5.0

O catálogo opcional é criado ao iniciar com `--memory-dir`, conforme documento
27. A memória mantém schema 1 e seu registro de exclusões. `/projects use ID`
seleciona cadastro ativo e aplica o mesmo ID como escopo de memória; o seletor
anterior de escopo livre continua disponível. Snapshots/restauração de memória
não incluem nem substituem o catálogo de projetos/tarefas.
