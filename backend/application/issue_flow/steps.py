from domain.models import ChangeSet

from application.issue_flow.contracts import (
    IssueFlowConfig,
    IssueFlowDependencies,
    IssueFlowResult,
)


def load_issue_context(
    config: IssueFlowConfig,
    dependencies: IssueFlowDependencies,
) -> tuple[str, str]:
    # Busca titulo/corpo da issue no provider (GitHub) e normaliza body vazio.
    issue_data = dependencies.get_issue(config.issue_number)
    issue_title = issue_data["title"]
    issue_body = issue_data.get("body") or ""
    return issue_title, issue_body


def prepare_repository(
    config: IssueFlowConfig,
    dependencies: IssueFlowDependencies,
) -> None:
    # Clona o repositorio alvo no diretório de trabalho e aplica setup basico do git.
    dependencies.clone_repo(
        config.repository_owner,
        config.repository_name,
        config.repository_directory,
    )
    dependencies.git_setup(config.repository_directory)


def generate_crew_output(
    issue_title: str,
    issue_body: str,
    config: IssueFlowConfig,
    dependencies: IssueFlowDependencies,
) -> str:
    # Resume a arvore de arquivos para contexto da IA e executa o crew multiagente.
    repository_tree_summary = dependencies.repo_tree_summary(config.repository_directory)
    return dependencies.run_crew(issue_title, issue_body, repository_tree_summary)


def parse_change_set(
    crew_output_text: str,
    dependencies: IssueFlowDependencies,
) -> ChangeSet:
    # Converte texto da IA para ChangeSet validado e publica observabilidade do pacote gerado.
    change_set = dependencies.parse_payload(crew_output_text)
    dependencies.observe_change_set(change_set)
    return change_set


def build_dry_run_result(change_set: ChangeSet) -> IssueFlowResult:
    # Resposta padrao para execucao sem escrita em repo remoto (sem push/PR).
    return IssueFlowResult(
        status="dry_run",
        message="Dry run completed with no repository or PR changes",
        branch=change_set.branch,
        commit=change_set.commit,
        pr_title=change_set.pr_title,
        pr_url=None,
    )


def build_success_result(
    change_set: ChangeSet,
    *,
    message: str,
    pr_url: str | None,
) -> IssueFlowResult:
    # Resposta de sucesso compartilhada por finais com e sem PR.
    return IssueFlowResult(
        status="success",
        branch=change_set.branch,
        commit=change_set.commit,
        pr_title=change_set.pr_title,
        pr_url=pr_url,
        message=message,
    )


def publish_repository_changes(
    config: IssueFlowConfig,
    dependencies: IssueFlowDependencies,
    change_set: ChangeSet,
) -> None:
    # Aplica arquivos no repositorio clonado e publica commit/branch no remoto.
    dependencies.apply_files(config.repository_directory, change_set.files)
    dependencies.publish_changes(config.repository_directory, change_set.branch, change_set.commit)


def build_pr_or_branch_result(
    config: IssueFlowConfig,
    dependencies: IssueFlowDependencies,
    change_set: ChangeSet,
) -> IssueFlowResult:
    # Se a base nao existir no remoto, finaliza sem PR (somente branch publicada).
    if not dependencies.remote_branch_exists(config.base_branch, config.repository_directory):
        return build_success_result(
            change_set,
            message=f"Branch pushed successfully: {change_set.branch}",
            pr_url=None,
        )

    # Se a base existir, cria PR apontando para base_branch configurada.
    pull_request = dependencies.create_pr(
        head=change_set.branch,
        base=config.base_branch,
        title=change_set.pr_title,
        body=change_set.pr_body,
    )
    return build_success_result(
        change_set,
        message="PR created successfully",
        pr_url=pull_request["html_url"],
    )
