from dataclasses import dataclass
from pathlib import Path
from typing import Callable, TypedDict

from domain.models import ChangeSet


class IssueData(TypedDict, total=False):
    title: str
    body: str | None


class PullRequestData(TypedDict):
    html_url: str


def _noop_observe_change_set(_: ChangeSet) -> None:
    return None


def _noop_observe_step(_: str, __: str, ___: str | None = None) -> None:
    return None


@dataclass(frozen=True)
class IssueFlowConfig:
    issue_number: int
    repository_owner: str
    repository_name: str
    base_branch: str
    repository_directory: Path
    dry_run: bool = False


@dataclass(frozen=True)
class IssueFlowDependencies:
    get_issue: Callable[[int], IssueData]
    create_pr: Callable[..., PullRequestData]
    clone_repo: Callable[[str, str, Path], None]
    git_setup: Callable[[Path], None]
    repo_tree_summary: Callable[[Path], str]
    run_crew: Callable[[str, str, str], str]
    parse_payload: Callable[[str], ChangeSet]
    apply_files: Callable[[Path, dict[str, str]], None]
    publish_changes: Callable[[Path, str, str], None]
    remote_branch_exists: Callable[[str, Path], bool]
    observe_change_set: Callable[[ChangeSet], None] = _noop_observe_change_set
    observe_step: Callable[[str, str, str | None], None] = _noop_observe_step


@dataclass(frozen=True)
class IssueFlowResult:
    status: str
    message: str
    branch: str | None = None
    commit: str | None = None
    pr_title: str | None = None
    pr_url: str | None = None
    error: str | None = None


def _load_issue_context(config: IssueFlowConfig, dependencies: IssueFlowDependencies) -> tuple[str, str]:
    issue_data = dependencies.get_issue(config.issue_number)
    issue_title = issue_data["title"]
    issue_body = issue_data.get("body") or ""
    return issue_title, issue_body


def _prepare_repository(config: IssueFlowConfig, dependencies: IssueFlowDependencies) -> None:
    dependencies.clone_repo(
        config.repository_owner,
        config.repository_name,
        config.repository_directory,
    )
    dependencies.git_setup(config.repository_directory)


def _generate_crew_output(
    issue_title: str,
    issue_body: str,
    config: IssueFlowConfig,
    dependencies: IssueFlowDependencies,
) -> str:
    repository_tree_summary = dependencies.repo_tree_summary(config.repository_directory)
    return dependencies.run_crew(issue_title, issue_body, repository_tree_summary)


def _parse_change_set(
    crew_output_text: str,
    dependencies: IssueFlowDependencies,
) -> ChangeSet:
    change_set = dependencies.parse_payload(crew_output_text)
    dependencies.observe_change_set(change_set)
    return change_set


def _build_dry_run_result(change_set: ChangeSet) -> IssueFlowResult:
    return IssueFlowResult(
        status="dry_run",
        message="Dry run completed with no repository or PR changes",
        branch=change_set.branch,
        commit=change_set.commit,
        pr_title=change_set.pr_title,
        pr_url=None,
    )


def _build_success_result(
    change_set: ChangeSet,
    *,
    message: str,
    pr_url: str | None,
) -> IssueFlowResult:
    return IssueFlowResult(
        status="success",
        branch=change_set.branch,
        commit=change_set.commit,
        pr_title=change_set.pr_title,
        pr_url=pr_url,
        message=message,
    )


def _publish_repository_changes(
    config: IssueFlowConfig,
    dependencies: IssueFlowDependencies,
    change_set: ChangeSet,
) -> None:
    dependencies.apply_files(config.repository_directory, change_set.files)
    dependencies.publish_changes(config.repository_directory, change_set.branch, change_set.commit)


def _build_pr_or_branch_result(
    config: IssueFlowConfig,
    dependencies: IssueFlowDependencies,
    change_set: ChangeSet,
) -> IssueFlowResult:
    if not dependencies.remote_branch_exists(config.base_branch, config.repository_directory):
        return _build_success_result(
            change_set,
            message=f"Branch pushed successfully: {change_set.branch}",
            pr_url=None,
        )

    pull_request = dependencies.create_pr(
        head=change_set.branch,
        base=config.base_branch,
        title=change_set.pr_title,
        body=change_set.pr_body,
    )
    return _build_success_result(
        change_set,
        message="PR created successfully",
        pr_url=pull_request["html_url"],
    )


def run_issue_flow(
    config: IssueFlowConfig,
    dependencies: IssueFlowDependencies,
    *,
    raise_on_error: bool = True,
) -> IssueFlowResult:
    try:
        dependencies.observe_step("load_issue", "start")
        issue_title, issue_body = _load_issue_context(config, dependencies)
        dependencies.observe_step("load_issue", "success")

        dependencies.observe_step("prepare_repo", "start")
        _prepare_repository(config, dependencies)
        dependencies.observe_step("prepare_repo", "success")

        dependencies.observe_step("run_crew", "start")
        crew_output_text = _generate_crew_output(issue_title, issue_body, config, dependencies)
        dependencies.observe_step("run_crew", "success")

        dependencies.observe_step("validate_payload", "start")
        change_set = _parse_change_set(crew_output_text, dependencies)
        dependencies.observe_step(
            "validate_payload",
            "success",
            detail=f"files_count={len(change_set.files)}",
        )

        if config.dry_run:
            dependencies.observe_step(
                "publish_branch",
                "success",
                detail="skipped (dry_run=true)",
            )
            dependencies.observe_step("finalize", "success", detail="dry_run completed")
            return _build_dry_run_result(change_set)

        dependencies.observe_step("publish_branch", "start")
        _publish_repository_changes(config, dependencies, change_set)
        dependencies.observe_step("publish_branch", "success", detail=change_set.branch)

        dependencies.observe_step("finalize", "start")
        result = _build_pr_or_branch_result(config, dependencies, change_set)
        dependencies.observe_step("finalize", "success", detail=result.message)
        return result
    except Exception as error:
        dependencies.observe_step("finalize", "error", detail=str(error))
        if raise_on_error:
            raise
        return IssueFlowResult(
            status="error",
            message="Issue flow execution failed",
            error=str(error),
        )
