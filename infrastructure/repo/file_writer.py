from pathlib import Path


def apply_files(repodir: Path, files_map: dict[str, str]):
    for rel_path, content in files_map.items():
        p = repodir / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
