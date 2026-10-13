# Condições públicas NVIDIA e pendências da conta

Consulta pública em 12/10/2026, complementada pelo relato da conta em 13/10/2026. Registro das fontes públicas para o desenvolvimento da Mist; os termos aceitos na conta do usuário ainda precisam ser identificados. A consulta pública não realizou login na NVIDIA, aceitação de termos ou compra. Posteriormente, o usuário confirmou a chave temporária ativa e autorizou continuar: as rodadas sintéticas reais estão no [documento 23](23-avaliacao-real-identidade.md).

## Fontes e conclusões verificáveis

A [FAQ oficial](https://docs.api.nvidia.com/nim/docs/product) descreve acesso gratuito via Developer Program para prototipagem e diferencia esse acesso do uso em produção. Não informa nesta página a cota restante ou o limite de requisições dos modelos selecionados na conta da Mist. A documentação não comprova gratuidade ilimitada nem autorização para servir usuários finais.

Nos [termos gerais Developer](https://developer.nvidia.com/legal/terms), seção 4, contratos específicos de produto podem prevalecer; seção 7 descreve ofertas promocionais sujeitas a condições e encerramento. Logo, é necessário identificar o contrato da oferta efetivamente usada.

O [PDF oficial API Trial Terms](https://assets.ngc.nvidia.com/products/api-catalog/legal/NVIDIA%20API%20Trial%20Terms%20of%20Service.pdf), seções 1.2–1.4, limita o trial a testes/avaliação e admite limites de uso. Na seção 2.3 há uma regra de não armazenamento/uso ao fim da sessão, com exceções na seção 2.4 e divulgações específicas. A seção 3.3 prevê coleta de conteúdo para melhoria de produtos/modelos; portanto, não registrar uma garantia irrestrita de ausência de retenção ou treinamento. As seções 2.6 e 4.3 restringem conteúdo confidencial/sensível e dados pessoais, ressalvadas permissões explícitas do serviço. Esse PDF é uma fonte pública acessível; não foi confirmado como o contrato vigente da conta.

A rota `https://build.nvidia.com/api-catalog-terms` retornou página 404 no navegador durante a consulta. Não usar como evidência de termos vigentes. A FAQ e o PDF descrevem ofertas com escopos distintos; uma referência a créditos no PDF não comprova que a conta atual use créditos.

## Relato da conta — 13/10/2026

O usuário copiou textos da FAQ de `build.nvidia.com` e de seu painel: modelos
gratuitos para prototipar, até 40 requisições por minuto para a maioria dos
modelos e ausência de cobrança por token no nível gratuito. A tela também
informa variação por modelo e throttling devido ao tráfego de outros usuários;
endpoints dedicados/NIM são uma alternativa para disponibilidade dedicada.
Este registro tem o usuário como fonte, sem nova consulta autenticada pelo agente.

O usuário não encontrou outros textos. A informação resolve a dúvida
operacional sobre a oferta exibida, mas não confirma retenção, treinamento,
exceções por modelo ou versão dos termos aceitos. Não solicitar repetidamente
os mesmos campos nem bloquear desenvolvimento local por isso. Memórias ficam
locais por padrão; avaliações externas continuam restritas a fixtures fictícias
explicitamente liberadas. Uso com memórias pessoais ou em produção depende de
condições aplicáveis e de uma escolha específica de política.

## Registro operacional da Mist

A [ficha oficial da NVIDIA para o checkpoint Nemotron Super FP8](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8)
identifica a NVIDIA Nemotron Open Model License e distingue os termos de
download dos termos do container NIM. Isso não confirma a variante servida
pelo endpoint nem substitui o contrato da API da conta. A licença pública do
checkpoint não determina, por si, cotas, retenção ou uso em produção da API.

| Item | Estado |
|---|---|
| Endpoint/IDs e parâmetros | Implementados e geração sintética real registrada nos documentos 17 e 18. |
| Oferta e contrato aceitos na conta | Usuário transcreveu FAQ/painel com oferta gratuita para prototipagem em 13/10/2026; nome formal do programa, contrato aceito e versão/data não confirmados. |
| Cota, rate limit e cobrança | Painel transcrito pelo usuário informa até 40 RPM para a maioria dos modelos, sem cobrança por token no nível gratuito; limite pode variar por modelo e tráfego. Não é medição de cota disponível ou capacidade dedicada. Cadência local e pausa após 429 permanecem no documento 24. |
| Retenção, treinamento e exceções por modelo | Não confirmados para a oferta atual; não prometer confidencialidade com base no funcionamento da API. |
| Licenças dos modelos | Verificação específica ainda pendente; distinta da licença de distribuição do código da Mist. |
| Uso neste estágio | Avaliação interna com dados sintéticos; external opt-in, Guarda e auditoria permanecem obrigatórios. |
| Credencial ativa | Chave temporária reutilizada após confirmação explícita do usuário, apenas por entrada oculta; não persistida no ambiente ou no repositório. |

Para completar o registro da conta, consultar suas telas de oferta/limites e o contrato aplicável. O acesso à página pública não substitui a confirmação desses campos. Qualquer mudança para serviço de produção precisa de condições compatíveis com esse uso.

O [controle NVIDIA 0.3.1](24-controle-requisicoes-nvidia.md) registra fontes e limites: mínimo 2,1 segundos entre envios e pausa no processo após 429. Não foi confirmada regra oficial de banimento automático por atingir 40 RPM.

## Avaliação real com entrada oculta

O runner agora aceita chave digitada em terminal interativo, sem salvá-la:

```sh
PYTHONPATH=src python evaluations/run_identity.py --real --ask-api-key \
  --output runtime/identity-real
```

O diretório de saída deve ser novo. O comando envia somente os cenários sintéticos definidos no protocolo, usando FAST e PRIMARY; não executa ferramentas. A entrada oculta é recusada quando o terminal só oferece leitura com eco. Também continua disponível `NVIDIA_API_KEY`, conforme o protocolo. A entrada oculta não aceita termos nem configura novas permissões da conta.

A revisão deste runner passou com 68 testes em Python 3.11.16 e 3.14.7, incluindo verificação de encaminhamento da chave ao runner sem exibição e recusa de fallback com eco. As rodadas reais foram executadas posteriormente; registros de 66/68 testes permanecem evidências históricas. A revisão 0.3.0 tem 75 testes aprovados e nova validação de instalação.

## Estado do P0-A

Concluída a consulta das fontes públicas, mas não a confirmação das condições da conta. A avaliação comportamental real foi executada e revisada, com correções e limitações registradas no documento 23. Código atualizado publicado na branch `mist-p0a-validacao`; sua revisão/integração em main permanece pendente. Não declarar o marco encerrado a partir desta consulta.
