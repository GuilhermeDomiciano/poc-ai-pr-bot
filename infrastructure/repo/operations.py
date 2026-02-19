import os
import shutil
import subprocess
from pathlib import Path


def run(command, cwd=None):
    print(">>", " ".join(command))
    subprocess.check_call(command, cwd=cwd)


def run_capture(command, cwd=None):
    print(">>", " ".join(command))
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True)


def clone_repo(owner: str, repo: str, token: str, repo_dir: Path):
    if repo_dir.exists():
        shutil.rmtree(repo_dir)
    clone_url = f"https://x-access-token:{token}@github.com/{owner}/{repo}.git"
    run(["git", "clone", clone_url, str(repo_dir)])


def repo_tree_summary(repo_dir: Path) -> str:
    file_paths = []
    for file_path in repo_dir.rglob("*"):
        if file_path.is_file() and file_path.stat().st_size < 20000:
            relative_path = file_path.relative_to(repo_dir)
            if any(part.startswith(".git") for part in relative_path.parts):
                continue
            file_paths.append(str(relative_path))
    return "\n".join(file_paths[:200])


def git_setup(repo_dir: Path):
    run(["git", "config", "user.name", os.getenv("GIT_AUTHOR_NAME", "AI Bot")], cwd=repo_dir)
    run(["git", "config", "user.email", os.getenv("GIT_AUTHOR_EMAIL", "ai-bot@example.com")], cwd=repo_dir)
    run(["git", "config", "--local", "credential.helper", ""], cwd=repo_dir)


def remote_branch_exists(branch: str, repo_dir: Path) -> bool:
    command_result = run_capture(["git", "ls-remote", "--exit-code", "--heads", "origin", branch], cwd=repo_dir)
    return command_result.returncode == 0
