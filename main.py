import os, re
from pathlib import Path
from dotenv import load_dotenv
from github_client import GitHubClient
from crew_flow import build_crew
from domain.payload_parser import parse_payload
from infrastructure.repo.operations import (
    clone_repo,
    git_setup,
    remote_branch_exists,
    repo_tree_summary,
    run,
)
from infrastructure.repo.file_writer import apply_files

load_dotenv()

WORKDIR = Path("/work")
REPODIR = WORKDIR / "repo"

def safe_slug(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:50] or "change"

def main():
    gh = GitHubClient()
    issue_number = int(os.environ["ISSUE_NUMBER"])
    issue = gh.get_issue(issue_number)

    title = issue["title"]
    body = issue.get("body") or ""

    owner = os.environ["GH_OWNER"]
    repo = os.environ["GH_REPO"]
    token = os.environ["GITHUB_TOKEN"]

    clone_repo(owner, repo, token, REPODIR)
    git_setup(REPODIR)

    tree = repo_tree_summary(REPODIR)

    crew = build_crew(title, body, tree)
    result = crew.kickoff()

    # CrewAI result: output must be standardized as simple JSON.
    # To keep this simple, write issues asking for a "JSON-only response".
    text = str(result)

    payload = parse_payload(text)

    files_map = payload.files
    branch = payload.branch
    commit_msg = payload.commit
    pr_title = payload.pr_title
    pr_body = payload.pr_body

    apply_files(REPODIR, files_map)

    run(["git", "checkout", "-b", branch], cwd=REPODIR)
    run(["git", "add", "."], cwd=REPODIR)
    run(["git", "commit", "-m", commit_msg], cwd=REPODIR)
    run(["git", "push", "-u", "origin", branch], cwd=REPODIR)

    base_branch = os.getenv("GH_BASE_BRANCH", "main")
    if not remote_branch_exists(base_branch, REPODIR):
        print(
            f"Base branch '{base_branch}' does not exist on remote. "
            "Skipping PR creation (common for empty/new repositories)."
        )
        print(f"Branch pushed successfully: {branch}")
        return

    pr = gh.create_pr(
        head=branch,
        base=base_branch,
        title=pr_title,
        body=pr_body
    )
    print("PR created:", pr["html_url"])

if __name__ == "__main__":
    main()
