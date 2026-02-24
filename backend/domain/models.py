from dataclasses import dataclass


@dataclass(frozen=True)
class ChangeSet:
    files: dict[str, str]
    branch: str
    commit: str
    pr_title: str
    pr_body: str
