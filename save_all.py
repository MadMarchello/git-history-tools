#!/usr/bin/env python3
"""
Скрипт для быстрого сохранения всех изменений в Git:
    git add --all
    git commit -m "сообщение"

Использование:
    python3 save_all.py -m "Текст коммита"
"""

import argparse
import subprocess
import sys


def run_command(cmd: list[str]) -> None:
    """Выполняет команду и завершает программу при ошибке."""
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при выполнении команды: {' '.join(cmd)}", file=sys.stderr)
        sys.exit(e.returncode)
    except FileNotFoundError:
        print("Команда 'git' не найдена. Убедитесь, что Git установлен и доступен в PATH.", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Добавить все изменения и сделать коммит с заданным сообщением."
    )
    parser.add_argument(
        "-m", "--message",
        required=True,
        help="Сообщение коммита (обязательный параметр)"
    )
    args = parser.parse_args()

    commit_message = args.message

    # Проверяем, что мы находимся внутри Git-репозитория
    try:
        subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            check=True, capture_output=True
        )
    except subprocess.CalledProcessError:
        print("Ошибка: текущая директория не является Git-репозиторием.", file=sys.stderr)
        sys.exit(1)

    # git add --all
    print("Добавляем все изменения...")
    run_command(["git", "add", "--all"])

    # git commit -m "сообщение"
    print(f"Создаём коммит с сообщением: \"{commit_message}\"")
    run_command(["git", "commit", "-m", commit_message])

    print("Готово! Все изменения добавлены и закоммичены.")


if __name__ == "__main__":
    main()
