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

Использование:
  python commit_by_date.py
  python commit_by_date.py --repo sandbox_repo
  python commit_by_date.py --repo /absolute/path/to/repo

Параметры:
  --repo PATH  Путь к репозиторию для работы (по умолчанию текущая директория).
               Поддерживает относительные и абсолютные пути. Кроссплатформенно (Windows/Unix).

Ограничения:
- Скрипт не меняет содержимое файлов — только коммитит текущие незакоммиченные изменения.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import date, datetime, time, timedelta
from typing import List, Optional, Sequence, Tuple


def run_git(
    args: Sequence[str],
    check: bool = True,
    env: Optional[dict] = None,
    cwd: Optional[str] = None,
) -> subprocess.CompletedProcess[str]:
    """Запускает git-команду и возвращает результат (кроссплатформенно)."""
    return subprocess.run(
        ["git", *args],
        text=True,
        capture_output=True,
        check=check,
        env=env,
        cwd=cwd,  # Работает на Windows и Unix
    )


def resolve_repo_path(repo_arg: Optional[str]) -> Optional[str]:
    """
    Разрешает путь к репозиторию и проверяет его валидность (кроссплатформенно).
    
    Возвращает нормализованный абсолютный путь к корню git-репозитория.
    Если repo_arg None, возвращает None (будет использована текущая директория).
    """
    if not repo_arg:
        return None
    
    # Нормализуем путь (работает на Windows и Unix)
    if os.path.isabs(repo_arg):
        repo_path = os.path.normpath(repo_arg)  # Нормализует \ и /
    else:
        # Относительно текущей рабочей директории
        repo_path = os.path.abspath(os.path.normpath(repo_arg))
    
    # Проверяем существование
    if not os.path.isdir(repo_path):
        sys.exit(f"Ошибка: директория не найдена: {repo_path}")
    
    # Проверяем, что это git-репозиторий
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=repo_path,  # cwd работает на всех платформах
            text=True,
            capture_output=True,
            check=True,
        )
        actual_repo_root = result.stdout.strip()
        # Нормализуем путь, возвращаемый Git (может содержать / на Windows)
        return os.path.normpath(actual_repo_root)
    except subprocess.CalledProcessError:
        sys.exit(f"Ошибка: {repo_path} не является git-репозиторием")


def ensure_repo_root(repo_path: Optional[str] = None) -> str:
    """Возвращает путь к корню репозитория и прекращает работу при ошибке."""
    if repo_path:
        # Если путь указан, используем его
        return repo_path
    
    # Иначе определяем из текущей директории
    try:
        result = run_git(["rev-parse", "--show-toplevel"])
        repo_root = result.stdout.strip()
        # Нормализуем путь для кроссплатформенности
        return os.path.normpath(repo_root)
    except subprocess.CalledProcessError as exc:
        sys.exit(f"Ошибка: не удалось определить корень репозитория ({exc.stderr.strip()})")


def ensure_clean_index(repo_path: Optional[str] = None) -> None:
    """Проверяет, что индекс пуст (нет подготовленных файлов)."""
    result = run_git(["diff", "--cached", "--name-only"], cwd=repo_path)
    staged = [line for line in result.stdout.splitlines() if line.strip()]
    if staged:
        sys.exit(
            "В индексе уже есть подготовленные файлы. Очистите его перед запуском скрипта, "
            "чтобы случайно не закоммитить лишнее."
        )


def parse_uncommitted_files(repo_path: Optional[str] = None) -> List[str]:
    """
    Возвращает список незакоммиченных файлов (отслеживаемые изменения и новые файлы).

    Используем `git status --porcelain -z`, чтобы корректно обрабатывать пробелы в путях
    и переименования (берем новую сторону для R/C).
    """
    result = run_git(["status", "--porcelain=v1", "-z"], cwd=repo_path)
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


def commit_file_on_date(file_path: str, commit_date: date, repo_path: Optional[str] = None) -> None:
    """Делает коммит указанного файла с фиктивной датой."""
    commit_dt = datetime.combine(commit_date, time(hour=12, minute=0, second=0))
    date_str = commit_dt.strftime("%Y-%m-%d %H:%M:%S")

    env = os.environ.copy()
    env["GIT_AUTHOR_DATE"] = date_str
    env["GIT_COMMITTER_DATE"] = date_str

    # Добавляем только нужный файл
    run_git(["add", "--", file_path], cwd=repo_path)

    # Формируем простое сообщение
    message = f"Auto commit for {file_path}"

    try:
        run_git(["commit", "-m", message], check=True, env=env, cwd=repo_path).check_returncode()
        print(f"✓ {commit_date.isoformat()} — {file_path}")
    except subprocess.CalledProcessError as exc:
        sys.exit(f"Не удалось сделать коммит для {file_path}: {exc.stderr or exc.stdout}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Коммит незакоммиченных файлов по датам в заданном диапазоне."
    )
    parser.add_argument(
        "--repo",
        type=str,
        default=None,
        help="Путь к репозиторию для работы (по умолчанию текущая директория)",
    )
    args = parser.parse_args()
    
    # Разрешаем путь к репозиторию
    repo_path = resolve_repo_path(args.repo)
    repo_root = ensure_repo_root(repo_path)
    print(f"Корень репозитория: {repo_root}")
    ensure_clean_index(repo_path)

    start = read_date("Стартовая дата (YYYY-MM-DD): ")
    end = read_date("Конечная дата (YYYY-MM-DD): ")
    dates = build_dates(start, end)

    files = parse_uncommitted_files(repo_path)
    if not files:
        sys.exit("Незакоммиченные файлы не найдены — делать нечего.")

    plan = build_plan(files, dates)
    confirm_plan(plan)

    for file_path, commit_date in plan:
        commit_file_on_date(file_path, commit_date, repo_path)

    print("\nГотово! Все файлы закоммичены с разными датами.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("\nПрервано пользователем.")

