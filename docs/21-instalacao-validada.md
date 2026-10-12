# Instalação e compatibilidade verificadas

Estado: pacote local construído e validado em 12/10/2026. Não publicado no PyPI. Código e evidências publicados na branch de revisão `mist-p0a-validacao` do GitHub.

## Resultado

| Ambiente Linux x86_64 | Pacote instalado em ambiente isolado | Suíte | Comando `mist` fora do repositório |
|---|---|---|---|
| Python 3.11.16 | Aprovado | 75 testes aprovados | Aprovado |
| Python 3.14.7 | Aprovado | 75 testes aprovados | Aprovado |

A instalação foi feita sem modo editável, seguida por uma instalação do arquivo wheel exportado. Os testes importaram a distribuição de `site-packages` em modo isolado do Python. O teste de fluxo offline bloqueou a criação de sockets, carregou as configurações empacotadas, gerou uma resposta explicitamente simulada e verificou auditoria approved/completed. O comando de terminal também foi executado em uma pasta temporária, fora do repositório.

A validação da instalação não usou segredo nem rede; a avaliação real dos modelos foi executada separadamente. A validação de instalação não mede qualidade conversacional.

O arquivo atual `neo_mist-0.3.0-py3-none-any.whl` tem 19.832 bytes e inclui 20 arquivos de execução/configuração, todos comparados byte a byte com o código atual, mais metadados de distribuição. Não inclui resultados, conversas, testes ou credenciais. Seu SHA-256 é:

```text
8429d54e912da3ef9f80ca7c6b349587384e5e91a7e85660f1ac154f973a2f11
```

## Instalar a partir do repositório

No diretório do projeto, usando Python 3.11 ou superior:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -c constraints-tested.txt .
mist --message 'Olá, Mist'
```

A instalação pode baixar dependências. O comando acima mantém o FakeModel offline; envio à NVIDIA exige configuração e habilitação explícitas.

`constraints-tested.txt` registra as versões de execução verificadas. É opcional e não representa um lock completo de ferramentas de build ou uma garantia de compilação idêntica. Pydantic continua fixado no projeto. Os comandos apresentados pressupõem Linux ou shell compatível.

Para instalar o arquivo wheel entregue, substitua o último passo de instalação pelo caminho local dele:

```sh
python -m pip install -c constraints-tested.txt /caminho/neo_mist-0.3.0-py3-none-any.whl
```

## Reproduzir a verificação

Depois de instalar o pacote, execute a partir do checkout:

```sh
python tools/verify_installation.py --output runtime/installation-check.json
```

Crie `runtime/` antes da execução. O arquivo de saída deve ser novo: o verificador não sobrescreve evidências. O script executa a suíte, inspeciona a origem do pacote, testa o comando instalado fora do checkout e registra versões e hashes dos arquivos de código/testes. Dependências de análise do benchmark não são necessárias para essa suíte.

Evidências da distribuição instalada a partir do wheel:

- [Python 3.11](../validation/installation/python-3.11-v0.3.0.json).
- [Python 3.14](../validation/installation/python-3.14-v0.3.0.json).
- [Identificação do wheel](../validation/installation/wheel-v0.3.0.json).

As evidências anteriores `python-3.11.json`, `python-3.14.json`, os dois arquivos `*-wheel.json` e `wheel.json` preservam a instalação histórica de 0.2.0 com 66 testes. Não foram sobrescritas. Os registros atuais identificam a revisão `d9277d3`; os módulos e testes não mudaram durante a verificação. Os 20 arquivos de execução/configuração do wheel atual foram comparados byte a byte com `src/mist`.

## Limites e pendências

Esta entrega verifica o limite inferior declarado e a versão 3.14 disponível no ambiente. Python 3.12/3.13, Windows e macOS não foram testados. Não ampliar a conclusão para toda combinação de versão/plataforma nem para instalação sem acesso às dependências.

A pendência de instalação do P0-A foi atendida para os dois ambientes Linux acima. As rodadas comportamentais reais e correções estão no documento 23. Permanecem pendentes as condições de acesso/dados/cotas da conta NVIDIA e a revisão/integração da branch no GitHub. O pacote 0.3.0 não foi publicado em um registro de distribuição.

## Revisão 0.3.1 — controle de requisições NVIDIA

Wheel não editável 0.3.1 instalado nos ambientes Linux/Python 3.11.16 e 3.14.7. Em cada um, os 84 testes passaram importando o pacote instalado em modo isolado, com CLI fora do checkout e smoke offline com rede proibida. Recibos: `validation/installation/python-3.11-v0.3.1.json` e `python-3.14-v0.3.1.json`. A revisão de código registrada nos recibos é `12bab44`; os hashes registram fontes e testes usados.

O wheel tem 20.358 bytes, SHA256 `3caddbda3bbbc8a63abc6480a5eaa18c372af530932f3e474b9d7179b102451c`. Seus 20 arquivos de runtime/configuração foram comparados com o código fonte sem diferenças; recibo `wheel-v0.3.1.json`. O pacote não inclui chave, resultados ou histórico. Nenhuma chamada real nesta revisão. Os recibos anteriores permanecem históricos e não validam mudanças posteriores.

O [documento 24](24-controle-requisicoes-nvidia.md) descreve cadência compartilhada no processo, pausa após 429 e limites da implementação.
