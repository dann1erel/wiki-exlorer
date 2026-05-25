# README.md для GitHub-репозитория


# Wiki Explorer (CLI)

Утилита командной строки для работы с Wikipedia через API. Получайте информацию о статьях, ищите, скачивайте изображения, анализируйте просмотры, стройте графы ссылок, изучайте категории и находите случайные статьи с фильтрацией.

## Установка

```bash
git clone https://github.com/yourusername/wiki-explorer.git
cd wiki-explorer
python -m venv venv
source venv/bin/activate       # Linux/Mac
# или
venv\Scripts\activate           # Windows
pip install -e .


После установки станет доступна команда `wiki-explorer-ds`.

## Команды

### `info`
Показывает основную информацию о статье (размер, дата создания, последний редактор, категории, главное изображение).

```bash
wiki-explorer-ds info "Python" --lang en
wiki-explorer-ds info "Россия" --show-categories --show-image-url
```

Опции:
- `--show-categories` — вывести категории (первые 10)
- `--show-image-url` — показать URL главного изображения

---

### `search`
Поиск статей по ключевым словам с сортировкой и ограничением.

```bash
wiki-explorer-ds search "machine learning" --limit 5 --sort relevance
wiki-explorer-ds search "deep learning" --lang ru --sort last_edit
```

Опции:
- `--limit N` — количество результатов (по умолч. 10, макс. 100)
- `--sort [relevance|last_edit|last_edit_desc]` — сортировка
- `--namespace` — пространство имён (0 – статьи, 1 – обсуждения и т.д.)

---

### `links`
Выводит список ссылок из статьи (только основные статьи).

```bash
wiki-explorer-ds links "Python" --limit 20
```

Опции:
- `--limit N` — количество ссылок (по умолч. 50)
- `--offset N` — смещение для пагинации

---

### `images`
Список всех изображений, используемых в статье, с возможностью скачать.

```bash
wiki-explorer-ds images "Python"                          # только таблица
wiki-explorer-ds images "Python" --download               # скачать все
wiki-explorer-ds images "Python" --index 1,3,5 --output ./my_images
```

Опции:
- `--download` — скачать все изображения
- `--index` — скачать только выбранные (номера через запятую)
- `--output` — папка для сохранения (по умолч. `./wiki_images/`)

---

### `pageviews`
Статистика просмотров статьи за последние N дней с возможностью построить график.

```bash
wiki-explorer-ds pageviews "Россия" --days 30
wiki-explorer-ds pageviews "Python" --days 7 --chart ascii
wiki-explorer-ds pageviews "AI" --chart png --output views.png
```

Опции:
- `--days N` — количество дней (макс. 90)
- `--chart [ascii|png]` — нарисовать график (в консоли символами или сохранить PNG)
- `--output` — путь для PNG (по умолч. `pageviews_<title>.png`)

---

### `categories`
Выводит категории, в которые входит статья, а также родительские категории (один уровень).

```bash
wiki-explorer-ds categories "Python"              # плоский список
wiki-explorer-ds categories "Россия" --tree       # с родительскими категориями
```

Опция `--tree` показывает для каждой категории её непосредственного родителя.

---

### `graph`
Строит ориентированный граф ссылок из статьи и сохраняет в PNG. Узлы раскрашены по глубине: корень — красный, прямые ссылки — голубые, ссылки второго уровня — зелёные.

```bash
wiki-explorer-ds graph "Python" --output graph.png
wiki-explorer-ds graph "AI" --depth 2 --max-links 15 --output deep_graph.png
```

Опции:
- `--output` (обязательный) — путь к файлу .png
- `--depth {1,2}` — глубина (1 – только прямые ссылки, 2 – ссылки ссылок)
- `--max-links N` — максимальное количество ссылок на уровень (по умолч. 20)

**Требование:** установлены `networkx` и `matplotlib` (автоматически ставятся через `pip install -e .`).

---

### `random`
Выбирает случайную статью с возможной фильтрацией по категории, минимальному количеству слов и наличию изображений.

```bash
wiki-explorer-ds random
wiki-explorer-ds random --category "Science" --min-words 500 --with-image --max-attempts 20
```

Опции:
- `--category` — ограничиться статьями из указанной категории
- `--min-words N` — минимальное количество слов в статье
- `--with-image` — требовать наличие хотя бы одного изображения
- `--max-attempts N` — количество попыток подбора (по умолч. 10)

---

## Глобальные опции

Все команды принимают:

- `--lang` (по умолч. `en`) — язык Wikipedia (`ru`, `en`, `de` и т.д.)
- `--verbose` — подробный вывод (логи запросов, отладочная информация)

Пример:
```bash
wiki-explorer-ds --lang ru --verbose info "Санкт-Петербург"
```

## Тестирование

```bash
pip install pytest pytest-cov
pytest tests/ -v
pytest tests/ --cov=wiki_explorer --cov-report=html
```

## Требования

- Python 3.8+
- Пакеты (устанавливаются автоматически):
  - click
  - requests
  - rich
  - networkx
  - matplotlib

## Лицензия

MIT
