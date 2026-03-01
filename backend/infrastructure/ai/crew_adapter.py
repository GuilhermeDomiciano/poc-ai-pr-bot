from application.ports import AIProvider
from infrastructure.ai.crew_runner import run_crew


class CrewAIProvider(AIProvider):
    def generate_changes(
        self,
        issue_title: str,
        issue_body: str,
        repo_tree: str,
    ) -> str:
        return run_crew(issue_title, issue_body, repo_tree)
