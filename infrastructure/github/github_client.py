import logging

import requests

from infrastructure.observability.logging_utils import log_event, safe_message


logger = logging.getLogger(__name__)


class GitHubClient:
    def __init__(self, *, token: str, owner: str, repo: str) -> None:
        self.token = token
        self.owner = owner
        self.repo = repo
        self.base = f"https://api.github.com/repos/{self.owner}/{self.repo}"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )

    def get_issue(self, number: int) -> dict[str, object]:
        log_event(logger, logging.INFO, "github.issue.get", issue_number=number)
        response = self.session.get(f"{self.base}/issues/{number}")
        response.raise_for_status()
        return response.json()

    def create_pr(self, head: str, base: str, title: str, body: str) -> dict[str, object]:
        log_event(logger, logging.INFO, "github.pr.create", head=head, base=base, title=title)
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
            safe_error_details = safe_message(error_details)
            log_event(
                logger,
                logging.ERROR,
                "github.pr.create_failed",
                status_code=response.status_code,
                details=safe_error_details,
            )
            raise RuntimeError(
                safe_message(
                    f"GitHub PR creation failed ({response.status_code}): {safe_error_details}"
                )
            )
        return response.json()
