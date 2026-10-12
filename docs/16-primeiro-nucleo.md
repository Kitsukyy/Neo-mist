# Primeiro núcleo offline da Mist

Registro do primeiro incremento offline em 12 de outubro de 2026. A evolução com API real está no [guia NVIDIA](17-integracao-nvidia.md); limites descritos aqui referem-se à configuração offline e ao estado anterior à integração. Este incremento inicia o P0-A; o marco completo exige pelo menos um provedor real validado. FakeModel é uma simulação determinística, não um modelo de linguagem.

## O que funciona

O Core coordena entrada → identidade → roteador → Gateway → Guarda → auditoria de aprovação → FakeModel → validação → auditoria de conclusão → resposta. Histórico só muda depois de uma interação bem-sucedida. Não há execução de ferramentas, memória persistente ou clientes de rede.

- Constituição mínima validada, com regras obrigatórias que não podem ser desligadas por configuração.
- Perfil inicial Mist com temperamento e comunicação contextuais, relacionamento colaborativo e iniciativa conversacional. Esta versão só aplica uma instrução estável e uma escolha simples de comunicação; adaptação emocional, aprendizado e inferências de preferências não estão implementados.
- Modos `AUTO`, `FAST` e `PRIMARY`, com seleção manual e regras determinísticas provisórias.
- Contexto transitório com orçamento em caracteres e descarte de turnos completos.
- Guarda com autorizações de uso único, vinculadas ao pedido completo e ao destino.
- Auditoria JSONL com metadados, sem prompts, respostas ou credenciais.
- Autonomia zero e autorização de ferramentas sempre negada.

## Instalação e execução

Python declarado: **3.11 ou superior**. Ambiente efetivamente verificado: **Linux, Python 3.14.7, Pydantic 2.13.5**. Compatibilidade com outras versões de Python ainda precisa de uma matriz de testes.

Na raiz do repositório:

```sh
python -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/mist
```

A instalação pode baixar dependências. O programa instalado e os testes offline não precisam de API, chave ou rede. O pacote se chama `neo-mist`, e a entrada de terminal se chama `mist`; nenhum pacote foi publicado no PyPI.

Para desenvolvimento, com Pydantic disponível no ambiente:

```sh
PYTHONPATH=src python -m mist
PYTHONPATH=src python -m mist --message "Olá, Mist"
PYTHONPATH=src python -m unittest discover -s tests -v
```

Exemplo de resposta: `[Simulação — FakeModel] Fluxo validado. Não interpretei a pergunta nem executei ações.` O texto confirma apenas o percurso da simulação; não é uma resposta inteligente à pergunta.

## Comandos de sessão

| Comando | Comportamento |
|---|---|
| `/help` | Mostra os comandos e o limite do FakeModel. |
| `/mode AUTO`, `/mode FAST`, `/mode PRIMARY` | Troca o modo de seleção do modelo. |
| `/style auto`, `/style concise`, `/style detailed` | Define a comunicação da sessão. |
| `/local TEXTO` | Classifica a entrada como `local_only`. |
| `/status` | Mostra modo, estilo, autonomia e turnos retidos. |
| `/reset` | Descarta histórico e preferências desta sessão. |
| `/quit` | Encerra o programa. |
| `/tool NOME` | Retorna uma recusa de autorização; não há executor. |

`--message` executa uma interação e sai. Falhas nessa modalidade retornam código 2. Para dados privados, prefira a entrada interativa: argumentos de terminal podem aparecer na lista de processos ou no histórico do shell.

No modo `AUTO`, entradas com mais de 600 caracteres ou contendo `planeje`, `arquitetura`, `analise`, `compare` ou `passo a passo` usam `fake-primary`; as demais usam `fake-fast`. Ambos executam o mesmo FakeModel. Essas regras não são um benchmark ou uma classificação confiável de complexidade.

No estilo automático, `explique`, `passo a passo` ou `detalhe` ativam a instrução de comunicação detalhada. A seleção explícita de estilo prevalece. Nada é aprendido ou preservado entre sessões.

## Configuração efetiva

Os três arquivos padrão ficam em `src/mist/defaults/` e acompanham o pacote instalado:

- `settings.json`: versão, autonomia, modelos, modo, orçamento e destinos.
- `constitution.json`: sete regras obrigatórias habilitadas.
- `personality.json`: identidade e quatro dimensões iniciais.

JSON é a escolha inicial para eliminar a dependência de um parser adicional. Os exemplos YAML do documento 11 continuam sendo propostas para a evolução; esta versão não lê YAML nem `.env`.

Para personalizar, copie os três arquivos para um diretório próprio e use:

```sh
PYTHONPATH=src python -m mist --config-dir /caminho/da/configuracao
```

Campos inesperados, modelos duplicados, referências inexistentes e configurações incompatíveis são recusados. O carregamento só aceita provedor `fake`, destino `offline`, `external: false`, lista vazia de destinos externos, `autonomy_level: 0` e `tools_enabled: false`. O nome Mist e os valores das dimensões são fixos nesta versão; somente as opções admitidas pelo schema podem variar.

O orçamento padrão é de 8.000 caracteres por entrada e 16.000 para o contexto enviado. A instrução de sistema conta nesse orçamento. Histórico antigo é removido em pares usuário/resposta. Uma resposta muito longa também pode levar ao descarte de turnos do histórico após a entrega. O orçamento não representa tokens e precisará ser adaptado para modelos reais.

## Segurança e auditoria

`OutputGuard` avalia o envelope final e emite um identificador interno de uso único, vinculado por hash ao pedido, mensagens, modelo e destino. Alterações após aprovação, repetição e identificadores falsos impedem o envio. Texto produzido pelo modelo não emite autorizações. Essa fronteira protege o fluxo da aplicação; código Python executado no mesmo processo é parte da base confiável, não um ambiente isolado para extensões.

Os testes usam um adaptador externo de teste que nunca acessa rede para verificar destino permitido, bloqueio de contexto `local_only` e reconhecimento de alguns padrões de credenciais. O detector por padrões é limitado e não garante detectar qualquer segredo. Antes da integração real serão necessárias políticas de destino e classificação mais completas. Mudar um arquivo JSON não habilita envio externo.

Uma resposta derivada de contexto `local_only` mantém essa classificação; interações posteriores permanecem protegidas enquanto esse contexto ou suas respostas derivadas estiverem retidos. O FakeModel processa essas entradas somente no próprio processo.

A auditoria padrão fica em `$XDG_STATE_HOME/neo-mist/audit.jsonl`, ou em `~/.local/state/neo-mist/audit.jsonl` quando a variável não existe. É possível indicar outro local:

```sh
PYTHONPATH=src python -m mist --audit-path /tmp/mist-audit.jsonl --message "Teste offline"
```

Cada evento contém horário UTC, identificador do pedido, provedor, modelo, fase, motivo e duração quando disponível. O arquivo é criado com permissão `0600`; arquivos existentes com permissões para grupo/outros, links simbólicos no arquivo final e destinos que não sejam arquivos regulares são recusados em Linux. Retenção, rotação, reparo de escrita parcial e recuperação entre execuções ainda não estão implementados.

O Gateway grava e sincroniza a aprovação antes de chamar o provedor. Se a auditoria falhar, suspende novas gerações naquela instância. Falha na auditoria de conclusão impede a entrega e a atualização do histórico, mesmo que o provedor já tenha sido chamado. `/reset` não remove a suspensão; é preciso resolver a causa e iniciar outra sessão. Erros exibidos não reproduzem o conteúdo de exceções de configuração ou provedor.

## Validação desta entrega

**29 testes passaram** usando `unittest` em Python 3.14.7. A suíte verifica:

- ordem guarda/aprovação/envio/conclusão e identidade do pedido;
- destinos proibidos, `local_only` e padrões sintéticos de credenciais;
- aprovação falsa, repetida e invalidada por alteração;
- falhas da guarda, da auditoria antes/depois do envio e do provedor;
- respostas inválidas, ausência de tentativas automáticas e erros sem conteúdo sensível;
- identidade, seleção de estilo/modelo, orçamento de contexto e descarte de turnos completos;
- propagação de sensibilidade, reset, entradas inválidas e autonomia zero;
- configuração segura, imutabilidade e proteção do arquivo de auditoria;
- execução da CLI com criação de sockets bloqueada e sem conteúdo conversacional no log.

Também foram verificados o empacotamento, a inclusão dos três JSON padrão e a execução da entrada `mist` após instalação local. Os testes não validam qualidade conversacional, um modelo local ou envio a APIs reais.

## Próximo incremento

Confirmar a configuração de um provedor real, verificar a documentação oficial do serviço e implementar seu adaptador com credenciais fora dos arquivos de configuração. Antes de habilitar chamadas: definir destino exato, sensibilidade, timeout, erros, cancelamento, limites e política de envio. Então executar os critérios restantes do P0-A. Memória persistente continua reservada ao P0-B.
