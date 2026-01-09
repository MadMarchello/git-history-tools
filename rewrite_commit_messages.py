#!/usr/bin/env python3
"""
Интерактивный переписыватель истории: проходит по всем коммитам и позволяет
изменить их текст. Работает через `git filter-branch` и переписывает историю
ветки, поэтому используйте только если готовы к force-push.

Как работает:
1. Собирает список коммитов (от самых старых к новым) через `git rev-list --reverse HEAD`.
2. По каждому коммиту показывает хэш и текущий текст; предлагает ввести новый.
   - Пустой ввод оставит сообщение без изменений.
3. После подтверждения запускает `git filter-branch --msg-filter ...`, передавая
   таблицу соответствий commit->new_message через переменную окружения.

Требования:
- Чистое рабочее дерево (без незакоммиченных изменений).
- Локальная ветка; после переписывания сделайте force-push, если есть удалённая.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Dict, List, Sequence


def run_git(args: Sequence[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        text=True,
        capture_output=True,
        check=check,
    )


def ensure_clean_worktree() -> None:
    dirty = run_git(["status", "--short"]).stdout.strip()
    if dirty:
        sys.exit("Рабочее дерево грязное. Очистите или закоммитьте изменения перед переписыванием истории.")


def list_commits() -> List[str]:
    result = run_git(["rev-list", "--reverse", "HEAD"])
    commits = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not commits:
        sys.exit("Коммитов не найдено.")
    return commits


def read_commit_message(commit: str) -> str:
    result = run_git(["log", "-1", "--format=%B", commit])
    return result.stdout.strip()


def collect_new_messages(commits: List[str]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    print("Введите новый текст для каждого коммита. Пусто — оставить как есть.\n")
    for commit in commits:
        old_msg = read_commit_message(commit)
        print("=" * 60)
        print(f"{commit}")
        print(f"Текущий текст:\n{old_msg}")
        new_msg = input("\nНовый текст (или Enter чтобы оставить): ").strip()
        if new_msg:
            mapping[commit] = new_msg
    return mapping


def confirm(mapping: Dict[str, str]) -> None:
    if not mapping:
        sys.exit("Новых сообщений нет — выходим.")
    print("\nБудут изменены сообщения для коммитов:")
    for commit, msg in mapping.items():
        print(f"- {commit}: {msg}")
    ans = input("\nПродолжить переписывание истории? Это потребует force-push. [y/N]: ").strip().lower()
    if ans not in {"y", "yes"}:
        sys.exit("Отменено пользователем.")


def rewrite_history(mapping: Dict[str, str]) -> None:
    env = os.environ.copy()
    env["MESSAGE_MAP"] = json.dumps(mapping)

    msg_filter = r"""python3 - <<'PY' "$GIT_COMMIT"
import json, os, sys
mapping = json.loads(os.environ["MESSAGE_MAP"])
commit = sys.argv[1]
old_msg = sys.stdin.read()
sys.stdout.write(mapping.get(commit, old_msg))
PY"""

    # Используем --tag-name-filter cat, чтобы не ломать теги; -- --all можно добавить при необходимости.
    cmd = ["git", "filter-branch", "-f", "--msg-filter", msg_filter, "--tag-name-filter", "cat", "--", "HEAD"]
    print("\nЗапускаю filter-branch... (это может занять время)")
    try:
        subprocess.run(cmd, text=True, check=True, env=env)
    except subprocess.CalledProcessError as exc:
        sys.exit(f"filter-branch завершился с ошибкой: {exc}")
    print("\nГотово. История переписана. Не забудьте сделать force-push при необходимости.")


def main() -> None:
    ensure_clean_worktree()
    commits = list_commits()
    mapping = collect_new_messages(commits)
    confirm(mapping)
    rewrite_history(mapping)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("\nПрервано пользователем.")

