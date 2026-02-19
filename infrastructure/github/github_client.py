import os

import requests


class GitHubClient:
    def __init__(self):
        self.token = os.environ["GITHUB_TOKEN"]
        self.owner = os.environ["GH_OWNER"]
        self.repo = os.environ["GH_REPO"]
        self.base = f"https://api.github.com/repos/{self.owner}/{self.repo}"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )

    def get_issue(self, number: int):
        response = self.session.get(f"{self.base}/issues/{number}")
        response.raise_for_status()
        return response.json()

    def create_pr(self, head: str, base: str, title: str, body: str):
        payload = {"title": title, "head": head, "base": base, "body": body}
        response = self.session.post(f"{self.base}/pulls", json=payload)
        if response.status_code >= 400:
            error_details = response.text
            try:
                error_payload = response.json()
                api_message = error_payload.get("message", "")
                api_errors = error_payload.get("errors", "")
                error_details = f"{api_message} | errors={api_errors}"
            except ValueError:
                pass
            raise RuntimeError(f"GitHub PR creation failed ({response.status_code}): {error_details}")
        return response.json()
