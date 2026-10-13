# Plano de desenvolvimento

Não há prazo ou calendário aprovado. As fases descrevem dependências, sem prometer datas.

## Caminho atual

| Etapa | Estado | Saída esperada |
|---|---|---|
| Fase 1 — Auditoria do legado | Relatório histórico, leitura estática. | Lições e riscos; não validação funcional. |
| Fase 2 — Requisitos | Recuperados parcialmente e revisados. | Visão e prioridades consolidadas neste conjunto. |
| Fase 3 — Arquitetura | Revisão corretiva como base. | Modularidade, Guarda, autonomia zero e divisão P0. |
| Fase 4 — Tecnologias e identidade | Consolidação com pendências. | Configuração, modelos e políticas verificáveis. |
| Fase 5 — Experimentos | Provedor NVIDIA e benchmark de modelos executados; sondagem lexical e avaliação real dirigida de memória executadas. | Evidência das escolhas técnicas relevantes. |
| Fase 6 — Núcleo mínimo | Core, NVIDIA, saída estruturada e memória local 0.4.1 implementados; validação offline/instalação e avaliação incremental; condições da conta e revisão pendentes. | P0-A, seguido de P0-B validado. |
| Fase 7 — Expansão modular | Projetos e tarefas locais 0.5.0 implementados; demais recursos futuros. | Evolução de projetos, ferramentas e autonomia limitada. |
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

Python ≥3.11 e Pydantic 2.13.5 são as escolhas iniciais de implementação; o adaptador NVIDIA usa o cliente HTTPS da biblioteca padrão, sem dependência HTTP adicional. A seleção do modelo principal não deve bloquear o fluxo offline.

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
| Python/dependências | Instalação e pacote local verificados em Linux 3.11.16/3.14.7; outras versões/plataformas não testadas. | Início do P0-A. |
| Constituição | Redação/esquema executáveis implementados e testados. | Antes de habilitar geração real. |
| Perfis | Regras e duas rodadas reais revisadas; correção final de idioma com regressão direcionada, sem homologação universal. | P0-A. |
| APIs | Endpoint/IDs/autenticação verificados; fontes públicas consultadas, oferta gratuita e até 40 RPM relatados pelo usuário; política de dados/termos aplicáveis pendentes. | Antes de integrar cada provedor. |
| Modelo principal | Kimi K3 selecionado provisoriamente; repetir com tarefas inéditas e extensas. | Antes de homologação definitiva. |
| Modelo rápido | Super com raciocínio selecionado provisoriamente; acompanhar latência e restrições de comunicação. | Antes de homologação definitiva. |
| Credenciais | Leitura oculta usada com autorização renovada; chave temporária não persistida nem incluída no pacote. | Integração real. |
| Guarda | Bloqueios, local-only e aprovações vinculadas implementados/testados; detecção complementar é evolução. | Antes de enviar dados. |
| Auditoria | Metadados privados e falhas com suspensão testados; política operacional de retenção pendente. | P0-A. |
| SQLite/FTS5 | Schema 1, migração transacional, busca lexical e experimento sintético de dez mil itens implementados; qualidade em conversa livre ainda incremental. | P0-B. |
| Exclusão/backups | Exclusão de versões/derivados, snapshots manuais e registro sobrevivente contra reaparecimento implementados; não apaga cópias externas/históricas. | P0-B. |
| Licença | Condições de distribuição do projeto. | Antes de definir distribuição. |

## Limites da expansão

Sem frameworks de agentes, bancos vetoriais dedicados, infraestrutura distribuída ou dezenas de modelos sem necessidade demonstrada. Sem daemon de sonhos/presença como dependência do núcleo.

A identidade evolui por configuração e preferências verificadas; políticas fundamentais não mudam automaticamente.

## Próxima ação concreta

A base offline foi implementada e testada: passos 1–5 têm uma versão mínima funcional, com os limites registrados no [guia](16-primeiro-nucleo.md). O adaptador NVIDIA tem geração real verificada e [benchmark com seleção provisória](18-benchmark-modelos.md). A saída estruturada foi implementada no [documento 19](19-saida-estruturada.md); a instalação foi validada no [documento 21](21-instalacao-validada.md). As rodadas reais e os ajustes estão no [documento 23](23-avaliacao-real-identidade.md). Próximo passo: revisar/integrar a branch `mist-p0a-validacao` publicada no GitHub e registrar oferta/cotas/condições de dados da conta conforme [fontes e pendências](22-condicoes-nvidia.md). O usuário concluiu o login do editor e autorizou seu acesso; a árvore publicada foi comparada integralmente com a entrega local. Enquanto as condições da conta permanecem pendentes, o desenvolvimento local do P0-B avançou por autorização do usuário: [memória 0.4.0](25-memoria-persistente.md), com captura automática escolhida explicitamente. Próxima validação é utilidade/qualidade em conversas inéditas sob política de envio definida; recursos P1 exigem escopo e permissões próprios. O envio externo exige configuração permitida e habilitação explícita.

### Incremento atual — 0.4.1

Avaliação real de memória com fixtures e correção de proveniência no documento
26. Oferta/painel NVIDIA transcritos pelo usuário no documento 22, sem confirmação
de retenção/treinamento. Próxima decisão de produto: escolher o primeiro recurso
usável de P1 e seu escopo; execução de ferramentas permanece desabilitada.

### Projetos 0.5.0

O usuário escolheu projetos como primeiro incremento de P1. Cadastro e tarefas
locais foram implementados no documento 27, ligados ao seletor de memórias.
Progresso manual, sem execução de tarefas ou montagem automática do catálogo
no contexto externo. Próximos incrementos: uso em conversa sob política definida,
relações/consolidação e interface; ferramentas continuam exigindo escopo próprio.
