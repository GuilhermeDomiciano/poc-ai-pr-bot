from domain.models import ChangeSet
from domain.payload.errors import contract_error
from domain.payload.extractor import extract_first_json_object
from domain.payload.validators import (
    validate_files_map,
    validate_non_empty_string_field,
    validate_required_keys,
)


def parse_payload(text: str) -> ChangeSet:
    # Tenta extrair o primeiro objeto JSON valido dentro do texto bruto da IA.
    # Isso permite tolerar ruido antes/depois do JSON.
    payload_data = extract_first_json_object(text)
    # O contrato exige um objeto JSON na raiz.
    if not isinstance(payload_data, dict):
        raise contract_error("no valid JSON object found in crew output; return JSON only")

    # Garante existencia das chaves obrigatorias do contrato de integracao.
    validate_required_keys(payload_data)

    # Valida mapa de arquivos (tipo, conteudo e politica de path).
    files_map = validate_files_map(payload_data["files"])
    # Valida campos textuais obrigatorios de metadados do git/PR.
    branch = validate_non_empty_string_field(payload_data, "branch")
    commit = validate_non_empty_string_field(payload_data, "commit")
    pr_title = validate_non_empty_string_field(payload_data, "pr_title")
    pr_body = validate_non_empty_string_field(payload_data, "pr_body")

    # Retorna estrutura canonica usada pelo restante do fluxo.
    return ChangeSet(
        files=files_map,
        branch=branch,
        commit=commit,
        pr_title=pr_title,
        pr_body=pr_body,
    )
