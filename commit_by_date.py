#!/usr/bin/env python3
"""
Интерактивный скрипт: берет все незакоммиченные файлы в репозитории и
делает по ним отдельные коммиты на разные даты в заданном диапазоне.

Как работает:
- Запрашивает у пользователя стартовую и конечную дату (включительно) в формате YYYY-MM-DD.
- Проверяет, что в индексе нет уже подготовленных изменений (чтобы не прихватить лишнее).
- Собирает список незакоммиченных файлов (отслеживаемые изменения + новые файлы).
- Если дат больше либо равно числу файлов — ставит по одному коммиту на дату.
- Если дат меньше, чем файлов — равномерно распределяет файлы по доступным датам (несколько коммитов на дату),
  проставляя GIT_AUTHOR_DATE и GIT_COMMITTER_DATE на выбранную дату (время фиксируем на 12:00:00).

Ограничения:
- Если файлов больше, чем дат в диапазоне, скрипт завершится с сообщением об ошибке.
- Скрипт не меняет содержимое файлов — только коммитит текущие незакоммиченные изменения.
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import date, datetime, time, timedelta
from typing import List, Optional, Sequence, Tuple


def run_git(
    args: Sequence[str],
    check: bool = True,
    env: Optional[dict] = None,
) -> subprocess.CompletedProcess[str]:
    """Запускает git-команду и возвращает результат."""
    return subprocess.run(
        ["git", *args],
        text=True,
        capture_output=True,
        check=check,
        env=env,
    )


def ensure_repo_root() -> str:
    """Возвращает путь к корню репозитория и прекращает работу при ошибке."""
    try:
        result = run_git(["rev-parse", "--show-toplevel"])
    except subprocess.CalledProcessError as exc:
        sys.exit(f"Ошибка: не удалось определить корень репозитория ({exc.stderr.strip()})")
    return result.stdout.strip()


def ensure_clean_index() -> None:
    """Проверяет, что индекс пуст (нет подготовленных файлов)."""
    result = run_git(["diff", "--cached", "--name-only"])
    staged = [line for line in result.stdout.splitlines() if line.strip()]
    if staged:
        sys.exit(
            "В индексе уже есть подготовленные файлы. Очистите его перед запуском скрипта, "
            "чтобы случайно не закоммитить лишнее."
        )


def parse_uncommitted_files() -> List[str]:
    """
    Возвращает список незакоммиченных файлов (отслеживаемые изменения и новые файлы).

    Используем `git status --porcelain -z`, чтобы корректно обрабатывать пробелы в путях
    и переименования (берем новую сторону для R/C).
    """
    result = run_git(["status", "--porcelain=v1", "-z"])
    entries = result.stdout.split("\0")

    files: List[str] = []
    i = 0
    while i < len(entries):
        entry = entries[i]
        if not entry:
            i += 1
            continue

        status = entry[:2]
        path = entry[3:]  # пропускаем два символа статуса и пробел

        # Для переименования/копирования Git кладет новый путь в следующую запись
        if status.startswith("R") or status.startswith("C"):
            if i + 1 < len(entries) and entries[i + 1]:
                path = entries[i + 1]
                i += 1  # пропускаем дополнительный путь

        # Игнорируем записи про игнорируемые файлы/директории
        if status.startswith("!"):
            i += 1
            continue

        cleaned = path.strip()
        if cleaned:
            files.append(cleaned)

        i += 1

    # Убираем дубликаты и сортируем для предсказуемости
    return sorted(set(files))


def read_date(prompt: str) -> date:
    """Читает дату у пользователя в формате YYYY-MM-DD."""
    raw = input(prompt).strip()
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        sys.exit(f"Неверный формат даты '{raw}'. Используйте YYYY-MM-DD. ({exc})")


def build_dates(start: date, end: date) -> List[date]:
    """Строит список дат (включительно)."""
    if end < start:
        sys.exit("Конечная дата раньше начальной. Исправьте диапазон.")
    days = (end - start).days + 1
    return [start + timedelta(days=offset) for offset in range(days)]


def build_plan(files: Sequence[str], dates: Sequence[date]) -> List[Tuple[str, date]]:
    """
    Возвращает сопоставление файл -> дата.

    - Если дат >= файлов: берем первые len(files) дат по порядку.
    - Если дат меньше: распределяем файлы по датам максимально равномерно
      (разница в количестве коммитов на дату не превышает 1).
    """
    if not dates:
        sys.exit("Диапазон дат пуст.")

    if len(dates) >= len(files):
        return list(zip(files, dates[: len(files)]))

    total_files = len(files)
    total_dates = len(dates)
    base = total_files // total_dates
    extra = total_files % total_dates  # первые `extra` дат получат на 1 файл больше

    plan: List[Tuple[str, date]] = []
    idx = 0
    for i, commit_date in enumerate(dates):
        quota = base + (1 if i < extra else 0)
        for _ in range(quota):
            plan.append((files[idx], commit_date))
            idx += 1

    return plan


def confirm_plan(pairs: Sequence[Tuple[str, date]]) -> None:
    """Выводит план коммитов и ждет подтверждения."""
    print("\nПланируемые коммиты (1 файл = 1 дата):")
    for path, commit_date in pairs:
        print(f"  {commit_date.isoformat()}  ->  {path}")
    answer = input("\nПродолжить? [y/N]: ").strip().lower()
    if answer not in {"y", "yes"}:
        sys.exit("Операция отменена пользователем.")


def commit_file_on_date(file_path: str, commit_date: date) -> None:
    """Делает коммит указанного файла с фиктивной датой."""
    commit_dt = datetime.combine(commit_date, time(hour=12, minute=0, second=0))
    date_str = commit_dt.strftime("%Y-%m-%d %H:%M:%S")

    env = os.environ.copy()
    env["GIT_AUTHOR_DATE"] = date_str
    env["GIT_COMMITTER_DATE"] = date_str

    # Добавляем только нужный файл
    run_git(["add", "--", file_path])

    # Формируем простое сообщение
    message = f"Auto commit for {file_path}"

    try:
        run_git(["commit", "-m", message], check=True, env=env).check_returncode()
        print(f"✓ {commit_date.isoformat()} — {file_path}")
    except subprocess.CalledProcessError as exc:
        sys.exit(f"Не удалось сделать коммит для {file_path}: {exc.stderr or exc.stdout}")


def main() -> None:
    repo_root = ensure_repo_root()
    print(f"Корень репозитория: {repo_root}")
    ensure_clean_index()

    start = read_date("Стартовая дата (YYYY-MM-DD): ")
    end = read_date("Конечная дата (YYYY-MM-DD): ")
    dates = build_dates(start, end)

    files = parse_uncommitted_files()
    if not files:
        sys.exit("Незакоммиченные файлы не найдены — делать нечего.")

    plan = build_plan(files, dates)
    confirm_plan(plan)

    for file_path, commit_date in plan:
        commit_file_on_date(file_path, commit_date)

    print("\nГотово! Все файлы закоммичены с разными датами.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("\nПрервано пользователем.")

