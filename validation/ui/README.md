# Validação da interface local 0.6.0

`python-3.11-v0.6.0.json` e `python-3.14-v0.6.0.json` registram a execução
do **comando instalado**, fora do checkout, com dois processos consecutivos
por ambiente. O runner em `tools/verify_ui.py` usa HTTP diretamente para
verificar a fronteira do servidor; não automatiza o navegador.

Fonte de runtime/testes: 08b749e. A correção de codificação UTF-8 do cliente
do runner foi aplicada depois; seu hash está nos recibos. O wheel e os assets
instalados foram comparados com a fonte, conforme recibo de instalação.

`browser-v0.6.0.json` registra a verificação manual pela automação oficial
do navegador, distinta dos testes Python. Imagens com dados fictícios em
`docs/images/`. Nenhuma credencial, conteúdo pessoal ou chamada NVIDIA foi
usada neste incremento. Portas locais efêmeras e caminhos temporários não
são parte da configuração de produção.

Repetir após instalar o pacote no ambiente desejado:

```sh
.venv/bin/python tools/verify_ui.py --output /tmp/mist-ui-receipt.json
```

O arquivo de saída deve ser novo; os resultados históricos são preservados.
