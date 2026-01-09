#!/usr/bin/env python3
"""
Меняет сообщение заданного коммита, переписывая историю ветки.

Использование:
    python3 change_commit_message.py <commit_hash> "<new message>"

Требования и предупреждения:
- Рабочее дерево должно быть чистым.
- История переписывается (git filter-branch). После завершения для удалённой ветки
  потребуется force-push: git push --force-with-lease.
- Скрипт трогает только указанный коммит; остальные сообщения остаются без изменений.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Sequence


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


def validate_commit_exists(commit: str) -> None:
    try:
        run_git(["cat-file", "-t", commit], check=True)
    except subprocess.CalledProcessError:
        sys.exit(f"Коммит '{commit}' не найден.")


def rewrite(commit: str, new_message: str) -> None:
    env = os.environ.copy()
    env["TARGET_COMMIT"] = commit
    env["TARGET_MESSAGE"] = new_message

    msg_filter = r"""python3 - <<'PY' "$GIT_COMMIT"
import os, sys
target = os.environ["TARGET_COMMIT"]
new_msg = os.environ["TARGET_MESSAGE"]
commit = sys.argv[1]
old_msg = sys.stdin.read()
if commit == target:
    sys.stdout.write(new_msg)
else:
    sys.stdout.write(old_msg)
PY"""

    cmd = [
        "git",
        "filter-branch",
        "-f",
        "--msg-filter",
        msg_filter,
        "--tag-name-filter",
        "cat",
        "--",
        "HEAD",
    ]

    print(f"Переписываю сообщение для коммита {commit} ...")
    try:
        subprocess.run(cmd, text=True, check=True, env=env)
    except subprocess.CalledProcessError as exc:
        sys.exit(f"filter-branch завершился с ошибкой: {exc}")
    print("Готово. Не забудьте сделать force-push, если требуется.")


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit("Использование: python3 change_commit_message.py <commit_hash> \"<new message>\"")

    commit = sys.argv[1].strip()
    new_message = " ".join(sys.argv[2:]).strip()

    if not new_message:
        sys.exit("Новое сообщение пустое.")

    ensure_clean_worktree()
    validate_commit_exists(commit)
    rewrite(commit, new_message)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("\nПрервано пользователем.")

