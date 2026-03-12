# Краулер для выкачки HTML-страниц

Скрипт скачивает HTML-страницы из заранее подготовленного списка URL, сохраняет **каждую страницу в отдельный файл** и формирует `index.txt`.

## Что делает

* читает ссылки из `urls.txt`
* скачивает только HTML-страницы
* проверяет, что на странице достаточно текста
* проверяет язык текста (`ru` по умолчанию)
* сохраняет страницу **вместе с HTML-разметкой**
* создаёт `index.txt` вида:

```text
1    001\_example.com\_ab12cd34.html    https://example.com/page1
2    002\_example.com\_ef56gh78.html    https://example.com/page2
```

## Структура

```text
crawler\_assignment/
├── crawler.py
├── validate\_urls.py
├── requirements.txt
├── urls\_example.txt
└── README.md
```

После запуска появятся:

```text
crawler\_assignment/
├── dump/
│   ├── 001\_....html
│   ├── 002\_....html
│   └── ...
└── index.txt
```

## Установка

```bash
python -m venv .venv
# Windows
.venv\\Scripts\\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

## Подготовка списка ссылок

Создай файл `urls.txt` и положи туда ссылки, по одной в строке.

Требования к ссылкам:

* только страницы с текстом
* один и тот же язык для всех страниц
* не использовать ссылки на `.js`, `.css`, картинки, pdf и т.д.
* лучше сразу подготовить 120–150 ссылок, чтобы после фильтрации гарантированно осталось 100

## Проверка списка перед выкачкой

```bash
python validate\_urls.py --urls urls.txt --lang ru
```

## Основной запуск

```bash
python crawler.py --urls urls.txt --out dump --index index.txt --lang ru --limit 100
```

## Полезные параметры

```bash
python crawler.py \\
  --urls urls.txt \\
  --out dump \\
  --index index.txt \\
  --lang ru \\
  --min-text-chars 800 \\
  --delay 0.5 \\
  --timeout 20 \\
  --limit 100
```

## \## Построение инвертированного индекса

## 

## ```bash

python build\_index.py --dump dump --mapping index.txt --lang ru --json-out inverted\_index.json --txt-out inverted\_index.txt

python boolean\_search.py --index inverted\_index.json --query "Цезарь AND NOT Клеопатра"
---

## python boolean\_search.py --index inverted\_index.json --query "(Клеопатра AND Цезарь) OR Помпей"

