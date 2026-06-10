"""
Политика Discovery Agent.

КРИТИЧНО: data/projects.csv — только чтение.
Удаление, перезапись и авто-добавление строк ЗАПРЕЩЕНЫ.
Агент только ищет, сравнивает и предлагает.
"""
from __future__ import annotations

FORBIDDEN_ON_CATALOG = frozenset(
    {
        "delete",
        "truncate",
        "drop_rows",
        "overwrite_csv",
        "auto_append",
        "auto_merge",
    }
)


class CatalogProtectedError(PermissionError):
    pass


def assert_catalog_read_only(operation: str) -> None:
    if operation.lower() in FORBIDDEN_ON_CATALOG:
        raise CatalogProtectedError(
            f"Операция «{operation}» запрещена. "
            "data/projects.csv нельзя удалять и менять без вашего явного решения."
        )


def policy_summary() -> dict:
    return {
        "catalog_file": "data/projects.csv",
        "catalog_mode": "read_only",
        "delete_allowed": False,
        "auto_update_allowed": False,
        "agent_role": "discover_and_propose_only",
        "user_action_required_to_add": "manual review or explicit run_revisor.py add --apply",
    }
