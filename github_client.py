import os
import requests

class GitHubClient:
    def __init__(self):
        self.token = os.environ["GITHUB_TOKEN"]
        self.owner = os.environ["GH_OWNER"]
        self.repo = os.environ["GH_REPO"]
        self.base = f"https://api.github.com/repos/{self.owner}/{self.repo}"
        self.s = requests.Session()
        self.s.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })

    def get_issue(self, number: int):
        r = self.s.get(f"{self.base}/issues/{number}")
        r.raise_for_status()
        return r.json()

    def create_pr(self, head: str, base: str, title: str, body: str):
        payload = {"title": title, "head": head, "base": base, "body": body}
        r = self.s.post(f"{self.base}/pulls", json=payload)
        if r.status_code >= 400:
            detail = r.text
            try:
                data = r.json()
                msg = data.get("message", "")
                errs = data.get("errors", "")
                detail = f"{msg} | errors={errs}"
            except ValueError:
                pass
            raise RuntimeError(f"GitHub PR creation failed ({r.status_code}): {detail}")
        return r.json()
