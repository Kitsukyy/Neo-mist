# Visão e escopo

## Visão escolhida

A Mist combinará quatro funções: assistente pessoal, IA com identidade própria, companheira adaptativa e plataforma modular. O usuário decidiu reconstruí-la e reconsiderar tecnologias anteriores, preservando o nome e os conceitos úteis sem obrigação de reutilizar implementações.

A visão de longo prazo é híbrida, multimodal e autônoma dentro de limites configuráveis. Isso significa evoluir para texto, voz, interface desktop, APIs, modelos locais e acompanhamento de tarefas autorizadas.

## Condições iniciais decididas

| Aspecto | Decisão |
|---|---|
| Plataforma | Um computador, execução local no Linux. |
| Interface inicial | Algo simples para testar; terminal na direção consolidada. |
| Dados antigos | Nenhuma migração de memórias, dados ou calibrações. |
| Volume esperado | Dezenas de milhares de memórias, sem otimização prematura. |
| Processamento externo | APIs são aceitáveis, com controle sobre dados e destinos. |
| Custos | Priorizar e operar com APIs gratuitas; cotas reais precisam de validação. |
| Identidade | Construída a partir das decisões atuais. |
| Provedores disponíveis | NVIDIA NIM e Token Harbor, segundo o usuário. |

A execução local mantém a aplicação e, futuramente, a memória na máquina. Não significa que respostas de APIs sejam processadas localmente.

## P0-A: núcleo conversacional

Inclui CLI, configuração validada, histórico de sessão, identidade, adaptação contextual, Gateway, roteador determinístico, FakeModel, um adaptador real, Guarda de Saída, autorização de ferramentas sempre negada e auditoria operacional.

Não inclui persistência de conversas ou memórias de longo prazo, embeddings, voz, GUI, ferramentas executáveis, daemon autônomo ou arquitetura de agentes. A auditoria pode persistir metadados operacionais sem constituir memória conversacional.

## P0-B: memória confiável

Adiciona armazenamento local, recuperação lexical, proveniência, estados epistêmicos, ciclo de candidatos, contradições, atualização, exclusão e preferências entre sessões. SQLite/FTS5 é a proposta inicial, não um benchmark concluído.

P0-B depende de um P0-A validado. Não exige banco vetorial nem representação OCEAN/VAD.

## Evolução posterior

- Modelos locais quando hardware, qualidade e manutenção justificarem.
- Ferramentas com contratos, permissões e limites fora do modelo.
- Voz e outras modalidades.
- Desktop com chat e painéis de memória, projetos, personalidade e operações.
- Planejamento, cancelamento, tarefas persistentes e segundo plano.
- Estado emocional simulado com efeitos úteis e verificáveis.
- Avaliação e melhoria controlada, com aprovação e reversão.

As tecnologias dessas capacidades e sua ordem exata ainda não foram fechadas.

## Princípios de produto

A identidade deve manter continuidade mesmo quando o modelo mudar. A experiência deve adaptar linguagem e iniciativa à situação. Precisão, transparência e limites do sistema prevalecem sobre estilo.

A Mist deve distinguir sugestão, tentativa e ação executada. Não deve afirmar que concluiu operações que não realizou. Evolução comportamental não é autorização para alterar princípios ou permissões.

Não há decisão final sobre nome de pacote, aparência, avatar, framework de GUI ou licença. O repositório é chamado Neo-mist; a assistente continua chamada Mist.

