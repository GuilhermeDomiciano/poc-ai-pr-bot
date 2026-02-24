from pathlib import Path


def apply_files(repo_dir: Path, files_map: dict[str, str]) -> None:
    for rel_path, content in files_map.items():
        target_file_path = repo_dir / rel_path
        target_file_path.parent.mkdir(parents=True, exist_ok=True)
        target_file_path.write_text(content, encoding="utf-8")
