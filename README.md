# Neo-mist — Mist

A Mist é uma assistente pessoal de IA com identidade própria, personalidade adaptativa e arquitetura modular. A aplicação será executada localmente, usando provedores externos para geração de respostas e permitindo, futuramente, modelos locais, memória persistente, ferramentas, voz e autonomia configurável.

**Estado:** primeiro núcleo offline do P0-A implementado, com CLI, FakeModel, identidade, roteamento, Guarda de Saída e auditoria. O adaptador NVIDIA tem geração real verificada. O benchmark selecionou provisoriamente Nemotron Super com raciocínio para FAST e Kimi K3 para PRIMARY; a aceitação completa do P0-A continua pendente. As duas rodadas reais de identidade tiveram revisão registrada e correções de comportamento; o perfil 0.3.0 acrescenta uma regressão direcionada de idioma. A suíte de 75 testes passou também usando o pacote instalado em Linux/Python 3.11.16 e 3.14.7. Consulte [resultados e limites](docs/23-avaliacao-real-identidade.md). O FakeModel produz respostas de teste e não interpreta perguntas.

**Base documental:** decisões dos chats do projeto Mist, consolidadas em 11 de outubro de 2026. Decisões, propostas e pendências estão identificadas para evitar que uma hipótese seja confundida com uma funcionalidade pronta.

## O que já está definido

- Reconstrução modular, sem obrigatoriedade de preservar a arquitetura antiga.
- Execução inicial em um computador Linux, com interface simples de terminal.
- Identidade independente do provedor e dividida em Constituição, personalidade e preferências.
- Adaptação contextual e evolução comportamental, com aprendizado por observação e esclarecimento.
- Núcleo conversacional primeiro; memória persistente depois.
- Autonomia nível zero no primeiro núcleo: nenhuma execução de ferramentas.
- Provedores disponíveis informados: NVIDIA NIM e Token Harbor.
- APIs gratuitas como requisito; não assumir acesso ilimitado.
- Início sem memórias, dados ou calibrações antigas.

## Executar o núcleo offline

Requisito declarado: Python 3.11 ou superior. Ambientes verificados nesta entrega: Python 3.11.16 e 3.14.7 em Linux.

```sh
python -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/mist
```

A instalação obtém Pydantic e suas dependências; a execução do FakeModel não usa rede. Para rodar a partir do código com Pydantic já instalado:

```sh
PYTHONPATH=src python -m mist
PYTHONPATH=src python -m unittest discover -s tests -v
```

Use `/help`, `/mode AUTO|FAST|PRIMARY`, `/style auto|concise|detailed`, `/local TEXTO`, `/status`, `/reset` e `/quit`. Veja configuração, auditoria, limites e validação no [guia do núcleo offline](docs/16-primeiro-nucleo.md).

## Testar com a NVIDIA

A configuração padrão continua offline. Para habilitar a API explicitamente e digitar a chave com entrada oculta:

```sh
PYTHONPATH=src python -m mist --config-dir examples/nvidia --allow-external --ask-api-key
```

Veja resultados reais, privacidade e limites no [guia da integração NVIDIA](docs/17-integracao-nvidia.md). A chave não faz parte do repositório.

O exemplo usa os modelos selecionados no [benchmark](docs/18-benchmark-modelos.md), com teto atual de 4.096 tokens e timeout de operação de 120 s (o benchmark usou 2.048 tokens). Foram oito candidatos sondados e 270 tentativas pontuadas em duas rodadas válidas. Resultados e notebooks estão em `benchmarks/`; a seleção depende das configurações e dos contratos de tarefa registrados, sem certificar desempenho universal.

## Documentação

Comece pelo [índice e estado documental](docs/README.md).

| Tema | Documento |
|---|---|
| Objetivos, visão e escopo | [Visão do produto](docs/01-visao-e-escopo.md) |
| Histórico de escolhas e revisões | [Registro de decisões](docs/02-decisoes.md) |
| Requisitos e prioridades | [Requisitos](docs/03-requisitos.md) |
| Componentes e fluxos | [Arquitetura](docs/04-arquitetura.md) |
| Regras fundamentais | [Constituição](docs/05-constituicao.md) |
| Personalidade e aprendizado | [Identidade adaptativa](docs/06-identidade.md) |
| Tipos, origem e ciclo de vida | [Memória](docs/07-memoria.md) |
| Gateway, modelos e roteamento | [Provedores](docs/08-provedores.md) |
| Privacidade, autorização e auditoria | [Segurança](docs/09-seguranca.md) |
| Esquemas e interfaces | [Contratos](docs/10-contratos.md) |
| Configuração e operação futura | [Configuração](docs/11-configuracao.md) |
| Verificação e experimentos | [Testes e aceitação](docs/12-validacao.md) |
| Etapas e dependências | [Plano de desenvolvimento](docs/13-roadmap.md) |
| Aprendizados da versão antiga | [Legado](docs/14-legado.md) |
| Integração real, configuração e limites | [NVIDIA](docs/17-integracao-nvidia.md) |
| Comparação real e escolha provisória FAST/PRIMARY | [Benchmark de modelos](docs/18-benchmark-modelos.md) |
| Oferta NVIDIA, dados e condições ainda pendentes | [Condições públicas NVIDIA](docs/22-condicoes-nvidia.md) |
| Instalação isolada, pacote local e compatibilidade | [Instalação validada](docs/21-instalacao-validada.md) |
| Rodadas reais, correções e regressão de idioma | [Resultados de identidade](docs/23-avaliacao-real-identidade.md) |
| Identidade, novos cenários e estado de aceitação P0-A | [Avaliação da identidade](docs/20-avaliacao-identidade.md) |
| Contratos JSON opcionais e validação de respostas | [Saída estruturada](docs/19-saida-estruturada.md) |
| Núcleo offline e comandos verificados | [Primeira implementação](docs/16-primeiro-nucleo.md) |
| Fontes, limitações e manutenção | [Proveniência documental](docs/15-fontes-e-manutencao.md) |

## Primeiro marco

O **P0-A** entregará uma conversa funcional no terminal com configuração validada, identidade configurável, FakeModel para testes offline, Gateway de modelos, Guarda de Saída, auditoria e pelo menos um provedor real validado.

O **P0-B** acrescentará memória persistente confiável, proveniência, recuperação lexical, tratamento de contradições, atualização e exclusão.

Voz, interface desktop, ferramentas, modelos locais e autonomia ampliada pertencem à evolução posterior. Veja o [plano](docs/13-roadmap.md).

## Como contribuir nesta etapa

Leia os requisitos e as decisões antes de propor código. Novas escolhas devem registrar justificativa, alternativas, critérios de verificação e impacto no escopo. Atualize os documentos na mesma mudança que alterar o comportamento.

O empacotamento inicial usa `pyproject.toml` e Pydantic 2.13.5. A licença de distribuição continua pendente; nenhum pacote foi publicado no PyPI. Alterações de segurança devem incluir verificação de falhas e bloqueios, além do caminho de sucesso.
