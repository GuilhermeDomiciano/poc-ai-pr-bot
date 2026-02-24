import logging
import shutil
import subprocess
from pathlib import Path
from typing import Sequence

from infrastructure.observability.logging_utils import log_event, safe_message


logger = logging.getLogger(__name__)


def _execute_command(command: Sequence[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True)


def run(command: Sequence[str], cwd: Path | None = None) -> None:
    log_event(logger, logging.INFO, "repo.command.run", command=list(command), cwd=str(cwd) if cwd else None)
    result = _execute_command(command, cwd=cwd)
    if result.returncode != 0:
        stdout = safe_message(result.stdout.strip()) if result.stdout else ""
        stderr = safe_message(result.stderr.strip()) if result.stderr else ""
        if stdout:
            log_event(logger, logging.ERROR, "repo.command.stdout", output=stdout)
        if stderr:
            log_event(logger, logging.ERROR, "repo.command.stderr", output=stderr)
        raise RuntimeError(
            safe_message(
                f"Command failed (exit_code={result.returncode}): {' '.join(command)}"
            )
        )


def run_capture(
    command: Sequence[str],
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    log_event(
        logger,
        logging.INFO,
        "repo.command.run_capture",
        command=list(command),
        cwd=str(cwd) if cwd else None,
    )
    return _execute_command(command, cwd=cwd)


def clone_repo(owner: str, repo: str, repo_dir: Path, *, github_token: str) -> None:
    if repo_dir.exists():
        shutil.rmtree(repo_dir)
    clone_url = f"https://x-access-token:{github_token}@github.com/{owner}/{repo}.git"
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


def git_setup(
    repo_dir: Path,
    *,
    git_author_name: str,
    git_author_email: str,
) -> None:
    run(["git", "config", "user.name", git_author_name], cwd=repo_dir)
    run(["git", "config", "user.email", git_author_email], cwd=repo_dir)
    run(["git", "config", "--local", "credential.helper", ""], cwd=repo_dir)


def remote_branch_exists(branch: str, repo_dir: Path) -> bool:
    command_result = run_capture(["git", "ls-remote", "--exit-code", "--heads", "origin", branch], cwd=repo_dir)
    return command_result.returncode == 0


def publish_changes(repo_dir: Path, branch: str, commit_message: str) -> None:
    run(["git", "checkout", "-b", branch], cwd=repo_dir)
    run(["git", "add", "."], cwd=repo_dir)
    run(["git", "commit", "-m", commit_message], cwd=repo_dir)
    run(["git", "push", "-u", "origin", branch], cwd=repo_dir)
