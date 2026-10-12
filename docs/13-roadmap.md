# Plano de desenvolvimento

Não há prazo ou calendário aprovado. As fases descrevem dependências, sem prometer datas.

## Caminho atual

| Etapa | Estado | Saída esperada |
|---|---|---|
| Fase 1 — Auditoria do legado | Relatório histórico, leitura estática. | Lições e riscos; não validação funcional. |
| Fase 2 — Requisitos | Recuperados parcialmente e revisados. | Visão e prioridades consolidadas neste conjunto. |
| Fase 3 — Arquitetura | Revisão corretiva como base. | Modularidade, Guarda, autonomia zero e divisão P0. |
| Fase 4 — Tecnologias e identidade | Consolidação com pendências. | Configuração, modelos e políticas verificáveis. |
| Fase 5 — Experimentos | Planejada. | Evidência das escolhas técnicas relevantes. |
| Fase 6 — Núcleo mínimo | Não implementado. | P0-A, seguido de P0-B validado. |
| Fase 7 — Expansão modular | Futuro. | Ferramentas, projetos e autonomia limitada. |
| Fases 8–9 — Avaliação/estabilização | Futuro. | Comparações, qualidade e operação confiável. |
| Fase 10 — Evolução contínua | Futuro. | Melhorias controladas e reversíveis. |

Experimentos podem ser incrementais. Não é necessário validar embeddings, voz ou desktop antes do P0-A.

## Sequência para o P0-A

1. Especificar Constituição mínima, contratos e configurações versionadas.
2. Implementar Core, CLI e FakeModel com testes offline.
3. Implementar Guarda e auditoria no caminho obrigatório de envio.
4. Impor autonomia zero e testar tentativas de alteração.
5. Implementar seleção manual e roteador determinístico.
6. Validar acesso/configuração de um provedor real e integrar adaptador.
7. Executar critérios P0-A, corrigir falhas e documentar uso real.

Pydantic, cliente HTTP e versões precisam ser confirmados quando escolhidos. A seleção do modelo principal não deve bloquear o fluxo offline.

## Sequência para o P0-B

1. Validar SQLite/FTS5 e definir schema/migrations.
2. Implementar contrato de memória e ciclo de candidatos.
3. Implementar persistência, recuperação lexical e orçamento.
4. Integrar escopo, sensibilidade e estados epistêmicos.
5. Implementar correção, conflito e exclusão de derivados.
6. Definir backup/retenção/restauração e exportação.
7. Integrar preferências entre sessões.
8. Executar avaliação de recuperação e critérios P0-B.

Não importar dados antigos para acelerar essa entrega.

## Evolução posterior

**P1, direção proposta:** projetos mais completos, relações entre memórias, consolidação, ferramentas declarativas, busca web segura, permissões por tarefa, cancelamento e painéis básicos.

**P2, direção proposta:** procedimentos, voz, desktop, estado interno simulado, execução isolada, retomada/segundo plano e experimentos de recuperação/modelos locais.

**P3, direção proposta:** modalidades adicionais, integrações ampliadas e melhoria contínua controlada.

Prioridades de P1–P3 são herdadas das propostas de requisitos e devem ser revistas conforme o núcleo real. Não são autorização para construir tudo simultaneamente.

## Pendências técnicas

| Tema | O que falta | Quando fechar |
|---|---|---|
| Python/dependências | Versões, cliente HTTP e distribuição. | Início do P0-A. |
| Constituição | Redação/esquema executável inicial. | Antes de habilitar geração real. |
| Perfis | Diretrizes mínimas e precedência contextual. | P0-A. |
| APIs | Endpoints, IDs, autenticação, cotas e política de dados. | Antes de integrar cada provedor. |
| Modelo principal | Avaliação com candidatos reais. | Configuração de operação normal. |
| Modelo rápido | Confirmar indicação e ID real. | Configuração de operação normal. |
| Credenciais | Ambiente/.env/cofre e operação segura. | Integração real. |
| Guarda | Taxonomia, regras e detecção complementar. | Antes de enviar dados. |
| Auditoria | Storage, erros, retenção e recuperação. | P0-A. |
| SQLite/FTS5 | Experimento, schema e migrations. | P0-B. |
| Exclusão/backups | Política e mecanismo contra reaparecimento. | Antes de concluir P0-B. |
| Licença | Condições de distribuição do projeto. | Antes de definir distribuição. |

## Limites da expansão

Sem frameworks de agentes, bancos vetoriais dedicados, infraestrutura distribuída ou dezenas de modelos sem necessidade demonstrada. Sem daemon de sonhos/presença como dependência do núcleo.

A identidade evolui por configuração e preferências verificadas; políticas fundamentais não mudam automaticamente.

## Próxima ação concreta

Fechar o primeiro contrato/configuração do P0-A e o fluxo com FakeModel. Esta documentação é a base para isso; não reiniciar o levantamento das escolhas já tomadas.

