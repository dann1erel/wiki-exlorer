
```markdown
# Wiki Explorer (CLI)

Утилита командной строки для работы с Wikipedia через API. Получайте информацию о статьях, ищите, скачивайте изображения, анализируйте просмотры, стройте графы ссылок и категории.

## Установка

```bash
git clone https://github.com/yourusername/wiki-explorer.git
cd wiki-explorer
python -m venv venv
source venv/bin/activate       # Linux/Mac
# или
venv\Scripts\activate           # Windows
pip install -e .
```

После установки станет доступна команда `wiki-explorer-ds`.

## Команды

### info
Показывает основную информацию о статье (размер, дата создания, последний редактор, категории и главное изображение).

```bash
wiki-explorer-ds info "Python" --lang en
```

Опции:
- `--show-categories` — вывести категории
- `--show-image-url` — показать URL главного изображения

### search
Поиск статей по ключевым словам.

```bash
wiki-explorer-ds search "machine learning" --limit 5 --sort relevance
```

Опции:
- `--limit N` — количество результатов (по умолч. 10, макс. 100)
- `--sort [relevance|last_edit]` — сортировка
- `--namespace` — пространство имён (0 – статьи)

### images
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

### pageviews
Статистика просмотров статьи за последние N дней.

```bash
wiki-explorer-ds pageviews "Россия" --days 30
wiki-explorer-ds pageviews "Python" --days 7 --chart ascii
wiki-explorer-ds pageviews "AI" --chart png --output views.png
```

Опции:
- `--days N` — количество дней (макс. 90)
- `--chart [ascii|png]` — нарисовать график (в консоли или сохранить PNG)
- `--output` — путь для PNG (по умолч. `pageviews_<title>.png`)

### categories
Выводит категории, в которые входит статья.

```bash
wiki-explorer-ds categories "Python"              # плоский список
wiki-explorer-ds categories "Россия" --tree       # с родительскими категориями
```

Опция `--tree` показывает для каждой категории её непосредственного родителя.

### graph
Строит ориентированный граф ссылок из статьи и сохраняет в PNG.

```bash
wiki-explorer-ds graph "Python" --output graph.png
wiki-explorer-ds graph "AI" --depth 2 --max-links 15 --output deep_graph.png
```

Опции:
- `--output` (обязательный) — путь к файлу .png
- `--depth {1,2}` — глубина (1 – только прямые ссылки, 2 – ссылки ссылок)
- `--max-links N` — максимальное количество ссылок на уровень (по умолч. 20)

**Требование:** установлены `networkx` и `matplotlib` (автоматически ставятся через `pip install -e .`).

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

## Автор

Ваше Имя (ваш email)
```

### Примечания
- Прикрепите к репозиторию файл `setup.py` (уже есть) и, возможно, значок лицензии.
- Если есть скриншоты примеров работы, положите их в папку `docs/` и добавьте ссылки в README.
- В качестве примера можно добавить .gif-анимацию работы нескольких команд, но это опционально.