# Wiki-Explorer

Wiki-Explorer — учебная CLI-утилита для получения и анализа информации из Wikipedia через командную строку.

На текущем этапе реализованы команды:

- `search` — поиск статей по ключевым словам;
- `info` — базовая информация о статье;
- `links` — внутренние ссылки из статьи;
- `graph` — построение простого графа ссылок статьи;
- `categories` — получение категорий статьи;
- `pageviews` — статистика просмотров статьи;
- `random` — получение случайной статьи Wikipedia;
- `images` — получение списка изображений статьи и их скачивание.

Подробное логирование доступно двумя способами:

```bash
python main.py --verbose <command> ...
python main.py <command> ... --verbose
```

В обычном режиме логи не выводятся и не мешают пользовательскому выводу. В режиме `--verbose` используется стандартный модуль `logging`.

## Команда `search`

Команда выполняет поиск статей Wikipedia по ключевым словам через MediaWiki Action API и выводит результаты в таблице.

Команда поддерживает:

- обязательный аргумент `query` — поисковый запрос;
- опцию `--lang` — язык Wikipedia, по умолчанию `ru`;
- опцию `--limit` — максимальное количество результатов, по умолчанию `10`;
- опцию `--sort` — сортировка: `relevance` или `last_edit`;
- опцию `--verbose` — включает подробное логирование через стандартный модуль `logging`.

Обычный поиск:

```bash
python main.py search "искусственный интеллект" --limit 20 --lang ru
```

Поиск в английской Wikipedia:

```bash
python main.py search "Python programming" --limit 10 --lang en
```

Сортировка по релевантности:

```bash
python main.py search "машинное обучение" --sort relevance --limit 10 --lang ru
```

Сортировка по дате последнего изменения:

```bash
python main.py search "Python" --sort last_edit --limit 10 --lang en
```

Запуск с подробным логированием:

```bash
python main.py search "Python" --sort last_edit --limit 10 --lang en --verbose
```

Глобальный запуск с подробным логированием:

```bash
python main.py --verbose search "Python" --sort last_edit --limit 10 --lang en
```

Таблица результата содержит колонки:

```text
№ | Название | Описание | Размер | Последнее изменение
```

HTML-теги из `snippet`, которые возвращает MediaWiki API, очищаются перед выводом в консоль.




### Защита от 429 при скачивании изображений

При скачивании файлов с `upload.wikimedia.org` команда `images` делает небольшую паузу между загрузками. Если сервер возвращает `429 Too Many Requests`, программа учитывает заголовок `Retry-After`, повторяет запрос несколько раз и не завершает всю команду из-за ошибки одного изображения.

Для больших статей лучше не использовать `--all` без необходимости. Сначала проверьте небольшой лимит:

```bash
python main.py images "Solar System" --limit 3 --download --output ./pictures --lang en
```

## Команда `random`

Команда получает случайную статью Wikipedia. Если категория не указана, используется MediaWiki `list=random` для основного пространства имён. Если категория указана, команда получает страницы категории через `categorymembers`, выбирает одну случайную страницу и затем запрашивает краткую информацию о ней.

Команда поддерживает:

- опцию `--lang` — язык Wikipedia, по умолчанию `ru`;
- опцию `--category` — категория, из которой нужно выбрать случайную статью;
- опцию `--min-words` — минимальное примерное количество слов;
- опцию `--with-image` — искать только статьи с изображением;
- опцию `--verbose` — включает подробное логирование через стандартный модуль `logging`.

Пример без фильтров:

```bash
python main.py random --lang ru
```

Случайная статья в английской Wikipedia:

```bash
python main.py random --lang en
```

Случайная статья из категории:

```bash
python main.py random --category "Наука" --lang ru
```

```bash
python main.py random --category "Science" --lang en
```

С фильтром по примерному количеству слов:

```bash
python main.py random --min-words 1000 --lang ru
```

Только статьи с изображением:

```bash
python main.py random --with-image --lang ru
```

С несколькими фильтрами и подробным логированием:

```bash
python main.py random --category "Science" --min-words 1000 --with-image --lang en --verbose
```

Глобальный подробный режим также поддерживается:

```bash
python main.py --verbose random --category "Science" --min-words 1000 --with-image --lang en
```

Если статья не подходит под фильтры, команда делает несколько попыток. Количество попыток задаётся константой `DEFAULT_RANDOM_ATTEMPTS`. Если подходящая статья не найдена, выводится понятное сообщение об ошибке.


## Команда `info`

Команда выводит базовую информацию о статье Wikipedia:

- название статьи;
- ID страницы;
- размер страницы в байтах;
- дату последней правки;
- последнего редактора;
- первые 10 категорий при опции `--show-categories`;
- список изображений при опции `--show-image`;
- ссылку на статью в браузере.

Команда также поддерживает локальный `--verbose` и глобальный `--verbose` для логирования.

Пример:

```bash
python main.py info "Python" --show-categories --show-image --lang en
```

С подробным логированием:

```bash
python main.py info "Python" --show-categories --show-image --lang en --verbose
```

Глобальный подробный режим:

```bash
python main.py --verbose info "Python" --show-categories --show-image --lang en
```

## Команда `links`

Команда выводит внутренние ссылки из выбранной статьи Wikipedia.

Команда поддерживает:

- обязательный аргумент `title` — название статьи;
- опцию `--lang` — язык Wikipedia, по умолчанию `ru`;
- опцию `--limit` — максимальное количество ссылок, по умолчанию `50`;
- опцию `--search` — фильтрация ссылок по части названия;
- опцию `--verbose` — включает подробное логирование через стандартный модуль `logging`.

Пример получения ссылок:

```bash
python main.py links "Python" --limit 50 --lang en
```

Пример с фильтрацией:

```bash
python main.py links "Python" --search "programming" --limit 50 --lang en
```

С подробным логированием:

```bash
python main.py links "Python" --search "programming" --limit 50 --lang en --verbose
```

Глобальный подробный режим:

```bash
python main.py --verbose links "Python" --limit 50 --lang en
```

## Команда `graph`

Команда строит ориентированный граф ссылок статьи.

При `--depth 1` граф строится в один уровень:

```text
исходная статья -> статьи первого уровня
```

При `--depth 2` граф строится в два уровня:

```text
исходная статья -> статьи первого уровня -> статьи второго уровня
```

Команда переиспользует получение ссылок из команды `links` и не дублирует API-логику. Количество ссылок на каждом уровне ограничивается параметром `--limit`, чтобы граф не становился слишком большим. Дополнительно в конфигурации задано ограничение `DEFAULT_GRAPH_MAX_NODES`, после достижения которого граф аккуратно обрезается.

В изображении графа уровни визуально различаются цветами: исходная статья, ссылки первого уровня и ссылки второго уровня рисуются разными цветами. Рёбра второго уровня также выделяются отдельным цветом. В режиме `--text` рёбра второго уровня выводятся отдельным цветом в таблице и имеют значение `2` в колонке `Уровень`.

Команда поддерживает:

- обязательный аргумент `title` — название статьи;
- опцию `--lang` — язык Wikipedia, по умолчанию `ru`;
- опцию `--limit` — количество ссылок на каждом уровне, по умолчанию `30`;
- опцию `--depth` — глубина графа: `1` или `2`, по умолчанию `1`;
- опцию `--output` — путь сохранения файла, по умолчанию `graph.png`;
- опцию `--format` — формат файла: `png` или `pdf`;
- опцию `--text` — вывести рёбра графа в консоль без сохранения изображения;
- опцию `--verbose` — включает подробное логирование через стандартный модуль `logging`.

Сохранить одноуровневый граф в файл:

```bash
python main.py graph "Python" --limit 30 --output graph.png --format png --lang en
```

Сохранить двухуровневый граф в файл:

```bash
python main.py graph "Python" --depth 2 --limit 10 --output graph.png --format png --lang en
```

Вывести одноуровневый граф в текстовом виде:

```bash
python main.py graph "Python" --limit 20 --text --lang en
```

Вывести двухуровневый граф в текстовом виде:

```bash
python main.py graph "Python" --depth 2 --limit 5 --text --lang en
```

С подробным логированием:

```bash
python main.py graph "Python" --depth 2 --limit 5 --text --lang en --verbose
```

Глобальный подробный режим:

```bash
python main.py --verbose graph "Python" --depth 2 --limit 5 --text --lang en
```

Пример текстового вывода:

```text
Python -> Programming language
Python -> Guido van Rossum
Programming language -> Compiler
Programming language -> Interpreter
```

Поддерживаемые форматы сохранения:

- `png`;
- `pdf`.


## Команда `categories`

Команда выводит категории, к которым относится выбранная статья Wikipedia.

В обычном режиме команда показывает плоский список категорий. В режиме `--tree` команда дополнительно пытается получить подкатегории первого уровня для каждой найденной категории через MediaWiki API.

Команда поддерживает:

- обязательный аргумент `title` — название статьи;
- опцию `--lang` — язык Wikipedia, по умолчанию `ru`;
- опцию `--limit` — максимальное количество категорий, по умолчанию `20`;
- опцию `--tree` — вывести простое дерево категорий;
- опцию `--verbose` — включает подробное логирование через стандартный модуль `logging`.

Пример обычного вывода:

```bash
python main.py categories "Python" --lang en
```

Пример с ограничением количества категорий:

```bash
python main.py categories "Python" --limit 20 --lang en
```

Пример древовидного вывода:

```bash
python main.py categories "Python" --tree --limit 10 --lang en
```

С подробным логированием:

```bash
python main.py categories "Python" --tree --limit 10 --lang en --verbose
```

Глобальный подробный режим:

```bash
python main.py --verbose categories "Python" --tree --limit 10 --lang en
```

Пример структуры в режиме `--tree`:

```text
Python
├── Category:Python
│   └── Category:Python implementations
└── Category:Programming languages
    ├── Category:Object-oriented programming languages
    └── Category:Scripting languages
```


## Команда `pageviews`

Команда получает ежедневную статистику просмотров статьи Wikipedia за выбранный период через Wikimedia Pageviews API. По умолчанию анализируются последние 30 доступных дней. Команда специально пропускает последние 3 календарных дня, потому что Wikimedia Pageviews API обычно публикует свежую статистику с задержкой, и слишком свежий период может возвращать 404 или неполный набор дней.

Команда поддерживает:

- обязательный аргумент `title` — название статьи;
- опцию `--days` — количество дней для анализа, по умолчанию `30`;
- опцию `--chart` — тип графика: `none`, `ascii` или `png`;
- опцию `--output` — путь для сохранения PNG-графика, по умолчанию `pageviews.png`;
- опцию `--verbose` — включает подробное логирование через стандартный модуль `logging`.

Опция `--lang` для команды `pageviews` убрана. В этой команде нет текстового содержимого из Wikipedia, поэтому язык пользовательского вывода не настраивается через CLI. Внутри проекта для Pageviews API используется `en.wikipedia.org`, чтобы запросы вида `pageviews "Python"` работали предсказуемо.

Обычный запуск:

```bash
python main.py pageviews "Python"
```

Период 90 дней:

```bash
python main.py pageviews "Python" --days 90
```

Вывод ASCII-графика в консоль:

```bash
python main.py pageviews "Python" --days 30 --chart ascii
```

Сохранение PNG-графика:

```bash
python main.py pageviews "Python" --days 30 --chart png --output pageviews.png
```

Запуск с подробным логированием для команды:

```bash
python main.py pageviews "Python" --days 30 --chart ascii --verbose
```

Глобальный запуск с подробным логированием:

```bash
python main.py --verbose pageviews "Python" --days 30 --chart ascii
```

В обычном режиме логи не выводятся и не мешают пользовательскому выводу. В режиме `--verbose` используется стандартный модуль `logging`; в логах фиксируются запуск команды, параметры, рассчитанный период, URL Pageviews API, HTTP-статус ответа, время запроса, количество записей, успешное завершение или ошибка.

Если выполнить `--days 1`, команда возьмёт не вчерашний день, а последний доступный день с учётом задержки API.

Команда выводит таблицу:

```text
Дата | Просмотры
```


А также краткую сводку:

- суммарное количество просмотров за период;
- среднее количество просмотров в день;
- день с максимальным количеством просмотров;
- день с минимальным количеством просмотров.


## Команда `images`

Команда получает список изображений, используемых в статье Wikipedia. Для каждого изображения команда пытается получить название файла, прямой URL, MIME-тип и размер через MediaWiki `imageinfo`. При необходимости изображения можно скачать в указанную папку.

Команда поддерживает:

- обязательный аргумент `title` — название статьи;
- опцию `--lang` — язык Wikipedia, по умолчанию `ru`;
- опцию `--limit` — максимальное количество изображений, по умолчанию `10`;
- опцию `--download` — скачать изображения;
- опцию `--output` — папка сохранения, по умолчанию `downloads`;
- опцию `--all` — обработать все изображения, полученные командой;
- опцию `--verbose` — включает подробное логирование через стандартный модуль `logging`.

Получить список изображений без скачивания:

```bash
python main.py images "Солнечная система" --lang ru
```

```bash
python main.py images "Solar System" --limit 10 --lang en
```

Скачать изображения в папку:

```bash
python main.py images "Солнечная система" --download --output ./pictures --lang ru
```

Скачать все изображения, полученные командой:

```bash
python main.py images "Solar System" --download --all --output ./pictures --lang en
```

Запуск с подробным логированием:

```bash
python main.py images "Python" --limit 5 --download --output ./downloads --lang en --verbose
```

Глобальный подробный режим также поддерживается:

```bash
python main.py --verbose images "Python" --limit 5 --download --output ./downloads --lang en
```

Если папка для скачивания не существует, команда создаёт её автоматически. Если одно изображение не удалось скачать, команда не падает полностью: ошибка фиксируется в результатах скачивания, а остальные изображения продолжают обрабатываться.

## Установка

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Linux / macOS:

```bash
source .venv/bin/activate
```

Установка зависимостей:

```bash
pip install -r requirements.txt
```

## Запуск

Через `main.py`:

```bash
python main.py info "Python" --show-categories --show-image --lang en
```

```bash
python main.py links "Python" --limit 50 --lang en
```

```bash
python main.py graph "Python" --limit 30 --output graph.png --format png --lang en
```

```bash
python main.py graph "Python" --depth 2 --limit 10 --output graph.png --format png --lang en
```

```bash
python main.py categories "Python" --limit 20 --lang en
```

```bash
python main.py categories "Python" --tree --limit 10 --lang en
```

```bash
python main.py pageviews "Python" --days 30 --chart ascii
```

```bash
python main.py pageviews "Python" --days 30 --chart png --output pageviews.png
```

```bash
python main.py images "Solar System" --limit 10 --lang en
```

```bash
python main.py images "Solar System" --download --all --output ./pictures --lang en
```

По умолчанию используется русская Wikipedia:

```bash
python main.py info "Python"
```

```bash
python main.py links "Python"
```

```bash
python main.py graph "Python" --text
```

```bash
python main.py categories "Python"
```

```bash
python main.py pageviews "Python"
```

```bash
python main.py random --lang ru
```

```bash
python main.py images "Солнечная система"
```

## Тесты

```bash
pytest
```

## Структура проекта

```text
wiki-explorer/
├── wiki_explorer/
│   ├── __init__.py
│   ├── cli.py
│   ├── config.py
│   ├── exceptions.py
│   ├── logging_config.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── mediawiki_client.py
│   │   └── pageviews_client.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── article_service.py
│   │   ├── graph_service.py
│   │   ├── image_service.py
│   │   └── pageviews_service.py
│   └── output/
│       ├── __init__.py
│       ├── chart_renderer.py
│       └── console_renderer.py
├── tests/
│   ├── test_info.py
│   ├── test_links.py
│   ├── test_graph.py
│   ├── test_categories.py
│   ├── test_pageviews.py
│   ├── test_search.py
│   ├── test_random.py
│   └── test_images.py
├── requirements.txt
├── README.md
└── main.py
```


> Примечание по `pageviews`: Wikimedia Pageviews API публикует статистику с задержкой.
> Поэтому команда специально пропускает последние 3 календарных дня, чтобы запросы за свежие даты не возвращали 404 или неполный набор дней.
