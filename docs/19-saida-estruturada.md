# Saída estruturada: implementação e limites

Estado: implementada e verificada localmente em 12/10/2026. Esta extensão aplica a ideia de declarar a estrutura da resposta usada no benchmark. Não altera as evidências nem reproduz exatamente o prompt de v3.

## Comportamento

A aplicação aceita um contrato opcional por interação. O Core acrescenta nomes e tipos ao texto de sistema, inclui esse texto no orçamento de contexto e vincula o contrato ao envelope aprovado pela Guarda. O contrato não contém respostas esperadas. O Gateway valida o JSON antes de registrar conclusão e antes de o Core atualizar o histórico.

Todos os campos são obrigatórios. Campos extras, chaves duplicadas, `null`, Markdown e texto fora do objeto são rejeitados. Tipos não são convertidos: `true` não é inteiro, e `42.0` não atende a `integer`. `number` aceita inteiros e decimais finitos. Uma falha retorna `INVALID_RESPONSE`, registra apenas metadados e mantém o histórico anterior. Não há correção, nova tentativa ou fallback automático.

O contrato é imutável, aceita de 1 a 32 campos, nomes de até 64 caracteres (`[A-Za-z][A-Za-z0-9_]*`) e tipos `string`, `integer`, `number`, `boolean` ou `array`. Arrays precisam de `items` com um tipo escalar e têm no máximo 256 elementos. Objetos aninhados, arrays aninhados, campos opcionais, valores esperados e JSON Schema arbitrário não estão disponíveis. O arquivo de contrato tem limite de 8 KiB; a resposta mantém o limite de 32.000 caracteres.

A validação comprova estrutura e tipos, não veracidade, qualidade ou correção dos valores. O provedor continua recebendo mensagens comuns; não se pressupõe suporte nativo a JSON Schema. Conversas sem contrato mantêm saída livre. O FakeModel continua sendo uma simulação textual e não produz respostas para contratos; nesse caso seu texto será rejeitado.

## Uso no terminal

O arquivo [answer.json](../examples/output/answer.json) declara um inteiro e uma explicação textual. A opção exige `--message` e vale somente para essa chamada:

```sh
mist --config-dir examples/nvidia --allow-external --ask-api-key \
  --output-contract examples/output/answer.json \
  --message 'Quanto é 6 vezes 7? Responda answer e explanation.'
```

O comando realiza envio externo ao destino configurado. A saída da CLI conserva o prefixo de apresentação; integrações devem usar `response.text` pela API Python para obter o JSON. O contrato é carregado e validado antes de pedir a chave ou criar a aplicação. Erros de arquivo não exibem seu conteúdo.

## Uso programático

```python
import json
from mist.output import OutputContract, OutputField

contract = OutputContract(fields=(OutputField(name="answer", type="integer"),))
response = app.handle("Quanto é 6 vezes 7?", output_contract=contract)
answer = json.loads(response.text)["answer"]
```

`app` é uma aplicação configurada com o provedor desejado. A classificação de privacidade da chamada permanece aplicável ao contrato e à resposta; conteúdo local-only continua bloqueado para provedores externos.

## Evidência e próximo marco

Foram aprovados **57 testes** em Python 3.14.7, incluindo 10 testes novos de contrato. O transporte NVIDIA simulado verificou os modelos FAST e PRIMARY selecionados, o raciocínio habilitado em FAST, o teto de 2.048 tokens, a passagem do contrato, o bloqueio de respostas inadequadas e a preservação do histórico. Nenhuma chamada real ou credencial real foi usada nesta etapa.

Ainda falta executar a avaliação ampla de comportamento e identidade para encerrar o P0-A, registrar as condições aplicáveis da conta NVIDIA e concluir os critérios de aceitação pertinentes. Critérios de fallback são condicionais: não existe fallback implementado. Memória persistente pertence ao P0-B. O código desta entrega está na cópia local; publicação no GitHub continua pendente.
