#!/usr/bin/env python3
"""
Скрипт для генерации фиктивных коммитов на весь 2025 год.
Создает 2-3 коммита в день с правильными датами для улучшения статистики GitHub.
"""

import os
import subprocess
import random
from datetime import datetime, timedelta

# Настройки
START_DATE = datetime(2025, 1, 1)
END_DATE = datetime(2025, 12, 31)

# Настройки коммитов по дням недели
# Выходные (суббота, воскресенье): больше коммитов
WEEKEND_COMMITS_MIN = 3
WEEKEND_COMMITS_MAX = 5

# Рабочие дни (пн-пт): меньше коммитов
WEEKDAY_COMMITS_MIN = 1
WEEKDAY_COMMITS_MAX = 3

# Вероятность пропуска дней
WEEKEND_SKIP_CHANCE = 0.15  # 15% шанс пропустить выходной
WEEKDAY_SKIP_DAYS_PER_WEEK = (1, 2)  # 1-2 дня без коммитов в рабочей неделе

# Сообщения коммитов
COMMIT_MESSAGES = [
    "Update configuration",
    "Fix minor bugs",
    "Refactor code",
    "Add new features",
    "Update documentation",
    "Improve performance",
    "Code cleanup",
    "Add tests",
    "Update dependencies",
    "Fix typos",
    "Optimize code",
    "Add comments",
    "Update README",
    "Fix formatting",
    "Add utility functions",
    "Update config files",
    "Improve error handling",
    "Add logging",
    "Update scripts",
    "Code review fixes",
    "Add new module",
    "Update API",
    "Fix security issues",
    "Add validation",
    "Update styles",
    "Improve UI",
    "Add examples",
    "Update translations",
    "Fix memory leak",
    "Add caching",
]

# Типы файлов для создания/изменения
FILE_TYPES = {
    'python': {
        'ext': '.py',
        'templates': [
            'def {name}():\n    """{desc}"""\n    pass\n',
            'class {name}:\n    """{desc}"""\n    def __init__(self):\n        self.value = None\n',
            'import os\nimport sys\n\n# {desc}\n',
        ]
    },
    'javascript': {
        'ext': '.js',
        'templates': [
            'function {name}() {{\n    // {desc}\n    return null;\n}}\n',
            'const {name} = () => {{\n    // {desc}\n}};\n',
            '// {desc}\nmodule.exports = {{}};\n',
        ]
    },
    'markdown': {
        'ext': '.md',
        'templates': [
            '# {name}\n\n{desc}\n',
            '## {name}\n\n{desc}\n\n## Details\n\nSome information here.\n',
        ]
    },
    'json': {
        'ext': '.json',
        'templates': [
            '{{\n    "name": "{name}",\n    "description": "{desc}",\n    "version": "1.0.0"\n}}\n',
        ]
    },
    'yaml': {
        'ext': '.yml',
        'templates': [
            'name: {name}\ndescription: {desc}\nversion: 1.0.0\n',
        ]
    },
    'text': {
        'ext': '.txt',
        'templates': [
            '{name}\n{desc}\n',
        ]
    }
}

# Список файлов для работы
FILES_TO_MANAGE = []


def generate_file_content(file_type, name, desc):
    """Генерирует содержимое файла"""
    if file_type not in FILE_TYPES:
        file_type = 'text'
    
    templates = FILE_TYPES[file_type]['templates']
    template = random.choice(templates)
    return template.format(name=name, desc=desc)


def create_or_modify_file(file_path, file_type='text'):
    """Создает или изменяет файл"""
    name = os.path.basename(file_path).replace(FILE_TYPES[file_type]['ext'], '')
    desc = random.choice(['Utility function', 'Helper class', 'Configuration', 'Documentation', 'Test file'])
    
    if os.path.exists(file_path):
        # Модифицируем существующий файл
        with open(file_path, 'a') as f:
            f.write(f'\n# Updated: {datetime.now().isoformat()}\n')
    else:
        # Создаем новый файл
        content = generate_file_content(file_type, name, desc)
        os.makedirs(os.path.dirname(file_path) if os.path.dirname(file_path) else '.', exist_ok=True)
        with open(file_path, 'w') as f:
            f.write(content)
    
    return file_path


def get_random_file():
    """Возвращает случайный файл для изменения"""
    if not FILES_TO_MANAGE:
        return None
    
    # 70% шанс изменить существующий файл, 30% создать новый
    if random.random() < 0.7 and FILES_TO_MANAGE:
        return random.choice(FILES_TO_MANAGE)
    else:
        # Создаем новый файл
        dirs = ['src', 'docs', 'config', 'scripts']
        dir_name = random.choice(dirs)
        file_types = list(FILE_TYPES.keys())
        file_type = random.choice(file_types)
        ext = FILE_TYPES[file_type]['ext']
        
        file_num = len([f for f in FILES_TO_MANAGE if f.startswith(dir_name)]) + 1
        file_name = f"{random.choice(['util', 'helper', 'main', 'config', 'test', 'api', 'service'])}{file_num}{ext}"
        file_path = os.path.join(dir_name, file_name)
        FILES_TO_MANAGE.append(file_path)
        return file_path


def make_commit(date, message):
    """Создает коммит с указанной датой"""
    # Форматируем дату для Git
    date_str = date.strftime('%Y-%m-%d %H:%M:%S')
    
    # Устанавливаем переменные окружения для даты
    env = os.environ.copy()
    env['GIT_AUTHOR_DATE'] = date_str
    env['GIT_COMMITTER_DATE'] = date_str
    
    # Добавляем файлы
    subprocess.run(['git', 'add', '-A'], check=True, capture_output=True)
    
    # Создаем коммит
    result = subprocess.run(
        ['git', 'commit', '-m', message],
        env=env,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0 and 'nothing to commit' not in result.stdout:
        print(f"Warning: {result.stderr}")
    elif result.returncode == 0:
        print(f"✓ {date.strftime('%Y-%m-%d %H:%M')}: {message}")


def should_skip_day(current_date, weekday_skip_days):
    """Определяет, нужно ли пропустить день"""
    weekday = current_date.weekday()  # 0=понедельник, 6=воскресенье
    
    # Выходные (суббота=5, воскресенье=6)
    if weekday >= 5:
        # Иногда пропускаем выходные
        return random.random() < WEEKEND_SKIP_CHANCE
    
    # Рабочие дни (пн-пт)
    # Проверяем, не является ли этот день одним из пропущенных в неделе
    return current_date in weekday_skip_days


def get_commits_for_day(weekday):
    """Возвращает количество коммитов для дня недели"""
    # Выходные (суббота=5, воскресенье=6)
    if weekday >= 5:
        return random.randint(WEEKEND_COMMITS_MIN, WEEKEND_COMMITS_MAX)
    # Рабочие дни (пн-пт)
    else:
        return random.randint(WEEKDAY_COMMITS_MIN, WEEKDAY_COMMITS_MAX)


def get_weekday_skip_days_for_week(week_start_date):
    """Определяет рабочие дни для пропуска в текущей неделе"""
    skip_days = []
    num_skip_days = random.randint(*WEEKDAY_SKIP_DAYS_PER_WEEK)
    
    # Получаем все рабочие дни недели (пн-пт)
    weekdays = []
    for i in range(5):  # Понедельник-пятница
        day = week_start_date + timedelta(days=i)
        weekdays.append(day)
    
    # Случайно выбираем дни для пропуска
    if weekdays:
        skip_days = random.sample(weekdays, min(num_skip_days, len(weekdays)))
    
    return skip_days


def generate_commits():
    """Генерирует коммиты на весь период"""
    current_date = START_DATE
    total_commits = 0
    skipped_days = 0
    
    # Инициализируем базовые файлы
    print("Инициализация базовых файлов...")
    base_files = [
        ('README.md', 'markdown'),
        ('src/main.py', 'python'),
        ('config/settings.json', 'json'),
        ('scripts/run.sh', 'text'),
    ]
    
    for file_path, file_type in base_files:
        create_or_modify_file(file_path, file_type)
        FILES_TO_MANAGE.append(file_path)
    
    # Первый коммит
    make_commit(START_DATE, "Initial commit")
    total_commits += 1
    
    print(f"\nГенерация коммитов с {START_DATE.date()} по {END_DATE.date()}...")
    print("Логика: выходные - больше коммитов (3-5), рабочие дни - меньше (1-3), иногда пропуски")
    print("-" * 60)
    
    # Находим начало первой недели (понедельник)
    week_start = START_DATE
    while week_start.weekday() != 0:  # 0 = понедельник
        week_start -= timedelta(days=1)
    
    # Инициализируем пропущенные дни для первой недели
    weekday_skip_days = get_weekday_skip_days_for_week(week_start)
    
    # Генерируем коммиты для каждого дня
    while current_date <= END_DATE:
        # Если началась новая неделя, определяем дни для пропуска
        if current_date.weekday() == 0:  # Понедельник
            week_start = current_date
            weekday_skip_days = get_weekday_skip_days_for_week(week_start)
        
        # Проверяем, нужно ли пропустить день
        if should_skip_day(current_date, weekday_skip_days):
            skipped_days += 1
            weekday_name = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'][current_date.weekday()]
            print(f"⊘ {current_date.strftime('%Y-%m-%d')} ({weekday_name}): пропущен")
        else:
            # Определяем количество коммитов для дня
            weekday = current_date.weekday()
            num_commits = get_commits_for_day(weekday)
            
            # Генерируем коммиты в течение дня
            for i in range(num_commits):
                # Случайное время в течение дня
                # Выходные: более широкий диапазон (8:00-23:00)
                # Рабочие дни: стандартный диапазон (9:00-20:00)
                if weekday >= 5:  # Выходные
                    hour = random.randint(8, 23)
                else:  # Рабочие дни
                    hour = random.randint(9, 20)
                
                minute = random.randint(0, 59)
                commit_time = current_date.replace(hour=hour, minute=minute, second=random.randint(0, 59))
                
                # Выбираем файл для изменения
                file_path = get_random_file()
                if file_path:
                    file_type = 'text'
                    for ft, info in FILE_TYPES.items():
                        if file_path.endswith(info['ext']):
                            file_type = ft
                            break
                    create_or_modify_file(file_path, file_type)
                
                # Выбираем сообщение коммита
                message = random.choice(COMMIT_MESSAGES)
                
                # Создаем коммит
                make_commit(commit_time, message)
                total_commits += 1
        
        # Переходим к следующему дню
        current_date += timedelta(days=1)
        
        # Прогресс каждые 30 дней
        if (current_date - START_DATE).days % 30 == 0:
            print(f"\nПрогресс: {(current_date - START_DATE).days} дней обработано, {total_commits} коммитов создано, {skipped_days} дней пропущено")
    
    print("-" * 60)
    print(f"\n✓ Готово! Создано {total_commits} коммитов")
    print(f"Пропущено дней: {skipped_days}")
    print(f"Период: {START_DATE.date()} - {END_DATE.date()}")


if __name__ == '__main__':
    try:
        generate_commits()
    except KeyboardInterrupt:
        print("\n\nПрервано пользователем")
    except Exception as e:
        print(f"\nОшибка: {e}")
        import traceback
        traceback.print_exc()

