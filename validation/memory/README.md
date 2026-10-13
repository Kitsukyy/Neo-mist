# Sondagem lexical sintética de memória 0.4.0

13/10/2026. Gerada por tools/verify_memory.py usando o wheel instalado em Python3.11.16 e3.14.7/Linux. Dez mil itens, cem consultas por termos únicos e verificações adicionais de escopo/consulta ausente. Os relatórios preservam gabaritos, retornos, duração de cada consulta e hashes de fonte/runner. Todos os casos definidos passaram nos dois ambientes.

As duas sondagens foram iniciadas em paralelo no mesmo host. Conexão aquecida; cache, contenção e filesystem temporário não controlados. Não usar suas latências para comparar Python ou prometer desempenho em produção. Não são avaliação de busca semântica, conversa livre ou qualidade de LLM. A precisão registrada usa o número de itens efetivamente retornados; recall usa gabaritos não vazios e até cinco resultados. Casos de vazio por privacidade são reportados separadamente.
