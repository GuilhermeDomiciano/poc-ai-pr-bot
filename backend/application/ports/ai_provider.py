from typing import Protocol


class AIProvider(Protocol):
    def generate_changes(
        self,
        issue_title: str,
        issue_body: str,
        repo_tree: str,
    ) -> str:
        """Generate raw text output that will be parsed into a ChangeSet."""
