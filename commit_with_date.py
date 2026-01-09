#!/usr/bin/env python3
"""
Утилита, которая делает реальный git-коммит с указанной датой.

Использование:
  python commit_with_date.py 2024-12-31 -m "fix: final touches" -a
  python commit_with_date.py 2024-12-31T10:15:00 --files path/to/file1 path/to/file2

Особенности:
- Принимает дату в формате YYYY-MM-DD или YYYY-MM-DDTHH:MM[:SS].
- Устанавливает GIT_AUTHOR_DATE и GIT_COMMITTER_DATE на указанное время.
- Может предварительно проиндексировать конкретные файлы (--files) или всё сразу (-a/--all).
- Если изменений в индексе нет и не указан --allow-empty, завершится без коммита.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime
from typing import Iterable, Optional, Sequence


def run_git(
    args: Sequence[str],
    *,
    env: Optional[dict] = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Запускает git с переданными аргументами."""
    return subprocess.run(
        ["git", *args],
        text=True,
        capture_output=True,
        check=check,
        env=env,
    )


def ensure_repo_root() -> str:
    """Проверяет, что выполняемся внутри репозитория и возвращает его корень."""
    try:
        result = run_git(["rev-parse", "--show-toplevel"])
    except subprocess.CalledProcessError as exc:
        sys.exit(f"Не удалось определить корень репозитория: {exc.stderr.strip()}")
    return result.stdout.strip()


def parse_commit_datetime(raw: str) -> datetime:
    """Парсит дату/дату-время ISO 8601."""
    try:
        return datetime.fromisoformat(raw)
    except ValueError as exc:
        sys.exit(f"Неверный формат даты '{raw}'. Ожидается YYYY-MM-DD или YYYY-MM-DDTHH:MM[:SS]. ({exc})")


def stage_files(files: Iterable[str]) -> None:
    """Добавляет в индекс указанные файлы."""
    try:
        run_git(["add", "--", *files])
    except subprocess.CalledProcessError as exc:
        sys.exit(f"Не удалось добавить файлы: {exc.stderr.strip() or exc.stdout.strip()}")


def stage_all() -> None:
    """Добавляет все изменения (включая новые файлы)."""
    try:
        run_git(["add", "-A"])
    except subprocess.CalledProcessError as exc:
        sys.exit(f"Не удалось подготовить изменения: {exc.stderr.strip() or exc.stdout.strip()}")


def has_staged_changes() -> bool:
    """Проверяет, есть ли подготовленные изменения."""
    result = run_git(["diff", "--cached", "--quiet"], check=False)
    return result.returncode != 0


def commit_with_date(message: str, commit_dt: datetime, allow_empty: bool) -> None:
    """Делает коммит с указанной датой."""
    date_str = commit_dt.strftime("%Y-%m-%d %H:%M:%S")
    env = os.environ.copy()
    env["GIT_AUTHOR_DATE"] = date_str
    env["GIT_COMMITTER_DATE"] = date_str

    cmd = ["commit", "-m", message]
    if allow_empty:
        cmd.append("--allow-empty")

    try:
        result = run_git(cmd, env=env, check=False)
    except subprocess.SubprocessError as exc:
        sys.exit(f"Ошибка при выполнении git commit: {exc}")

    if result.returncode != 0:
        sys.exit(result.stderr.strip() or result.stdout.strip() or "git commit завершился с ошибкой")

    print(f"Готово: коммит создан с датой {date_str}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Сделать git-коммит с заданной датой.")
    parser.add_argument(
        "date",
        help="Дата коммита в формате YYYY-MM-DD или YYYY-MM-DDTHH:MM[:SS]",
    )
    parser.add_argument(
        "-m",
        "--message",
        default=None,
        help="Сообщение коммита. По умолчанию: 'Commit on <date>'.",
    )
    parser.add_argument(
        "-f",
        "--files",
        nargs="+",
        help="Список файлов, которые нужно проиндексировать перед коммитом.",
    )
    parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Добавить все изменения (эквивалент git add -A).",
    )
    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help="Разрешить пустой коммит, даже если изменений нет.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    repo_root = ensure_repo_root()
    print(f"Репозиторий: {repo_root}")

    if args.files and args.all:
        sys.exit("Нельзя использовать одновременно --files и --all.")

    if args.files:
        stage_files(args.files)
    elif args.all:
        stage_all()
    else:
        print("Файлы не добавляются автоматически. Будут использованы уже подготовленные изменения.")

    if not has_staged_changes() and not args.allow_empty:
        sys.exit("В индексе нет изменений. Добавьте файлы или используйте --allow-empty.")

    commit_dt = parse_commit_datetime(args.date)
    message = args.message or f"Commit on {commit_dt.date()}"
    commit_with_date(message, commit_dt, allow_empty=args.allow_empty)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("\nПрервано пользователем.")


