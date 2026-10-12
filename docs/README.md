# Documentação da Mist

Versão documental: 1.0 · Data: 11 de outubro de 2026 · Idioma: português do Brasil.

Este conjunto documenta as decisões recuperadas sobre a nova Mist e organiza a especificação para implementação. Descreve comportamento esperado, não capacidades já demonstradas pelo programa.

## Como interpretar o estado de uma informação

| Estado | Significado |
|---|---|
| Decisão do usuário | Escolha explicitamente registrada no histórico. |
| Diretriz consolidada | Arquitetura ou regra mantida na revisão mais recente e no documento mestre. |
| Proposta técnica | Detalhamento recomendado que ainda precisa de validação ou fechamento. |
| Pendente | Informação ou escolha que não foi resolvida. |
| Futuro | Capacidade desejada fora dos marcos iniciais. |

Uma diretriz documental não significa implementação concluída. Testes só podem ser declarados aprovados quando executados e registrados.

## Ordem de leitura

1. [Visão e escopo](01-visao-e-escopo.md) e [decisões](02-decisoes.md).
2. [Requisitos](03-requisitos.md) e [arquitetura](04-arquitetura.md).
3. [Constituição](05-constituicao.md), [identidade](06-identidade.md) e [segurança](09-seguranca.md).
4. [Memória](07-memoria.md), [provedores](08-provedores.md), [contratos](10-contratos.md) e [configuração](11-configuracao.md).
5. [Validação](12-validacao.md) e [roadmap](13-roadmap.md).
6. [Legado](14-legado.md) e [fontes](15-fontes-e-manutencao.md).

## Precedência entre documentos

A decisão explícita mais recente do usuário prevalece sobre sugestões anteriores. A revisão corretiva da arquitetura e o documento mestre orientam o escopo atual. Os detalhes novos deste conjunto são propostas quando não estavam definidos no histórico.

Para divergências de escopo, consulte o registro de decisões. Para permissões e privacidade, consulte Constituição e segurança. Nenhum documento amplia silenciosamente o P0-A.

## Estado real do repositório

Na inspeção inicial desta publicação, havia apenas um README com o nome do projeto. Não foi encontrado código da nova Mist. Portanto:

- a Fase 4 é uma consolidação documental, com pendências técnicas;
- o P0-A e o P0-B são entregas planejadas;
- não há benchmark, modelo principal escolhido ou adaptador real validado;
- exemplos de contratos e configuração são especificações, não arquivos executáveis.

## Glossário

| Termo | Definição no projeto |
|---|---|
| Core | Coordena uma interação e o estado da sessão. |
| Gateway | Fronteira uniforme de geração entre Core e provedores. |
| Adaptador | Integra uma API ou modelo sem espalhar seu formato pelo núcleo. |
| Guarda de Saída | Verifica o payload antes do envio a um destino externo. |
| Constituição | Regras fundamentais controladas pela aplicação. |
| Preferência | Escolha ou padrão de interação, com origem e possibilidade de correção. |
| Proveniência | Registro de onde, quando e em que contexto veio uma informação. |
| Estado epistêmico | Grau e tipo de sustentação de uma informação. |
| Local-only | Informação que não pode ser enviada a serviços externos. |
| FakeModel | Provedor simulado e determinístico para testes. |
| Fallback | Alternativa limitada após falha recuperável, sujeita a nova avaliação de envio. |
| P0-A / P0-B | Marcos internos do núcleo mínimo: conversa e memória confiável. |

