import os
import shutil
import subprocess
from pathlib import Path


def run(cmd, cwd=None):
    print(">>", " ".join(cmd))
    subprocess.check_call(cmd, cwd=cwd)


def run_capture(cmd, cwd=None):
    print(">>", " ".join(cmd))
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def clone_repo(owner: str, repo: str, token: str, repodir: Path):
    if repodir.exists():
        shutil.rmtree(repodir)
    url = f"https://x-access-token:{token}@github.com/{owner}/{repo}.git"
    run(["git", "clone", url, str(repodir)])


def repo_tree_summary(repodir: Path) -> str:
    paths = []
    for p in repodir.rglob("*"):
        if p.is_file() and p.stat().st_size < 20000:
            rel = p.relative_to(repodir)
            if any(part.startswith(".git") for part in rel.parts):
                continue
            paths.append(str(rel))
    return "\n".join(paths[:200])


def git_setup(repodir: Path):
    run(["git", "config", "user.name", os.getenv("GIT_AUTHOR_NAME", "AI Bot")], cwd=repodir)
    run(["git", "config", "user.email", os.getenv("GIT_AUTHOR_EMAIL", "ai-bot@example.com")], cwd=repodir)
    run(["git", "config", "--local", "credential.helper", ""], cwd=repodir)


def remote_branch_exists(branch: str, repodir: Path) -> bool:
    r = run_capture(["git", "ls-remote", "--exit-code", "--heads", "origin", branch], cwd=repodir)
    return r.returncode == 0
