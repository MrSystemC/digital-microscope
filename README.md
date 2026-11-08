# Микроскоп цифрового пространства v2.0

Универсальный профессиональный инструмент для изучения **цифровой ткани** на молекулярном уровне.  
Аналог физического микроскопа — показывает, из чего состоят цифровые объекты.

Работает в **терминале** и через **веб-интерфейс**. Применим к любому направлению исследования.

## Возможности

- Автоопределение и разбор: JSON, Python (AST + функции/классы/импорты), CSV, HTML, Markdown, XML, YAML, TOML, INI, логи, текст, директории
- Иерархическое дерево молекул
- Графовое представление (Mermaid)
- Статистика по ткани
- Сравнение двух образцов
- Экспорт в JSON
- Современный веб-интерфейс с вкладками (дерево / граф / JSON)
- CLI с подкомандами

## Установка

```bash
pip install -r requirements.txt
```

## Использование

### Терминал

```bash
# Анализ файла
python -m microscope.cli analyze data.json

# Из stdin
cat script.py | python -m microscope.cli analyze -

# Полный JSON
python -m microscope.cli analyze file.py --json

# Mermaid-граф
python -m microscope.cli analyze config.yaml --mermaid

# Сравнение
python -m microscope.cli compare a.json b.json

# Веб-интерфейс
python -m microscope.cli serve
# → http://localhost:8000
```

### Веб

Откройте интерфейс, вставьте текст или загрузите файл. Доступны вкладки «Дерево», «Граф» и «JSON».

## Примеры

Смотрите папку `examples/`.

## Архитектура

- `microscope/core.py` — движок анализа
- `microscope/cli.py` — командная строка
- `microscope/web.py` — веб-интерфейс

Инструмент спроектирован как расширяемый: новые анализаторы добавляются методами `_analyze_<type>`.
