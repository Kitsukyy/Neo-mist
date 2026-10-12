# Neo-mist — Mist

A Mist é uma assistente pessoal de IA com identidade própria, personalidade adaptativa e arquitetura modular. A aplicação será executada localmente, usando provedores externos para geração de respostas e permitindo, futuramente, modelos locais, memória persistente, ferramentas, voz e autonomia configurável.

**Estado:** documentação e consolidação técnica da nova versão. O núcleo P0-A ainda será implementado. Este repositório não oferece, neste momento, um programa executável.

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
| Fontes, limitações e manutenção | [Proveniência documental](docs/15-fontes-e-manutencao.md) |

## Primeiro marco

O **P0-A** entregará uma conversa funcional no terminal com configuração validada, identidade configurável, FakeModel para testes offline, Gateway de modelos, Guarda de Saída, auditoria e pelo menos um provedor real validado.

O **P0-B** acrescentará memória persistente confiável, proveniência, recuperação lexical, tratamento de contradições, atualização e exclusão.

Voz, interface desktop, ferramentas, modelos locais e autonomia ampliada pertencem à evolução posterior. Veja o [plano](docs/13-roadmap.md).

## Como contribuir nesta etapa

Leia os requisitos e as decisões antes de propor código. Novas escolhas devem registrar justificativa, alternativas, critérios de verificação e impacto no escopo. Atualize os documentos na mesma mudança que alterar o comportamento.

Versões de Python, dependências, licença de distribuição e comandos de instalação serão definidos durante a implementação. Não há instruções de execução verificadas ainda.

