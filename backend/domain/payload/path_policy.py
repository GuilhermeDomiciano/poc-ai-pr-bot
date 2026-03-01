from pathlib import PurePosixPath

from domain.payload.errors import contract_error


# Escopo permitido para arquivos retornados pela IA.
# Todo path deve comecar com "backend/" ou "frontend/".
ALLOWED_FILE_ROOTS = {"backend", "frontend"}


def validate_file_path(file_path: str) -> None:
    # Impede path vazio (ou composto apenas por espacos).
    if not file_path.strip():
        raise contract_error("file path must be a non-empty string")

    # Obriga separador POSIX ("/"), evitando variacoes de Windows ("\\").
    if "\\" in file_path:
        raise contract_error(f"file path '{file_path}' must use '/' as separator")

    # Bloqueia "~" para evitar caminhos dependentes de home do usuario.
    if file_path.startswith("~"):
        raise contract_error(f"file path '{file_path}' must not start with '~'")

    # Converte para objeto de path POSIX para validacoes consistentes.
    normalized_path = PurePosixPath(file_path)
    # So aceita caminhos relativos ao repositorio (nunca absolutos).
    if normalized_path.is_absolute():
        raise contract_error(f"file path '{file_path}' must be repository-relative, not absolute")

    # Bloqueia path traversal e segmentos invalidos.
    # ".", ".." e segmento vazio nao sao aceitos.
    if any(part in {"", ".", ".."} for part in normalized_path.parts):
        raise contract_error(f"file path '{file_path}' contains invalid path traversal segments")

    # Exige raiz + arquivo (ex.: backend/app.py).
    # Evita aceitar apenas "backend" sem arquivo de destino.
    if len(normalized_path.parts) < 2:
        raise contract_error(
            f"file path '{file_path}' must include a target file under backend/ or frontend/"
        )

    # Garante que a escrita fique restrita ao escopo combinado do monorepo.
    if normalized_path.parts[0] not in ALLOWED_FILE_ROOTS:
        raise contract_error(
            f"file path '{file_path}' must start with 'backend/' or 'frontend/'"
        )
