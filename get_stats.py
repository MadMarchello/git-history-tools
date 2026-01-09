#!/usr/bin/env python3
"""
Скрипт для получения статистики коммитов из Git репозитория.
Генерирует HTML файл с встроенными данными для визуализации.
"""

import subprocess
import json
from datetime import datetime, timedelta
from collections import defaultdict
import os

def get_commit_stats():
    """Получает статистику коммитов из Git"""
    # Получаем все коммиты с датами
    result = subprocess.run(
        ['git', 'log', '--format=%ai', '--date=short'],
        capture_output=True,
        text=True,
        check=False
    )
    
    if result.returncode != 0:
        print("Ошибка: Git репозиторий не найден или нет коммитов")
        return {}
    
    # Подсчитываем коммиты по дням
    commits_by_date = defaultdict(int)
    
    for line in result.stdout.strip().split('\n'):
        if line:
            # Парсим дату (формат: 2025-01-01 12:34:56 +0700)
            date_str = line.split()[0]
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d').date()
                commits_by_date[str(date)] += 1
            except ValueError:
                continue
    
    # Находим диапазон дат
    if not commits_by_date:
        return {}
    
    dates = sorted(commits_by_date.keys())
    start_date = datetime.strptime(dates[0], '%Y-%m-%d').date()
    end_date = datetime.strptime(dates[-1], '%Y-%m-%d').date()
    
    # Создаем полный список дат с количеством коммитов
    stats = {}
    current = start_date
    while current <= end_date:
        date_str = str(current)
        stats[date_str] = commits_by_date.get(date_str, 0)
        current += timedelta(days=1)
    
    # Вычисляем общую статистику
    total_commits = sum(commits_by_date.values())
    max_commits = max(commits_by_date.values()) if commits_by_date else 0
    
    return {
        'stats': stats,
        'total_commits': total_commits,
        'max_commits': max_commits,
        'start_date': str(start_date),
        'end_date': str(end_date),
        'days_with_commits': len([d for d in stats.values() if d > 0]),
        'total_days': len(stats)
    }


def generate_html_with_data(stats):
    """Генерирует HTML файл с встроенными данными"""
    # Читаем шаблон HTML
    template_path = 'stats.html'
    if not os.path.exists(template_path):
        print(f"❌ Файл {template_path} не найден")
        return False
    
    with open(template_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Встраиваем данные в JavaScript
    stats_json = json.dumps(stats, ensure_ascii=False)
    
    # Заменяем функцию loadStats на встроенные данные
    old_load_function = """        // Загружаем данные
        async function loadStats() {
            try {
                const response = await fetch('stats.json');
                if (!response.ok) {
                    throw new Error('Файл stats.json не найден. Запустите: python3 get_stats.py');
                }
                statsData = await response.json();
                renderStats();
            } catch (error) {
                document.getElementById('loading').style.display = 'none';
                document.getElementById('error').style.display = 'block';
                document.getElementById('error').textContent = error.message;
            }
        }"""
    
    new_load_function = f"""        // Загружаем встроенные данные
        function loadStats() {{
            try {{
                statsData = {stats_json};
                renderStats();
            }} catch (error) {{
                document.getElementById('loading').style.display = 'none';
                document.getElementById('error').style.display = 'block';
                document.getElementById('error').textContent = error.message;
            }}
        }}"""
    
    html_content = html_content.replace(old_load_function, new_load_function)
    
    # Сохраняем обновленный HTML
    output_path = 'stats.html'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return True


if __name__ == '__main__':
    stats = get_commit_stats()
    
    if stats:
        # Сохраняем в JSON файл (для совместимости)
        with open('stats.json', 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        
        # Генерируем HTML с встроенными данными
        if generate_html_with_data(stats):
            print(f"✓ Статистика встроена в stats.html")
        else:
            print(f"⚠️  Не удалось обновить stats.html, но stats.json создан")
        
        print(f"  Всего коммитов: {stats['total_commits']}")
        print(f"  Дней с коммитами: {stats['days_with_commits']}")
        print(f"  Максимум коммитов в день: {stats['max_commits']}")
    else:
        print("❌ Не удалось получить статистику")

