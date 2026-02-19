import os, re
from pathlib import Path
from dotenv import load_dotenv
from infrastructure.github.github_client import GitHubClient
from infrastructure.ai.crew_runner import run_crew
from domain.payload_parser import parse_payload
from infrastructure.repo.file_writer import apply_files
from infrastructure.repo.operations import (
    clone_repo,
    git_setup,
    remote_branch_exists,
    repo_tree_summary,
    run,
)


load_dotenv()

WORKDIR = Path("/work")
REPODIR = WORKDIR / "repo"

def safe_slug(text: str) -> str:
    normalized_text = text.lower()
    normalized_text = re.sub(r"[^a-z0-9]+", "-", normalized_text).strip("-")
    return normalized_text[:50] or "change"

def main():
    github_client = GitHubClient()
    issue_number = int(os.environ["ISSUE_NUMBER"])
    issue_data = github_client.get_issue(issue_number)

    issue_title = issue_data["title"]
    issue_body = issue_data.get("body") or ""

    repository_owner = os.environ["GH_OWNER"]
    repository_name = os.environ["GH_REPO"]
    github_token = os.environ["GITHUB_TOKEN"]

    clone_repo(repository_owner, repository_name, github_token, REPODIR)
    git_setup(REPODIR)

    repository_tree_summary = repo_tree_summary(REPODIR)

    crew_output_text = run_crew(issue_title, issue_body, repository_tree_summary)

    change_set = parse_payload(crew_output_text)

    files_map = change_set.files
    branch_name = change_set.branch
    commit_message = change_set.commit
    pull_request_title = change_set.pr_title
    pull_request_body = change_set.pr_body

    apply_files(REPODIR, files_map)

    run(["git", "checkout", "-b", branch_name], cwd=REPODIR)
    run(["git", "add", "."], cwd=REPODIR)
    run(["git", "commit", "-m", commit_message], cwd=REPODIR)
    run(["git", "push", "-u", "origin", branch_name], cwd=REPODIR)

    base_branch = os.getenv("GH_BASE_BRANCH", "main")
    if not remote_branch_exists(base_branch, REPODIR):
        print(
            f"Base branch '{base_branch}' does not exist on remote. "
            "Skipping PR creation (common for empty/new repositories)."
        )
        print(f"Branch pushed successfully: {branch_name}")
        return

    pull_request = github_client.create_pr(
        head=branch_name,
        base=base_branch,
        title=pull_request_title,
        body=pull_request_body
    )
    print("PR created:", pull_request["html_url"])

if __name__ == "__main__":
    main()
