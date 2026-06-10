"""
Политика безопасности GitHub для Atlas.

По умолчанию ТОЛЬКО чтение. Удаление, push и изменение файлов на GitHub
запрещены и не реализованы в коде.
"""
from __future__ import annotations

FORBIDDEN_OPERATIONS = frozenset(
    {
        "delete",
        "delete_file",
        "delete_branch",
        "push",
        "force_push",
        "create_or_update_file",
        "create_pull_request_merge",
        "truncate",
    }
)


class GitHubReadOnlyError(PermissionError):
    """Попытка деструктивной или записывающей операции."""


def assert_read_only(operation: str, *, user_confirmed: bool = False) -> None:
    op = (operation or "").lower()
    if op in FORBIDDEN_OPERATIONS:
        raise GitHubReadOnlyError(
            f"Операция «{operation}» запрещена. Ничего не удаляется и не меняется на GitHub "
            "без вашего явного отдельного согласия."
        )
    if user_confirmed:
        raise GitHubReadOnlyError(
            "Запись на GitHub в этой версии платформы не реализована — только просмотр и анализ."
        )


def policy_summary() -> dict:
    return {
        "mode": "read_only",
        "deletes_allowed": False,
        "push_allowed": False,
        "note": "Для приватного репозитория задайте GITHUB_TOKEN (только чтение).",
    }
