# Sistema de memória

**Escopo:** persistência entra no P0-B. No P0-A há histórico de sessão e contexto temporário. A Mist começa com armazenamento vazio, sem importação de dados ou calibrações antigas.

**Tecnologia proposta:** SQLite com FTS5 para recuperação lexical. Validar no ambiente antes de fechar o schema. Não há decisão de usar embeddings, Supabase, PostgreSQL ou banco vetorial no primeiro núcleo.

## Seis tipos conceituais

| Tipo | O que representa | Entrada inicial |
|---|---|---|
| Trabalho | Objetivo, contexto, decisões e erros da sessão. | P0-A temporário; checkpoints futuros. |
| Episódica | Eventos relevantes e resultados de tarefas/conversas. | P0-B com critérios explícitos de relevância. |
| Semântica | Informações relativamente estáveis, conceitos e entidades. | P0-B. |
| Preferências | Declarações e hipóteses sobre escolhas/interação. | P0-B. |
| Projetos | Objetivos, decisões, problemas, contexto e próximas etapas. | Escopo no P0-B; recursos completos posteriores. |
| Procedimentos | Condições, passos e resultados de estratégias úteis. | Expansão posterior com evidência de sucesso. |

Cache é mecanismo de desempenho, não tipo de memória. Identidade central fica fora desses tipos.

## Modelo conceitual

Campos propostos, não schema SQL final:

| Campo/grupo | Finalidade |
|---|---|
| ID estável e tipo | Identificação única sem depender do conteúdo apenas. |
| Conteúdo e resumo | Informação armazenada e representação para recuperação. |
| Origem e referência | Usuário, sessão/mensagem, ferramenta ou derivação. |
| Data da fonte | Momento da declaração/evento, distinto da gravação. |
| Estado epistêmico | Confirmado, inferido ou hipótese. |
| Confiança opcional | Estimativa quando houver método justificável. |
| Escopo | Global, projeto ou tarefa/ferramenta quando existir. |
| Sensibilidade e política | Controle local-only e permissões por destino. |
| Ciclo de vida | Ativa, arquivada, substituída ou excluída. |
| Versão e relações | Substituição, derivação e vínculos entre itens. |
| Datas/uso/validade | Criação, atualização, último acesso e expiração opcional. |
| Hash de conteúdo | Deduplicação exata dentro de escopo definido. |

Não exigir confiança numérica fictícia em todas as memórias. Importância e pesos de ranking são hipóteses a calibrar.

## Origem e sustentação

| Situação | Tratamento |
|---|---|
| Usuário declara preferência | Registrar que a preferência foi declarada e por quem/quando. |
| Aplicação infere um padrão | Manter origem da inferência e referências de evidência. |
| Modelo sugere uma afirmação | Não persistir como fato confirmado só por ter sido gerada. |
| Informação verificada externamente | Registrar fonte e método de verificação, se esse recurso existir. |
| Preferência muda | Atualizar versão/validade e preservar relações necessárias. |

Confirmado não significa verdade universal. Uma preferência confirmada é sustentada por declaração/confirmacão do usuário; uma alegação factual exige contexto de verificação próprio.

Recuperar frequentemente uma hipótese não a confirma. Confiança alta também não basta.

## Ciclo de candidatos

1. Identificar algo potencialmente útil.
2. Avaliar relevância, escopo, origem e sensibilidade.
3. Classificar estado epistêmico.
4. Checar duplicata exata e possíveis conflitos.
5. Validar campos e política.
6. Persistir de modo transacional.
7. Registrar metadados da operação.

Se um modelo auxiliar extrair candidatos, seu retorno é não confiável e passa por validação. A chamada externa também exige Guarda/auditoria. Nenhum modelo escreve diretamente na fonte de verdade.

Critérios finais de extração automática e necessidade de confirmação estão pendentes. Não gravar toda conversa indiscriminadamente.

## Recuperação e contexto

- Consulta lexical e filtros por escopo, validade, estado e sensibilidade.
- Retorno com referências, razão da seleção e metadados epistêmicos.
- Limites configuráveis de itens e orçamento de contexto.
- Seleção determinística e observável quando a pontuação empatar.
- Conteúdo excluído/substituído não volta como versão vigente.
- Não enviar itens local-only ao modelo externo; filtrar antes da montagem e conferir na Guarda.
- Semântica/embeddings só depois de comparar com baseline lexical.

Pesos de importância, recência, frequência e meia-vida não herdam constantes do legado.

## Deduplicação

Hash exato é a estratégia inicial. Definir normalização e escopo antes de implementar; preservar fontes múltiplas quando o mesmo conteúdo tiver evidências distintas.

Hash identifica igualdade, não equivalência semântica. Conteúdos parecidos não são mesclados automaticamente.

## Contradição e atualização

Detectar conflito não significa resolvê-lo. Registrar as fontes, datas e escopos, distinguir mudança temporal de incompatibilidade e pedir esclarecimento quando necessário.

Uma correção explícita orienta o contexto atual. A persistência usa versão e vínculos de substituição, evitando duas versões contraditórias simultaneamente apresentadas como vigentes.

Processo exato de detecção lexical/modelo está pendente. Não inventar um árbitro infalível de verdade.

## Esquecimento, arquivamento e exclusão

Decaimento reduz relevância. Arquivamento retira do contexto corrente sem afirmar que o conteúdo foi apagado. Expiração e exclusão têm fluxos próprios.

Exclusão solicitada deve abranger conteúdo, índices FTS, caches, resumos e derivados que o reproduzam. Tombstones, se usados, contêm apenas metadados mínimos necessários, sem preservar o texto excluído.

Backups exigem política de retenção explícita. Uma restauração não pode reintroduzir dados excluídos como ativos. O mecanismo de reconciliação com exclusões e o alcance da remoção física devem ser definidos e testados antes da entrega. Não prometer remoção instantânea de todas as cópias históricas sem mecanismo demonstrado.

## Integridade e portabilidade

Schema único, migrations versionadas, transações e uma fonte de verdade. Caches são derivados e reconstruíveis. Exportação em formato aberto deve preservar relações, origem e versões permitidas.

Testar atualização interrompida, corrupção/indisponibilidade, backup e restauração. Com memória indisponível, a conversa pode continuar sem contexto recuperado se a configuração permitir; nunca apresentar informação inexistente como recuperada.

## Embeddings futuros

Armazenar modelo, dimensão, versão e data em estrutura separada do conteúdo. Reindexação precisa de avaliação de qualidade, retomada após interrupção e fonte original preservada.

Embeddings remotos obedecem às mesmas regras local-only. Dimensão, modelo e banco vetorial não foram escolhidos.

