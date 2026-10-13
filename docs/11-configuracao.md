# Configuração e operação planejada

Este documento preserva a operação planejada para o P0-A completo. A CLI, os arquivos JSON e o adaptador NVIDIA já estão implementados; consulte o [guia offline](16-primeiro-nucleo.md) e a [integração real](17-integracao-nvidia.md).

## Separação proposta

| Grupo | Conteúdo | Versionar? |
|---|---|---|
| settings | Modo, limites, orçamento de contexto e auditoria. | Configuração não secreta. |
| constitution | Regras e versão da identidade fundamental. | Sim. |
| personality | Diretrizes comportamentais e adaptação. | Sim, sem dados pessoais inferidos. |
| models | IDs, capacidades, papéis, destinos e políticas. | Parte não secreta. |
| credentials | Chaves reais e autenticação. | Não. |
| runtime | Logs, banco de memória e estado de execução. | Não por padrão. |

YAML é o formato proposto no documento mestre. Parser, esquema e precedência entre arquivos/ambiente ainda precisam ser definidos. Não confundir exemplo ilustrativo com configuração utilizável.

## Exemplo documental de configuração

```yaml
# Rascunho conceitual; não existe parser implementado.
schema_version: 1
router:
  default_mode: AUTO
  fast_model: "<id-interno-a-validar>"
  primary_model: "<id-interno-a-validar>"
autonomy:
  tools_enabled: false
  level: 0
audit:
  required_before_external_send: true
memory:
  enabled: false # P0-A
```

Todos os placeholders exigem substituição e validação. Configuração externa incompleta não impede necessariamente testes FakeModel, desde que o modo offline seja explícito e não inicialize adaptadores de rede.

## Credenciais

A proposta inicial é resolver segredos de ambiente ou cofre local. Se .env for adotado, deve ficar fora do Git; .env.example contém apenas nomes/valores ilustrativos.

Referências de variáveis como NVIDIA_API_KEY ou TOKEN_HARBOR_API_KEY são exemplos propostos, não convenções finais nem variáveis confirmadas pelas APIs.

Não reutilizar defaults secretos do código antigo. Não solicitar envio de chaves por chat ou copiar valores para documentação.

## Inicialização esperada

1. Carregar configuração e versão.
2. Validar Constituição/perfil e limites.
3. Resolver modelos e políticas.
4. Verificar referências de credenciais para adaptadores externos habilitados.
5. Verificar disponibilidade da auditoria.
6. Inicializar a composição sem executar ferramentas.
7. No P0-B, abrir armazenamento e validar migrations.
8. Informar modo ativo e limitações.

Falhas devem identificar o campo ou componente, nunca imprimir seu segredo.

## Estados operacionais propostos

Pronto, processando, bloqueado pela política, falha recuperável e indisponível. A UI mostra a categoria relevante sem revelar detalhes privados.

No P0-A, sair encerra o contexto da sessão; não há promessa de retomada persistente. Preferências corrigidas na sessão deixam de existir entre execuções até P0-B.

## Operação offline

FakeModel roda sem rede e credenciais. Não é uma IA local real. Em modo real sem rede, informar indisponibilidade; não substituir por simulação sem indicação.

No P0-B, recuperação lexical local não exige embeddings externos. Definir comportamento em falhas do banco separadamente da falha do provedor.

## Arquivos locais

Diretórios de configuração privada, logs e banco serão definidos conforme convenções Linux e requisitos de instalação. Permissões de arquivos, backup, retenção e criptografia não foram fechados.

Estado de execução não deve ser versionado no repositório. Índices/caches são reconstruíveis e subordinados à fonte de verdade.

## Instalação futura

Antes de publicar comandos de instalação, fixar versão de Python, dependências, método de distribuição e entrada da CLI. Validar em ambiente limpo e documentar versões suportadas.

Não inventar um comando “mist run”, arquivo requirements ou pacote PyPI ainda inexistente.

## Manutenção

Documentar mudanças de configuração, migrations e incompatibilidades. A recuperação de erros deve respeitar Guarda/auditoria. Substituir modelo não permite ampliar automaticamente destinos ou orçamento.

