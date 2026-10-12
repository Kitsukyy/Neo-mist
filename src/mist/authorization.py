from mist.errors import ErrorCode, MistError


class Authorizer:
    def require_tool(self, tool_name: str) -> None:
        # No executor exists. Tool names and model output cannot grant authority.
        raise MistError(ErrorCode.AUTHORIZATION_DENIED)

