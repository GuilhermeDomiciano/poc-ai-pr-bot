from contextvars import ContextVar, Token

# Cria uma variavel de contexto para armazenar o request_id, com um valor padrão de "-"
_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")

# Define funções para setar, obter e resetar o request_id no contexto atual
def set_request_id(request_id: str) -> Token[str]:
    return _request_id_ctx.set(request_id)


def get_request_id() -> str:
    return _request_id_ctx.get()


def reset_request_id(token: Token[str]) -> None:
    _request_id_ctx.reset(token)
