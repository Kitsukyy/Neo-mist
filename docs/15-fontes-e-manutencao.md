# Fontes, limitações e manutenção

## Base desta documentação

Decisões e propostas foram recuperadas dos seis chats acessíveis do projeto Mist:

1. Lembrar da Mist.
2. Lembrar da Mist (1).
3. Branch · Lembrar da Mist (1).
4. Branch · Lembrar da Mist (1) (1).
5. Branch · Branch · Lembrar da Mist (1) (1).
6. Branch · Branch · Lembrar da Mist (1) (1) (1).

Turnos compartilhados entre branches foram deduplicados. A coleta retornou sem páginas adicionais. Nenhum chat arquivado da Mist apareceu na listagem disponível.

Os conteúdos incluem auditoria da Fase 1, requisitos da Fase 2, arquitetura inicial e revisão corretiva da Fase 3, escolhas de tecnologias/provedores e identidade da Fase 4.

## Limitação de recuperação

A ferramenta limita o conteúdo de uma mensagem a 20.000 caracteres. A Especificação de Requisitos da Fase 2 e o Documento Mestre da Fase 4 ficaram parcialmente truncados. As partes finais não puderam ser recuperadas por paginação.

Portanto, esta documentação consolida todas as decisões acessíveis, mas não afirma ser uma transcrição integral desses dois documentos. Não reproduz como completos os 36 critérios históricos, pesos finais ou experimentos ausentes. Os critérios VAL são uma organização nova para tornar o estado recuperado verificável.

O superprompt original foi referido no histórico, mas seu texto integral não estava disponível. Não é apresentado como fonte diretamente lida.

## Como se resolveu divergência

- Decisões explícitas mais recentes do usuário prevalecem.
- Revisão corretiva substitui proposta arquitetural anterior.
- Documento mestre é a síntese mais recente, com propostas ainda identificadas.
- Respostas do assistente não são atribuídas ao usuário sem evidência.
- Campos, exemplos e critérios novos são especificações propostas.

A atribuição do modelo rápido foi mantida como proposta; o modelo principal permanece aberto. Memória persistente ficou no P0-B apesar de aparecer no P0-A em sugestão anterior.

## Conteúdo publicado

Foi feita uma síntese técnica adequada ao repositório público. Não foi publicada uma transcrição dos chats, credenciais, anexos antigos, dados de calibração ou informações pessoais de conta.

A documentação não verifica disponibilidade atual dos modelos citados. Nomes e acesso são relatos históricos. A integração futura deve buscar documentação oficial e catálogo acessível, registrando data e resultado.

## Rastreabilidade por tema

| Tema | Origem principal |
|---|---|
| Visão híbrida/multimodal/autonomia | Escolhas iniciais do usuário em Lembrar da Mist. |
| Um computador, sem migração, interface simples e custo | Respostas Q1–Q7 em Branch · Lembrar da Mist (1). |
| Separação P0-A/P0-B e Guarda obrigatória | Revisão corretiva da Fase 3 e ajustes subsequentes. |
| Provedores e nomes relatados | Chats de início da Fase 4. |
| Constituição e contratos nomeados | Proposta da Fase 4.3. |
| Quatro dimensões e evolução | Escolha da opção C na Fase 4.5. |
| Observação e perguntas | Escolha “Combinar os dois” na Fase 4.6. |
| Dois papéis e modos | Documento Mestre da Fase 4. |
| Memórias, origem e exclusão | Requisitos da Fase 2 e correções de revisão. |
| Lições do legado | Auditoria histórica e revisões. |

## Regras de manutenção

1. Atualizar documentos na mesma mudança que afetar contratos/comportamento.
2. Registrar decisões com estado, justificativa e critérios.
3. Não marcar planejado como implementado.
4. Não declarar teste ou benchmark sem execução registrada.
5. Explicitar incompatibilidades de configuração e migrations.
6. Remover pendências somente quando resolvidas com evidência.
7. Registrar substituição de decisões antigas em vez de apagá-las silenciosamente.
8. Não transformar correções de documentação em mudança de autorização.

## Estado inicial desta publicação

Conjunto documental 1.0. Inspeção do repositório: apenas README inicial, sem implementação da nova Mist. Esta mudança adiciona documentação, não instala dependências nem cria funcionalidades executáveis.

