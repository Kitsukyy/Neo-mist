from enum import StrEnum


class ErrorCode(StrEnum):
    CONFIGURATION = "CONFIGURATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    UNKNOWN_MODEL = "UNKNOWN_MODEL"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    GUARD_BLOCKED = "GUARD_BLOCKED"
    GUARD_FAILURE = "GUARD_FAILURE"
    AUDIT_FAILURE = "AUDIT_FAILURE"
    AUTHORIZATION_DENIED = "AUTHORIZATION_DENIED"
    PROVIDER_FAILURE = "PROVIDER_FAILURE"
    PROVIDER_AUTH = "PROVIDER_AUTH"
    PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
    RATE_LIMIT = "RATE_LIMIT"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    EXTERNAL_DISABLED = "EXTERNAL_DISABLED"
    MEMORY_UNAVAILABLE = "MEMORY_UNAVAILABLE"
    MEMORY_INVALID = "MEMORY_INVALID"
    MEMORY_NOT_FOUND = "MEMORY_NOT_FOUND"
    PROJECT_UNAVAILABLE = "PROJECT_UNAVAILABLE"
    PROJECT_INVALID = "PROJECT_INVALID"
    PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
    PROJECT_ARCHIVED = "PROJECT_ARCHIVED"


MESSAGES = {
    ErrorCode.PROJECT_UNAVAILABLE: "Catálogo local de projetos indisponível. Confira o armazenamento; a operação não foi concluída.",
    ErrorCode.PROJECT_INVALID: "Operação de projeto inválida. Confira identificador, conteúdo, campos e limites.",
    ErrorCode.PROJECT_NOT_FOUND: "Projeto ou tarefa ausente ou fora do projeto informado.",
    ErrorCode.PROJECT_ARCHIVED: "Projeto arquivado. Reabra-o antes de selecionar ou atualizar tarefas.",
    ErrorCode.MEMORY_UNAVAILABLE: "Memória local indisponível ou ocupada. Nenhum envio foi iniciado; confira o armazenamento.",
    ErrorCode.MEMORY_INVALID: "Operação de memória inválida. Confira o conteúdo, os campos e o escopo.",
    ErrorCode.MEMORY_NOT_FOUND: "Memória ausente, excluída ou fora do escopo atual.",
    ErrorCode.CONFIGURATION: "Configuração inválida. Confira os arquivos, campos e referências.",
    ErrorCode.INVALID_INPUT: "Entrada inválida ou maior que o orçamento de contexto.",
    ErrorCode.UNKNOWN_MODEL: "Modelo ou provedor indisponível na configuração.",
    ErrorCode.INVALID_RESPONSE: "O provedor devolveu uma resposta inválida.",
    ErrorCode.GUARD_BLOCKED: "Envio bloqueado pela política de privacidade.",
    ErrorCode.GUARD_FAILURE: "Não foi possível avaliar o envio. Nenhuma chamada foi realizada.",
    ErrorCode.AUDIT_FAILURE: "Auditoria indisponível. Geração suspensa; reinicie após corrigir o registro.",
    ErrorCode.AUTHORIZATION_DENIED: "Execução de ferramentas desabilitada: autonomia nível zero.",
    ErrorCode.PROVIDER_FAILURE: "Falha no provedor. A solicitação não foi concluída.",
    ErrorCode.PROVIDER_AUTH: "Credencial ausente, inválida ou sem acesso ao provedor.",
    ErrorCode.PROVIDER_TIMEOUT: "O provedor excedeu o tempo de espera. Não houve nova tentativa automática.",
    ErrorCode.RATE_LIMIT: "Limite do provedor atingido. Envios NVIDIA pausados neste processo; sem nova tentativa automática. Aguarde e confira o serviço antes de iniciar outra sessão.",
    ErrorCode.PROVIDER_UNAVAILABLE: "Modelo ou serviço externo indisponível. Confira a configuração.",
    ErrorCode.EXTERNAL_DISABLED: "Envio externo desabilitado. Use --allow-external somente para a configuração desejada.",
}


class MistError(Exception):
    """Only predefined messages are safe to display or audit."""

    def __init__(self, code: ErrorCode):
        self.code = code
        super().__init__(MESSAGES[code])
