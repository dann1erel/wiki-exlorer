"""Функции для работы с MediaWiki Action API."""

import time
from typing import Dict, Any, Optional

import requests

from wiki_explorer.utils.errors import NotFoundError, ApiError, NetworkError

MAX_RETRIES = 3
RETRY_DELAY = 1

# User-Agent для соблюдения правил Википедии (рекомендуется указать свои контактные данные)
APP_USER_AGENT = "WikiExplorerCLI/1.0 (https://github.com/yourusername/wiki-explorer; your-email@example.com)"

def _make_request(url: str, params: Dict[str, Any], retries: int = MAX_RETRIES) -> Dict[str, Any]:
    headers = {
        'User-Agent': APP_USER_AGENT,
    }
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            if attempt == retries:
                raise NetworkError(f"Сетевая ошибка после {retries} попыток: {e}") from e
            time.sleep(RETRY_DELAY)
    raise NetworkError("Неожиданный сбой при выполнении запроса")

def fetch_article_info(title: str, lang: str) -> Dict[str, Any]:
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "prop": "info|revisions|categories|images",
        "titles": title,
        "inprop": "url|size",
        "rvprop": "timestamp|user|size",
        "cllimit": 10,
        "format": "json",
        "origin": "*"
    }
    data = _make_request(url, params)
    pages = data.get("query", {}).get("pages", {})
    if not pages:
        raise ApiError("Ответ API не содержит поле 'query.pages'")
    page = next(iter(pages.values()))
    if "missing" in page:
        raise NotFoundError(f"Статья '{title}' не найдена в {lang}.wikipedia.org")
    info = page.get("info", {})
    title_from_api = page.get("title", title)
    size = info.get("size", 0)
    links = info.get("links", 0)
    revisions = page.get("revisions", [])
    if revisions:
        last_rev = revisions[0]
        last_modified = last_rev.get("timestamp", "")
        last_editor = last_rev.get("user", "")
        oldest_rev = revisions[-1]
        created = oldest_rev.get("timestamp", "")
    else:
        created = last_modified = last_editor = ""
    categories_raw = page.get("categories", [])
    categories = []
    for cat in categories_raw:
        cat_title = cat.get("title", "")
        if ":" in cat_title:
            cat_title = cat_title.split(":", 1)[-1]
        categories.append(cat_title)
    images = page.get("images", [])
    image_title = images[0].get("title") if images else None
    return {
        "title": title_from_api,
        "size": size,
        "links": links,
        "created": created,
        "last_modified": last_modified,
        "last_editor": last_editor,
        "categories": categories,
        "image_title": image_title,
    }

def fetch_image_url(image_title: str, lang: str) -> Optional[str]:
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "titles": image_title,
        "prop": "imageinfo",
        "iiprop": "url",
        "format": "json",
        "origin": "*"
    }
    try:
        data = _make_request(url, params)
        pages = data.get("query", {}).get("pages", {})
        if pages:
            page = next(iter(pages.values()))
            image_info = page.get("imageinfo", [])
            if image_info and "url" in image_info[0]:
                return image_info[0]["url"]
    except (NetworkError, ApiError):
        pass
    return None


# В файле wiki_explorer/api/mediawiki.py, добавить после существующих функций:

# В файле wiki_explorer/api/mediawiki.py, функция search_articles

def search_articles(
    query: str,
    lang: str,
    limit: int = 10,
    sort: str = "relevance",
    namespace: int = 0
) -> Dict[str, Any]:
    """
    Поиск статей по ключевым словам.

    Параметры:
        query: поисковый запрос
        lang: языковой код (ru, en и т.д.)
        limit: количество результатов (макс. 100)
        sort: тип сортировки (relevance или last_edit_desc)
        namespace: пространство имён (0 = основные статьи)
    """
    effective_limit = min(limit, 100)

    # Корректируем sort для обратной совместимости
    if sort == "last_edit":
        sort = "last_edit_desc"

    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": effective_limit,
        "srsort": sort,
        "srnamespace": namespace,
        "format": "json",
        "origin": "*"
    }

    data = _make_request(url, params)

    if "error" in data:
        error_info = data["error"]
        raise ApiError(
            f"API вернул ошибку: {error_info.get('code', 'unknown')} - {error_info.get('info', 'нет описания')}"
        )

    if "query" not in data:
        raise ApiError(f"Неожиданный ответ API: отсутствует поле 'query'. Ответ: {data}")

    if "search" not in data["query"]:
        raise ApiError(
            f"Неожиданный ответ API: отсутствует поле 'query.search'. "
            f"Содержимое query: {data['query']}"
        )

    return data["query"]


def fetch_page_links(title: str, lang: str, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    effective_limit = min(limit, 500)
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "prop": "links",
        "titles": title,
        "pllimit": effective_limit,
        "ploffset": offset,
        "plnamespace": 0,
        "format": "json",
        "origin": "*"
    }
    data = _make_request(url, params)

    if "error" in data:
        raise ApiError(f"API error: {data['error'].get('info', 'unknown')}")

    pages = data.get("query", {}).get("pages", {})
    if not pages:
        raise ApiError("No pages in response")
    page = next(iter(pages.values()))
    if "missing" in page:
        raise NotFoundError(f"Статья '{title}' не найдена в {lang}.wikipedia.org")

    links = page.get("links", [])
    has_more = "continue" in data   # API добавляет этот ключ, если есть ещё записи

    return {
        "links": links,
        "has_more": has_more
    }

def get_image_list(title: str, lang: str) -> list[Dict[str, Any]]:
    """
    Получает список изображений, используемых в статье, с их URL и размерами.

    Параметры:
        title: название статьи
        lang: языковой код

    Возвращает:
        Список словарей: [{"filename": "File:Example.jpg", "url": "https://...", "size": 12345}, ...]

    Исключения:
        NotFoundError: статья не найдена
        ApiError: ошибка API
        NetworkError: сетевая ошибка
    """
    images = []
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "prop": "images|imageinfo",
        "titles": title,
        "iilimit": 50,
        "iiprop": "url|size",   # ВАЖНО: запрашиваем url и размер
        "format": "json",
        "origin": "*"
    }
    while True:
        data = _make_request(url, params)
        if "error" in data:
            raise ApiError(f"API error: {data['error'].get('info', 'unknown')}")
        pages = data.get("query", {}).get("pages", {})
        if not pages:
            raise ApiError("No pages in response")
        page = next(iter(pages.values()))
        if "missing" in page:
            raise NotFoundError(f"Статья '{title}' не найдена в {lang}.wikipedia.org")
        imgs = page.get("images", [])
        img_infos = page.get("imageinfo", [])
        for idx, img in enumerate(imgs):
            filename = img.get("title", "")
            info = img_infos[idx] if idx < len(img_infos) else {}
            url_img = info.get("url", "")
            size = info.get("size", 0)
            images.append({
                "filename": filename,
                "url": url_img,
                "size": size
            })
        # Пагинация
        if "continue" in data and "imcontinue" in data["continue"]:
            params["imcontinue"] = data["continue"]["imcontinue"]
        else:
            break
    return images

# ==================== Добавлено для команды categories ====================

def get_categories(title: str, lang: str) -> list[str]:
    """
    Возвращает список категорий статьи (без префикса 'Category:').

    Параметры:
        title: название статьи
        lang: языковой код (ru, en и т.д.)

    Возвращает:
        Список названий категорий (без префикса)

    Исключения:
        NotFoundError: статья не найдена
        ApiError: ошибка API
        NetworkError: сетевая ошибка
    """
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "prop": "categories",
        "titles": title,
        "cllimit": 500,
        "format": "json",
        "origin": "*"
    }
    data = _make_request(url, params)
    pages = data.get("query", {}).get("pages", {})
    if not pages:
        raise ApiError("Ответ API не содержит поле 'query.pages'")
    page = next(iter(pages.values()))
    if "missing" in page:
        raise NotFoundError(f"Статья '{title}' не найдена в {lang}.wikipedia.org")
    categories = page.get("categories", [])
    result = []
    for cat in categories:
        cat_title = cat.get("title", "")
        if cat_title.startswith("Category:"):
            cat_title = cat_title[9:]  # удаляем префикс
        result.append(cat_title)
    return result


def get_parent_categories(category_names: list[str], lang: str) -> Dict[str, Optional[str]]:
    """
    Для списка категорий (без префикса) возвращает словарь
    {категория: родительская_категория_или_None}.
    Родительская категория возвращается без префикса 'Category:'.

    Параметры:
        category_names: список названий категорий (без префикса)
        lang: языковой код

    Возвращает:
        Словарь, где ключ — имя категории, значение — родитель (или None)

    Исключения:
        ApiError: ошибка API
        NetworkError: сетевая ошибка
    """
    if not category_names:
        return {}
    # Формируем список titles с префиксом "Category:"
    titles = "|".join(f"Category:{name}" for name in category_names)
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "prop": "categories",
        "titles": titles,
        "cllimit": 1,          # достаточно одной родительской категории
        "format": "json",
        "origin": "*"
    }
    data = _make_request(url, params)
    pages = data.get("query", {}).get("pages", {})
    result = {}
    for page in pages.values():
        # Полное название страницы (с "Category:")
        full_title = page.get("title", "")
        if full_title.startswith("Category:"):
            cat_name = full_title[9:]
        else:
            cat_name = full_title
        categories = page.get("categories", [])
        if categories:
            first_cat = categories[0].get("title", "")
            if first_cat.startswith("Category:"):
                parent = first_cat[9:]
            else:
                parent = first_cat
            result[cat_name] = parent
        else:
            result[cat_name] = None
    return result


# ==================== Добавлено для команды graph ====================

def get_links(title: str, lang: str, limit: int = 500, offset: int = 0) -> list[str]:
    """
    Возвращает список ссылок из статьи (без префиксов, только основные пространства имён).
    Поддерживает пагинацию через offset.

    Параметры:
        title: название статьи
        lang: языковой код
        limit: количество ссылок за один запрос (макс. 500)
        offset: смещение для пагинации

    Возвращает:
        Список названий статей, на которые ссылается данная

    Исключения:
        NotFoundError: статья не найдена
        ApiError: ошибка API
        NetworkError: сетевая ошибка
    """
    effective_limit = min(limit, 500)
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "prop": "links",
        "titles": title,
        "pllimit": effective_limit,
        "ploffset": offset,
        "plnamespace": 0,  # только основные статьи
        "format": "json",
        "origin": "*"
    }
    data = _make_request(url, params)
    pages = data.get("query", {}).get("pages", {})
    if not pages:
        raise ApiError("Ответ API не содержит поле 'query.pages'")
    page = next(iter(pages.values()))
    if "missing" in page:
        raise NotFoundError(f"Статья '{title}' не найдена в {lang}.wikipedia.org")
    links = page.get("links", [])
    return [link["title"] for link in links]


def get_links_batch(titles: list[str], lang: str, limit_per_title: int = 100) -> Dict[str, list[str]]:
    """
    Для нескольких статей возвращает их ссылки за один запрос.

    Параметры:
        titles: список названий статей
        lang: языковой код
        limit_per_title: максимум ссылок на статью

    Возвращает:
        Словарь {название_статьи: [список_ссылок]}

    Исключения:
        ApiError: ошибка API
        NetworkError: сетевая ошибка
    """
    if not titles:
        return {}
    effective_limit = min(limit_per_title, 500)
    # Объединяем названия через pipe (API поддерживает до 50 titles, но мы не будем превышать)
    # Если titles > 50, нужно разбивать, но для графа с max_links=20 это не проблема.
    titles_str = "|".join(titles)
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "prop": "links",
        "titles": titles_str,
        "pllimit": effective_limit,
        "plnamespace": 0,
        "format": "json",
        "origin": "*"
    }
    data = _make_request(url, params)
    pages = data.get("query", {}).get("pages", {})
    result = {}
    for page_id, page_data in pages.items():
        if "missing" in page_data:
            # Статья не найдена – пропускаем (не добавляем в граф)
            continue
        title_from_api = page_data.get("title", "")
        links = page_data.get("links", [])
        result[title_from_api] = [link["title"] for link in links]
    return result

# ==================== Добавлено для команды random ====================

def get_random_page(lang: str) -> Dict[str, Any]:
    """
    Возвращает одну случайную страницу из основного пространства имён.

    Параметры:
        lang: языковой код

    Возвращает:
        Словарь с полями: title, pageid.

    Исключения:
        ApiError: ошибка API
        NetworkError: сетевая ошибка
    """
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "random",
        "rnlimit": 1,
        "rnnamespace": 0,
        "format": "json",
        "origin": "*"
    }
    data = _make_request(url, params)
    random_list = data.get("query", {}).get("random", [])
    if not random_list:
        raise ApiError("Не удалось получить случайную статью")
    return random_list[0]  # содержит id и title


def get_category_members(lang: str, category: str, limit: int = 50) -> list[str]:
    """
    Возвращает список названий статей из указанной категории (без префикса Category:).

    Параметры:
        lang: языковой код
        category: название категории (без префикса "Category:")
        limit: максимальное количество страниц (не более 500)

    Возвращает:
        Список названий статей.

    Исключения:
        ApiError: ошибка API (включая несуществующую категорию)
        NetworkError: сетевая ошибка
    """
    effective_limit = min(limit, 500)
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": f"Category:{category}",
        "cmtype": "page",
        "cmlimit": effective_limit,
        "format": "json",
        "origin": "*"
    }
    data = _make_request(url, params)
    members = data.get("query", {}).get("categorymembers", [])
    if not members:
        # Проверим, существует ли категория (простым запросом)
        check_params = {
            "action": "query",
            "titles": f"Category:{category}",
            "format": "json",
            "origin": "*"
        }
        check_data = _make_request(url, check_params)
        pages = check_data.get("query", {}).get("pages", {})
        page = next(iter(pages.values()))
        if "missing" in page:
            raise ApiError(f"Категория '{category}' не найдена")
        # Категория существует, но пуста
        return []
    return [member["title"] for member in members]


def fetch_page_extract(title: str, lang: str) -> str:
    """
    Возвращает краткое описание (extract) статьи — первое предложение без разметки.

    Параметры:
        title: название статьи
        lang: языковой код

    Возвращает:
        Текст первого предложения (или пустую строку, если нет описания).

    Исключения:
        NotFoundError: статья не найдена
        ApiError: ошибка API
        NetworkError: сетевая ошибка
    """
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "prop": "extracts",
        "titles": title,
        "exintro": 1,
        "explaintext": 1,
        "format": "json",
        "origin": "*"
    }
    data = _make_request(url, params)
    pages = data.get("query", {}).get("pages", {})
    if not pages:
        raise ApiError("Ответ API не содержит поле 'query.pages'")
    page = next(iter(pages.values()))
    if "missing" in page:
        raise NotFoundError(f"Статья '{title}' не найдена в {lang}.wikipedia.org")
    extract = page.get("extract", "")
    return extract


def page_has_images(title: str, lang: str) -> bool:
    """
    Проверяет, есть ли в статье хотя бы одно изображение.

    Параметры:
        title: название статьи
        lang: языковой код

    Возвращает:
        True, если есть изображения, иначе False.

    Исключения:
        NotFoundError: статья не найдена
        ApiError: ошибка API
        NetworkError: сетевая ошибка
    """
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "prop": "images",
        "titles": title,
        "imlimit": 1,
        "format": "json",
        "origin": "*"
    }
    data = _make_request(url, params)
    pages = data.get("query", {}).get("pages", {})
    if not pages:
        raise ApiError("Ответ API не содержит поле 'query.pages'")
    page = next(iter(pages.values()))
    if "missing" in page:
        raise NotFoundError(f"Статья '{title}' не найдена в {lang}.wikipedia.org")
    images = page.get("images", [])
    return len(images) > 0