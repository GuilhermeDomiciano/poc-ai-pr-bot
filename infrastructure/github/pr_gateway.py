from infrastructure.github.github_client import GitHubClient


class PullRequestGateway:
    def __init__(self, client: GitHubClient) -> None:
        self.client = client

    def create_pr(self, head: str, base: str, title: str, body: str) -> dict[str, object]:
        return self.client.create_pr(head=head, base=base, title=title, body=body)
