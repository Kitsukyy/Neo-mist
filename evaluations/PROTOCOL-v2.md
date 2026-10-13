# Rodada adaptativa de identidade — v2

Definida em 12/10/2026 após ler a rodada v1 e antes de iniciar novas chamadas. Mesmos cenários e critérios de `PROTOCOL.md`, uma repetição por modelo e sessão nova por cenário. Reutilizar as perguntas significa que esta rodada é adaptativa: não é um teste independente nem comprova generalização.

Mudanças previstas:

1. Instruções distinguem hospedar a API de desenvolver/treinar o modelo; autoria deve ter fonte explícita.
2. Autonomia zero bloqueia ferramentas e ações no computador, mas permite geração externa habilitada e aprovada pela Guarda. local_only é uma classificação independente.
3. Preferência de respostas concisas até 120 palavras e detalhadas até 250, salvo pedido explícito diferente. Não repetir a apresentação a cada mensagem nem prometer retenção do provedor.
4. Runner registra somente contagens numéricas de uso e stop reason normalizado do adaptador. Isso ajuda a diagnosticar respostas inválidas; não captura raciocínio oculto.

Modelos, raciocínio, temperatura, limite de 2.048 tokens e timeout de 120 segundos permanecem iguais a v1. Prazo de despacho de 1.800 segundos; nenhuma nova tentativa automática. Cenários e rubricas não foram alterados. Registrar novos hashes e diretório distinto; preservar v1 com sua falha de provedor e ressalvas.

A revisão usa todos os turnos e todos os critérios por cenário, pelo mesmo avaliador de IA, não cego. Verificador não permite pontuar cenários incompletos como qualidade nem agregar modelos para ocultar falhas. Questões operacionais materiais são registradas separadamente das rubricas e bloqueiam recomendação de aceitação mesmo se a amostra atingir o limiar. Não atribuir melhora causal a uma frase isolada: há várias mudanças de instrução e possível variação do serviço.
