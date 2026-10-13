# Fluxo de projetos no pacote instalado — 0.5.0

`tools/verify_projects.py` usa somente um projeto e duas tarefas fictícias.
Em cada versão de Python, quatro processos isolados novos executam duas sessões
CLI e duas leituras de verificação, fora do checkout e com criação de sockets
bloqueada. Cadastro/tarefas são criados, uma tarefa é marcada concluída, recebe
prazo e o projeto é arquivado/reaberto. Leituras seguintes conferem IDs estáveis,
estado/prazo/fontes/progresso de 50%, local_only, permissões e arquivo 0600.
Nenhuma geração acontece; o arquivo de auditoria de geração não é criado.
Bancos temporários são removidos ao fim. Recibos preservam saídas fictícias,
hashes e os gabaritos; não medem qualidade de modelo, latência ou produção.

Os dois recibos apontam para runtime do commit ebba477, com hashes de módulos e
runner. A distribuição instalada é 0.5.0, importada de site-packages. Os 166 testes
completos e a CLI do pacote também foram verificados em validation/installation.
Históricos anteriores não foram sobrescritos. Não houve chave ou envio NVIDIA.
