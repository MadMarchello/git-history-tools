#!/usr/bin/env python3
"""
Скрипт для полной очистки истории коммитов в Git репозитории.
Удаляет все коммиты, но сохраняет файлы в рабочей директории.
"""

import os
import subprocess
import shutil
from pathlib import Path

def clear_git_history():
    """Очищает всю историю коммитов Git"""
    repo_path = os.getcwd()
    git_dir = os.path.join(repo_path, '.git')
    
    if not os.path.exists(git_dir):
        print("❌ Git репозиторий не найден в текущей директории")
        return False
    
    print("⚠️  ВНИМАНИЕ: Это удалит всю историю коммитов!")
    print(f"Директория: {repo_path}")
    
    # Подтверждение
    response = input("Продолжить? (yes/no): ").strip().lower()
    if response not in ['yes', 'y', 'да', 'д']:
        print("Отменено")
        return False
    
    try:
        # Удаляем .git директорию
        print("\nУдаление .git директории...")
        shutil.rmtree(git_dir)
        print("✓ .git директория удалена")
        
        # Инициализируем новый репозиторий
        print("\nИнициализация нового Git репозитория...")
        subprocess.run(['git', 'init'], check=True, capture_output=True)
        print("✓ Новый репозиторий инициализирован")
        
        # Показываем статус
        result = subprocess.run(['git', 'status'], capture_output=True, text=True)
        print("\nТекущий статус:")
        print(result.stdout)
        
        print("\n✓ История коммитов успешно очищена!")
        print("Все файлы сохранены в рабочей директории")
        return True
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    clear_git_history()



