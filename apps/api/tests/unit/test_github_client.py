"""GitHub client unit tests (no network)."""

from eaw.infrastructure.connectors.github_client import GitHubClient


def test_select_indexable_paths_prioritizes_readme() -> None:
    tree = [
        {"type": "blob", "path": "src/app.py", "size": 100},
        {"type": "blob", "path": "node_modules/x.js", "size": 100},
        {"type": "blob", "path": "README.md", "size": 50},
        {"type": "blob", "path": "docs/architecture.md", "size": 80},
        {"type": "blob", "path": "huge.bin", "size": 9999999},
        {"type": "tree", "path": "src"},
    ]
    paths = GitHubClient.select_indexable_paths(tree, max_files=10, max_file_bytes=1000)
    assert "README.md" in paths
    assert "docs/architecture.md" in paths
    assert "src/app.py" in paths
    assert "node_modules/x.js" not in paths
    assert paths[0] in {"README.md", "docs/architecture.md"}


def test_token_required() -> None:
    import pytest
    from eaw.domain.common.errors import ValidationAppError

    with pytest.raises(ValidationAppError):
        GitHubClient("  ")
