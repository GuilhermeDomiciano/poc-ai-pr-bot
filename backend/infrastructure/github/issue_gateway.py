from infrastructure.github.github_client import GitHubClient


class IssueGateway:
    def __init__(self, client: GitHubClient) -> None:
        self.client = client

    def get_issue(self, number: int) -> dict[str, object]:
        return self.client.get_issue(number)
