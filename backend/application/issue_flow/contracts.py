from dataclasses import dataclass
from pathlib import Path
from typing import Callable, TypedDict

from application.ports import AIProvider
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
    ai_provider: AIProvider
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
