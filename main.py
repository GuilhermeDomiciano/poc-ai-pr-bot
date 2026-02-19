import os, re, subprocess, shutil
from pathlib import Path
from dotenv import load_dotenv
from github_client import GitHubClient
from crew_flow import build_crew
from domain.payload_parser import parse_payload

load_dotenv()

WORKDIR = Path("/work")
REPODIR = WORKDIR / "repo"

def run(cmd, cwd=None):
    print(">>", " ".join(cmd))
    subprocess.check_call(cmd, cwd=cwd)

def run_capture(cmd, cwd=None):
    print(">>", " ".join(cmd))
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)

def safe_slug(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:50] or "change"

def clone_repo(owner, repo, token):
    if REPODIR.exists():
        shutil.rmtree(REPODIR)
    url = f"https://x-access-token:{token}@github.com/{owner}/{repo}.git"
    run(["git", "clone", url, str(REPODIR)])

def repo_tree_summary():
    # Short summary for the AI (avoid sending the entire repo)
    paths = []
    for p in REPODIR.rglob("*"):
        if p.is_file() and p.stat().st_size < 20000:
            rel = p.relative_to(REPODIR)
            if any(part.startswith(".git") for part in rel.parts): 
                continue
            paths.append(str(rel))
    return "\n".join(paths[:200])

def apply_files(files_map):
    for rel_path, content in files_map.items():
        p = REPODIR / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

def git_setup():
    run(["git", "config", "user.name", os.getenv("GIT_AUTHOR_NAME", "AI Bot")], cwd=REPODIR)
    run(["git", "config", "user.email", os.getenv("GIT_AUTHOR_EMAIL", "ai-bot@example.com")], cwd=REPODIR)
    # Avoid failures/noise when global config references GitHub CLI helpers not installed in runtime.
    run(["git", "config", "--local", "credential.helper", ""], cwd=REPODIR)

def remote_branch_exists(branch: str) -> bool:
    r = run_capture(["git", "ls-remote", "--exit-code", "--heads", "origin", branch], cwd=REPODIR)
    return r.returncode == 0

def main():
    gh = GitHubClient()
    issue_number = int(os.environ["ISSUE_NUMBER"])
    issue = gh.get_issue(issue_number)

    title = issue["title"]
    body = issue.get("body") or ""

    owner = os.environ["GH_OWNER"]
    repo = os.environ["GH_REPO"]
    token = os.environ["GITHUB_TOKEN"]

    clone_repo(owner, repo, token)
    git_setup()

    tree = repo_tree_summary()

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

    apply_files(files_map)

    run(["git", "checkout", "-b", branch], cwd=REPODIR)
    run(["git", "add", "."], cwd=REPODIR)
    run(["git", "commit", "-m", commit_msg], cwd=REPODIR)
    run(["git", "push", "-u", "origin", branch], cwd=REPODIR)

    base_branch = os.getenv("GH_BASE_BRANCH", "main")
    if not remote_branch_exists(base_branch):
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
