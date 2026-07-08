from pathlib import Path


def find_repo_root(start_path: Path) -> Path | None:
    current_path = start_path.resolve()
    while current_path != current_path.parent:  # Avoid infinite loop at the root
        if (current_path / ".root").exists():
            return current_path
        current_path = current_path.parent
    return None
