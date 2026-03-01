from typing import Any

from domain.payload.errors import contract_error
from domain.payload.path_policy import validate_file_path


# Campos obrigatorios do contrato que a IA precisa devolver.
REQUIRED_PAYLOAD_KEYS = {"files", "branch", "commit", "pr_title", "pr_body"}


def validate_required_keys(payload_data: dict[str, Any]) -> None:
    # Calcula quais chaves obrigatorias estao faltando no payload.
    missing_keys = REQUIRED_PAYLOAD_KEYS - payload_data.keys()
    if missing_keys:
        # Erro de contrato com mensagem objetiva para diagnostico rapido.
        raise contract_error(
            "missing required keys: "
            f"{sorted(missing_keys)}; expected keys: files, branch, commit, pr_title, pr_body"
        )


def validate_non_empty_string_field(payload_data: dict[str, Any], field_name: str) -> str:
    # Recupera o valor dinamicamente para campos textuais como branch/commit/pr_title/pr_body.
    value = payload_data.get(field_name)
    # Exige string nao vazia (tipo e conteudo).
    if not isinstance(value, str) or not value.strip():
        raise contract_error(f"field '{field_name}' must be a non-empty string")
    # Retorna valor validado para uso no parser final.
    return value


def validate_files_map(files_value: Any) -> dict[str, str]:
    # O campo "files" precisa ser um objeto JSON no formato {path: content}.
    if not isinstance(files_value, dict):
        raise contract_error("field 'files' must be an object map: {path: content}")

    # Nao permite payload sem alteracoes de arquivo.
    if not files_value:
        raise contract_error("field 'files' must contain at least one file change")

    # Mapa final validado e tipado.
    validated_files: dict[str, str] = {}
    for raw_path, raw_content in files_value.items():
        # Toda chave deve ser path textual.
        if not isinstance(raw_path, str):
            raise contract_error("all file paths in 'files' must be strings")

        # Reusa politica central de seguranca/escopo para caminho.
        validate_file_path(raw_path)

        # Conteudo de arquivo tambem precisa ser textual.
        if not isinstance(raw_content, str):
            raise contract_error(f"file content for '{raw_path}' must be a string")

        # Guarda par path->conteudo ja validado.
        validated_files[raw_path] = raw_content

    return validated_files
