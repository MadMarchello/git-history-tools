#!/bin/bash
# Скрипт для быстрого просмотра статистики

echo "Генерация статистики из Git..."
python3 get_stats.py

if [ $? -eq 0 ]; then
    echo ""
    echo "Открытие stats.html в браузере..."
    
    # Определяем ОС и открываем браузер
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        open stats.html
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        xdg-open stats.html 2>/dev/null || sensible-browser stats.html 2>/dev/null || firefox stats.html
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        # Windows
        start stats.html
    else
        echo "Пожалуйста, откройте stats.html в браузере вручную"
    fi
else
    echo "Ошибка при генерации статистики"
    exit 1
fi



