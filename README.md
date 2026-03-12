# Краулер для выкачки HTML-страниц

Скрипт скачивает HTML-страницы из заранее подготовленного списка URL, сохраняет **каждую страницу в отдельный файл** и формирует `index.txt`.

## Что делает

- читает ссылки из `urls.txt`
- скачивает только HTML-страницы
- проверяет, что на странице достаточно текста
- проверяет язык текста (`ru` по умолчанию)
- сохраняет страницу **вместе с HTML-разметкой**
- создаёт `index.txt` вида:

```text
1    001_example.com_ab12cd34.html    https://example.com/page1
2    002_example.com_ef56gh78.html    https://example.com/page2
```

## Структура

```text
crawler_assignment/
├── crawler.py
├── validate_urls.py
├── requirements.txt
├── urls_example.txt
└── README.md
```

После запуска появятся:

```text
crawler_assignment/
├── dump/
│   ├── 001_....html
│   ├── 002_....html
│   └── ...
└── index.txt
```

## Установка

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

## Подготовка списка ссылок

Создай файл `urls.txt` и положи туда ссылки, по одной в строке.

Требования к ссылкам:
- только страницы с текстом
- один и тот же язык для всех страниц
- не использовать ссылки на `.js`, `.css`, картинки, pdf и т.д.
- лучше сразу подготовить 120–150 ссылок, чтобы после фильтрации гарантированно осталось 100

## Проверка списка перед выкачкой

```bash
python validate_urls.py --urls urls.txt --lang ru
```

## Основной запуск

```bash
python crawler.py --urls urls.txt --out dump --index index.txt --lang ru --limit 100
```

## Полезные параметры

```bash
python crawler.py \
  --urls urls.txt \
  --out dump \
  --index index.txt \
  --lang ru \
  --min-text-chars 800 \
  --delay 0.5 \
  --timeout 20 \
  --limit 100
```

## Что сдавать

1. Репозиторий на GitHub с кодом.
2. Архив папки `dump` с HTML-файлами.
3. Файл `index.txt`.

## Как оформить репозиторий

Рекомендуемая последовательность:

```bash
git init
git add .
git commit -m "Initial crawler implementation"
# создать пустой репозиторий на GitHub
git remote add origin <URL_ТВОЕГО_РЕПОЗИТОРИЯ>
git branch -M main
git push -u origin main
```

## Как сделать архив с выкачкой

### Windows PowerShell

```powershell
Compress-Archive -Path .\dump\* -DestinationPath .\dump.zip -Force
```

### Linux / macOS

```bash
zip -r dump.zip dump/
```

## Важное замечание

Скрипт **не очищает HTML от разметки**, потому что по условию нужно сохранять страницы целиком, вместе с тегами.


## Дополнительный вариант: обход сайта по глубине

### 1) Готовый список из 122 ссылок
```bash
python crawler.py --urls urls_ru_122.txt --out dump --index index.txt --lang ru --limit 100
```

### 2) Обход ru.wikipedia.org по глубине
```bash
python crawler_depth.py   --seeds seed_urls_ru.txt   --out dump_depth   --index index_depth.txt   --limit 100   --max-depth 2   --lang ru   --allowed-domains ru.wikipedia.org
```

### Что добавлено
- `urls_ru_122.txt` — готовый файл со 122 русскоязычными HTML-страницами
- `seed_urls_ru.txt` — стартовые страницы для обхода по глубине
- `crawler_depth.py` — BFS-краулер по ссылкам внутри разрешённых доменов

### Что лучше сдавать
Для надёжной сдачи обычно лучше использовать **готовый список URL** и обычный `crawler.py`, потому что результат будет воспроизводимым.
