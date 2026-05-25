"""Business logic for article-related commands."""

from __future__ import annotations

from dataclasses import dataclass, field
import random as random_module
import html
import logging
import re
from typing import Any
from urllib.parse import quote

from wiki_explorer.api.mediawiki_client import MediaWikiClient
from wiki_explorer.config import (
    ARTICLE_URL,
    DEFAULT_CATEGORIES_LIMIT,
    DEFAULT_CATEGORY_LIMIT,
    DEFAULT_LANGUAGE,
    DEFAULT_LINKS_LIMIT,
    DEFAULT_RANDOM_ATTEMPTS,
    DEFAULT_CATEGORY_MEMBERS_LIMIT,
    DEFAULT_SEARCH_LIMIT,
    DEFAULT_SEARCH_SORT,
)
from wiki_explorer.exceptions import (
    ApiRequestError,
    ArticleNotFoundError,
    InvalidApiResponseError,
    InvalidUserInputError,
    NoCategoryMembersError,
    RandomArticleNotFoundError,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ArticleInfo:
    """Prepared data for the `info` command output."""

    title: str
    page_id: int
    size_bytes: int | None
    last_edit_timestamp: str | None
    last_editor: str | None
    url: str
    categories: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)




@dataclass(frozen=True)
class ArticleCategories:
    """Prepared data for the `categories` command output."""

    title: str
    page_id: int
    categories: list[str] = field(default_factory=list)
    tree: dict[str, list[str]] = field(default_factory=dict)



@dataclass(frozen=True)
class ArticleLinks:
    """Prepared data for the `links` command output."""

    title: str
    page_id: int
    links: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SearchResult:
    """One normalized search result."""

    title: str
    snippet: str
    size: int | None
    timestamp: str | None


@dataclass(frozen=True)
class SearchResults:
    """Prepared data for the `search` command output."""

    query: str
    lang: str
    results: list[SearchResult] = field(default_factory=list)
    verbose_info: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class RandomArticle:
    """Prepared data for the `random` command output."""

    title: str
    page_id: int
    size_bytes: int | None
    words_count: int
    url: str
    has_image: bool
    first_image: str | None = None
    attempts_used: int = 1
    category: str | None = None


class ArticleService:
    """Service for preparing Wikipedia article data."""

    def __init__(self, client: MediaWikiClient | None = None) -> None:
        self.client = client or MediaWikiClient()

    def search_articles(
        self,
        query: str,
        lang: str = DEFAULT_LANGUAGE,
        limit: int = DEFAULT_SEARCH_LIMIT,
        sort: str = DEFAULT_SEARCH_SORT,
    ) -> SearchResults:
        """Search Wikipedia articles and normalize results for CLI output."""
        if limit <= 0:
            raise InvalidUserInputError(
                "Параметр --limit должен быть положительным числом."
            )

        normalized_sort = sort.lower()
        if normalized_sort not in {"relevance", "last_edit"}:
            raise InvalidUserInputError(
                "Параметр --sort должен быть одним из значений: "
                "relevance, last_edit."
            )

        data = self.client.search_articles(
            query=query,
            lang=lang,
            limit=limit,
        )
        results = self._extract_search_results(data)

        if normalized_sort == "last_edit":
            results.sort(
                key=lambda item: item.timestamp or "",
                reverse=True,
            )

        logger.info("Search results received: %s", len(results))
        verbose_info = {
            "command": "search",
            "lang": lang,
            "limit": str(limit),
            "sort": normalized_sort,
            "endpoint": self.client.last_url or "нет данных",
            "http_status": str(self.client.last_status_code or "нет данных"),
            "records": str(len(results)),
        }

        return SearchResults(
            query=query,
            lang=lang,
            results=results[:limit],
            verbose_info=verbose_info,
        )


    def get_random_article(
        self,
        lang: str = DEFAULT_LANGUAGE,
        category: str | None = None,
        min_words: int | None = None,
        with_image: bool = False,
    ) -> RandomArticle:
        """Get a random article and apply optional filters."""
        if min_words is not None and min_words <= 0:
            raise InvalidUserInputError(
                "Параметр --min-words должен быть положительным числом."
            )

        normalized_category = (
            self._normalize_category_title(category, lang)
            if category
            else None
        )
        category_candidates = (
            self._get_category_candidate_titles(
                normalized_category,
                lang,
                DEFAULT_CATEGORY_MEMBERS_LIMIT,
            )
            if normalized_category
            else None
        )

        for attempt in range(1, DEFAULT_RANDOM_ATTEMPTS + 1):
            title = self._pick_random_title(
                lang=lang,
                category_candidates=category_candidates,
            )
            logger.info(
                "Random article attempt %s/%s: title=%s",
                attempt,
                DEFAULT_RANDOM_ATTEMPTS,
                title,
            )

            page_data = self.client.get_article_summary_info(
                title=title,
                lang=lang,
            )
            page = self._extract_page(page_data, title)
            article = self._build_random_article(
                page=page,
                lang=lang,
                attempts_used=attempt,
                category=normalized_category,
            )

            if min_words is not None and article.words_count < min_words:
                logger.info(
                    "Random article skipped: words_count=%s is less than %s",
                    article.words_count,
                    min_words,
                )
                continue

            if with_image and not article.has_image:
                logger.info("Random article skipped: image is required")
                continue

            logger.info("Random article accepted: %s", article.title)
            return article

        raise RandomArticleNotFoundError(
            "Не удалось найти случайную статью по заданным фильтрам. "
            "Попробуйте уменьшить --min-words или убрать --with-image."
        )

    def get_info(
        self,
        title: str,
        lang: str = DEFAULT_LANGUAGE,
        include_categories: bool = False,
        include_images: bool = False,
    ) -> ArticleInfo:
        """Get and normalize article information for CLI output."""
        data = self.client.get_article_info(
            title=title,
            lang=lang,
            category_limit=DEFAULT_CATEGORY_LIMIT,
        )
        page = self._extract_page(data, title)

        revision = self._extract_last_revision(page)
        categories = self._extract_categories(page) if include_categories else []
        images = self._extract_images(page) if include_images else []

        return ArticleInfo(
            title=str(page.get("title", title)),
            page_id=int(page.get("pageid", 0)),
            size_bytes=page.get("length"),
            last_edit_timestamp=revision.get("timestamp"),
            last_editor=revision.get("user"),
            url=self._build_article_url(lang, str(page.get("title", title))),
            categories=categories,
            images=images,
        )

    def get_links(
        self,
        title: str,
        lang: str = DEFAULT_LANGUAGE,
        limit: int = DEFAULT_LINKS_LIMIT,
        search: str | None = None,
    ) -> ArticleLinks:
        """Get and normalize internal article links for CLI output."""
        if limit <= 0:
            raise ValueError("Параметр --limit должен быть положительным числом.")

        data = self.client.get_article_links(
            title=title,
            lang=lang,
            limit=limit,
        )
        page = self._extract_page(data, title)
        links = self._extract_links(page)

        if search:
            search_lower = search.lower()
            links = [link for link in links if search_lower in link.lower()]

        return ArticleLinks(
            title=str(page.get("title", title)),
            page_id=int(page.get("pageid", 0)),
            links=links[:limit],
        )


    def get_categories(
        self,
        title: str,
        lang: str = DEFAULT_LANGUAGE,
        limit: int = DEFAULT_CATEGORIES_LIMIT,
        tree: bool = False,
    ) -> ArticleCategories:
        """Get and normalize article categories for CLI output."""
        if limit <= 0:
            raise ValueError("Параметр --limit должен быть положительным числом.")

        data = self.client.get_article_categories(
            title=title,
            lang=lang,
            limit=limit,
        )
        page = self._extract_page(data, title)
        categories = self._extract_categories(page)[:limit]
        category_tree: dict[str, list[str]] = {}

        if tree:
            category_tree = self._build_category_tree(
                categories=categories,
                lang=lang,
                limit=limit,
            )

        return ArticleCategories(
            title=str(page.get("title", title)),
            page_id=int(page.get("pageid", 0)),
            categories=categories,
            tree=category_tree,
        )

    def _build_category_tree(
        self,
        categories: list[str],
        lang: str,
        limit: int,
    ) -> dict[str, list[str]]:
        """Build a simple category -> direct subcategories mapping."""
        category_tree: dict[str, list[str]] = {}

        for category in categories:
            try:
                data = self.client.get_category_subcategories(
                    category_title=category,
                    lang=lang,
                    limit=limit,
                )
                category_tree[category] = self._extract_category_members(data)
            except (ApiRequestError, InvalidApiResponseError):
                category_tree[category] = []

        return category_tree


    def _get_category_candidate_titles(
        self,
        category_title: str,
        lang: str,
        limit: int,
    ) -> list[str]:
        """Get page titles from a category for random selection."""
        data = self.client.get_category_pages(
            category_title=category_title,
            lang=lang,
            limit=limit,
        )
        members = self._extract_category_members(data)

        if not members:
            raise NoCategoryMembersError(
                f'В категории "{category_title}" не найдено статей.'
            )

        return members

    def _pick_random_title(
        self,
        lang: str,
        category_candidates: list[str] | None,
    ) -> str:
        """Pick a random article title either from API or category candidates."""
        if category_candidates is not None:
            return random_module.choice(category_candidates)

        data = self.client.get_random_article(lang=lang)
        random_items = data.get("query", {}).get("random")

        if not isinstance(random_items, list) or not random_items:
            raise InvalidApiResponseError(
                "API вернул некорректный ответ. "
                "Невозможно получить случайную статью."
            )

        random_item = random_items[0]
        if not isinstance(random_item, dict) or not random_item.get("title"):
            raise InvalidApiResponseError(
                "API вернул некорректный объект случайной статьи."
            )

        return str(random_item["title"])

    def _build_random_article(
        self,
        page: dict[str, Any],
        lang: str,
        attempts_used: int,
        category: str | None,
    ) -> RandomArticle:
        """Convert a MediaWiki page object into RandomArticle."""
        size = page.get("length")
        size_bytes = size if isinstance(size, int) else None
        words_count = size_bytes // 6 if size_bytes is not None else 0
        images = self._extract_images(page)
        title = str(page.get("title", ""))
        url = str(page.get("fullurl") or self._build_article_url(lang, title))

        return RandomArticle(
            title=title,
            page_id=int(page.get("pageid", 0)),
            size_bytes=size_bytes,
            words_count=words_count,
            url=url,
            has_image=bool(images),
            first_image=images[0] if images else None,
            attempts_used=attempts_used,
            category=category,
        )

    @staticmethod
    def _normalize_category_title(category: str | None, lang: str) -> str | None:
        """Add localized category prefix when user passed a bare category name."""
        if category is None:
            return None

        normalized = category.strip()
        if not normalized:
            return None

        known_prefixes = ("Category:", "Категория:")
        if normalized.startswith(known_prefixes):
            return normalized

        if lang.lower().startswith("ru"):
            return f"Категория:{normalized}"

        if lang.lower().startswith("en"):
            return f"Category:{normalized}"

        return normalized

    @staticmethod
    def _extract_page(data: dict[str, Any], title: str) -> dict[str, Any]:
        pages = data.get("query", {}).get("pages")

        if not isinstance(pages, list) or not pages:
            raise InvalidApiResponseError(
                "API вернул некорректную структуру данных о странице."
            )

        page = pages[0]
        if not isinstance(page, dict):
            raise InvalidApiResponseError(
                "API вернул некорректную структуру объекта страницы."
            )

        if page.get("missing") is True or "pageid" not in page:
            raise ArticleNotFoundError(f'Статья "{title}" не найдена.')

        return page

    @staticmethod
    def _extract_last_revision(page: dict[str, Any]) -> dict[str, Any]:
        revisions = page.get("revisions", [])
        if not isinstance(revisions, list) or not revisions:
            return {}

        revision = revisions[0]
        return revision if isinstance(revision, dict) else {}

    @staticmethod
    def _extract_categories(page: dict[str, Any]) -> list[str]:
        categories = page.get("categories", [])
        if not isinstance(categories, list):
            return []

        return [
            str(category.get("title", ""))
            for category in categories
            if isinstance(category, dict) and category.get("title")
        ]


    @staticmethod
    def _extract_category_members(data: dict[str, Any]) -> list[str]:
        members = data.get("query", {}).get("categorymembers")
        if members is None:
            return []

        if not isinstance(members, list):
            raise InvalidApiResponseError(
                "API вернул некорректную структуру списка подкатегорий."
            )

        return [
            str(member.get("title", ""))
            for member in members
            if isinstance(member, dict) and member.get("title")
        ]

    @staticmethod
    def _extract_images(page: dict[str, Any]) -> list[str]:
        images = page.get("images", [])
        if not isinstance(images, list):
            return []

        return [
            str(image.get("title", ""))
            for image in images
            if isinstance(image, dict) and image.get("title")
        ]

    @staticmethod
    def _extract_links(page: dict[str, Any]) -> list[str]:
        links = page.get("links", [])
        if not isinstance(links, list):
            return []

        return [
            str(link.get("title", ""))
            for link in links
            if isinstance(link, dict) and link.get("title")
        ]

    @staticmethod
    def _extract_search_results(data: dict[str, Any]) -> list[SearchResult]:
        search_data = data.get("query", {}).get("search")

        if search_data is None:
            raise InvalidApiResponseError(
                "API вернул некорректный ответ. Невозможно выполнить поиск."
            )

        if not isinstance(search_data, list):
            raise InvalidApiResponseError(
                "API вернул некорректную структуру результатов поиска."
            )

        results: list[SearchResult] = []
        for raw_item in search_data:
            if not isinstance(raw_item, dict):
                raise InvalidApiResponseError(
                    "API вернул некорректный элемент результатов поиска."
                )

            title = raw_item.get("title")
            if not title:
                continue

            raw_snippet = str(raw_item.get("snippet", ""))
            size = raw_item.get("size")
            timestamp = raw_item.get("timestamp")

            results.append(
                SearchResult(
                    title=str(title),
                    snippet=ArticleService._clean_search_snippet(raw_snippet),
                    size=size if isinstance(size, int) else None,
                    timestamp=timestamp if isinstance(timestamp, str) else None,
                )
            )

        return results

    @staticmethod
    def _clean_search_snippet(snippet: str) -> str:
        """Remove HTML tags and unescape entities from MediaWiki snippet."""
        without_tags = re.sub(r"<[^>]+>", "", snippet)
        normalized_spaces = re.sub(r"\s+", " ", without_tags).strip()
        return html.unescape(normalized_spaces)

    @staticmethod
    def _build_article_url(lang: str, title: str) -> str:
        safe_title = quote(title.replace(" ", "_"))
        return ARTICLE_URL.format(lang=lang, title=safe_title)
