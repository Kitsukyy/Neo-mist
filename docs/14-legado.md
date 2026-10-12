# Legado e lições

## Evidência disponível

A auditoria histórica analisou estaticamente um ZIP da Mist antiga. Relatou 85 arquivos Python e aproximadamente 12 mil linhas. Não executou o sistema nem demonstrou funcionamento dos componentes.

Esta publicação não realizou uma nova auditoria do ZIP. Achados abaixo são relatos recuperados. Nomes de arquivos identificam o legado, não arquivos presentes na nova versão.

## Problemas relatados

- mist.py misturava UI, roteamento, busca, histórico e comandos.
- supabase_memory.py combinava storage, regras de memória e chamadas de LLM.
- SupabaseMemory e MemoryManager usavam vocabulários de colunas incompatíveis.
- Memória, emoção e persona eram acopladas por uma flag.
- Existiam OCEAN, VAD e outra representação de humor.
- Gatilhos por substring podiam produzir falsos positivos.
- Havia promoção de memórias sem confirmação e exclusão por limiar.
- Cache JSON local e backend remoto atuavam como fontes concorrentes.
- O provedor e endpoints estavam fixos em mais de um módulo.
- Fallback e roteamento dependiam de decisões do modelo.
- Conteúdo raspado era inserido em prompt sem fronteira de confiança.
- Não foram encontrados testes, migrations e documentação operacional suficientes.
- Configuração dispersa e tratamento genérico/silencioso de erros.
- Credenciais embutidas e resíduos de estado/geração no projeto.

O usuário informou que as credenciais antigas expiraram e que o schema SQL deixou de existir. Nenhuma chave ou configuração antiga é reproduzida nesta documentação.

## O que aproveitar

Conceitos: módulos substituíveis, recuperação lexical quando semântica falha, separação de responsabilidades, pontuação de relevância a avaliar e necessidade de manutenção da memória.

O usuário decidiu não importar memórias, dados ou calibrações. A nova identidade parte das escolhas atuais. Nenhum código deve ser preservado por obrigação.

## O que evitar reproduzir

- Um novo monólito apenas reorganizado em pastas.
- Dois contratos de memória sobre a mesma fonte.
- Identidade misturada com fatos do usuário.
- Caches não derivados.
- Frequência interpretada como verdade.
- Esquecimento como exclusão irreversível silenciosa.
- Aliases de modelos que apontem para modelos diferentes.
- Segredos como defaults.
- Framework distribuído para aplicação de um computador.
- Tarefas de vínculo/sonho/presença sem autonomia e evidência de utilidade.

## Tratamento do código antigo

Se um componente for reaproveitado futuramente, revisar seu contrato e dependências, remover acoplamentos, validar segurança e escrever testes relevantes antes de declarar integração concluída.

Não reconstruir schema perdido por suposição nem tratar arquivos de estado do daemon como prova de execução bem-sucedida.

A auditoria original classificava alguns componentes apenas como “investigar”. Esta documentação não transforma nomes de arquivos não lidos em implementação verificada.

