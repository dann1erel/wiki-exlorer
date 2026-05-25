"""Client for MediaWiki Action API."""

from __future__ import annotations

from typing import Any
import logging
import time

import requests

from wiki_explorer.config import (
    DEFAULT_CATEGORIES_LIMIT,
    DEFAULT_CATEGORY_LIMIT,
    DEFAULT_CATEGORY_MEMBERS_LIMIT,
    DEFAULT_IMAGES_LIMIT,
    DEFAULT_LANGUAGE,
    DEFAULT_LINKS_LIMIT,
    DEFAULT_SEARCH_LIMIT,
    DEFAULT_TIMEOUT,
    MEDIAWIKI_API_URL,
    USER_AGENT,
)
from wiki_explorer.exceptions import ApiRequestError, InvalidApiResponseError


logger = logging.getLogger(__name__)


class MediaWikiClient:
    """Small wrapper around MediaWiki Action API."""

    def __init__(self, timeout: int = DEFAULT_TIMEOUT) -> None:
        self.timeout = timeout
        self.last_url: str | None = None
        self.last_status_code: int | None = None
        self.last_elapsed_seconds: float | None = None


    def get_article_info(
        self,
        title: str,
        lang: str = DEFAULT_LANGUAGE,
        category_limit: int = DEFAULT_CATEGORY_LIMIT,
    ) -> dict[str, Any]:
        """Fetch raw article information from MediaWiki Action API."""
        params: dict[str, Any] = {
            "action": "query",
            "prop": "info|revisions|categories|images",
            "titles": title,
            "rvprop": "timestamp|user",
            "cllimit": category_limit,
            "format": "json",
            "formatversion": 2,
        }

        return self._get_json(lang=lang, params=params)

    def get_article_links(
        self,
        title: str,
        lang: str = DEFAULT_LANGUAGE,
        limit: int = DEFAULT_LINKS_LIMIT,
    ) -> dict[str, Any]:
        """Fetch raw article links from MediaWiki Action API.

        The method supports MediaWiki continuation and collects links until
        the requested limit is reached or API has no more pages to return.
        """
        if limit <= 0:
            raise ValueError("limit must be positive")

        result_pages: list[dict[str, Any]] = []
        query_continue: dict[str, Any] = {}
        remaining = limit

        while remaining > 0:
            current_limit = min(remaining, 500)
            params: dict[str, Any] = {
                "action": "query",
                "prop": "links",
                "titles": title,
                "pllimit": current_limit,
                "format": "json",
                "formatversion": 2,
                **query_continue,
            }

            data = self._get_json(lang=lang, params=params)
            pages = data.get("query", {}).get("pages")

            if not isinstance(pages, list) or not pages:
                raise InvalidApiResponseError(
                    "API вернул некорректную структуру данных о ссылках."
                )

            page = pages[0]
            if not isinstance(page, dict):
                raise InvalidApiResponseError(
                    "API вернул некорректную структуру объекта страницы."
                )

            links = page.get("links", [])
            if links and not isinstance(links, list):
                raise InvalidApiResponseError(
                    "API вернул некорректную структуру списка ссылок."
                )

            result_pages.append(page)
            remaining -= len(links) if isinstance(links, list) else 0

            continue_data = data.get("continue")
            if (
                not isinstance(continue_data, dict)
                or "plcontinue" not in continue_data
            ):
                break

            query_continue = {
                "continue": continue_data.get("continue", ""),
                "plcontinue": continue_data["plcontinue"],
            }

        merged_page = self._merge_link_pages(result_pages)

        return {"query": {"pages": [merged_page]}}


    def search_articles(
        self,
        query: str,
        lang: str = DEFAULT_LANGUAGE,
        limit: int = DEFAULT_SEARCH_LIMIT,
    ) -> dict[str, Any]:
        """Search Wikipedia articles through MediaWiki Action API."""
        if limit <= 0:
            raise ValueError("limit must be positive")

        params: dict[str, Any] = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": limit,
            "srprop": "snippet|size|timestamp",
            "format": "json",
            "formatversion": 2,
        }

        return self._get_json(lang=lang, params=params)

    def get_random_article(
        self,
        lang: str = DEFAULT_LANGUAGE,
    ) -> dict[str, Any]:
        """Fetch one random article from the main Wikipedia namespace."""
        params: dict[str, Any] = {
            "action": "query",
            "list": "random",
            "rnnamespace": 0,
            "rnlimit": 1,
            "format": "json",
            "formatversion": 2,
        }

        return self._get_json(lang=lang, params=params)

    def get_category_pages(
        self,
        category_title: str,
        lang: str = DEFAULT_LANGUAGE,
        limit: int = DEFAULT_CATEGORY_MEMBERS_LIMIT,
    ) -> dict[str, Any]:
        """Fetch pages that belong to a category."""
        if limit <= 0:
            raise ValueError("limit must be positive")

        params: dict[str, Any] = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": category_title,
            "cmtype": "page",
            "cmlimit": limit,
            "format": "json",
            "formatversion": 2,
        }

        return self._get_json(lang=lang, params=params)

    def get_article_summary_info(
        self,
        title: str,
        lang: str = DEFAULT_LANGUAGE,
    ) -> dict[str, Any]:
        """Fetch compact article info used by the `random` command."""
        params: dict[str, Any] = {
            "action": "query",
            "prop": "info|images",
            "titles": title,
            "inprop": "url",
            "imlimit": 1,
            "format": "json",
            "formatversion": 2,
        }

        return self._get_json(lang=lang, params=params)


    def get_article_images(
        self,
        title: str,
        lang: str = DEFAULT_LANGUAGE,
        limit: int = DEFAULT_IMAGES_LIMIT,
    ) -> dict[str, Any]:
        """Fetch raw image list for an article from MediaWiki Action API."""
        if limit <= 0:
            raise ValueError("limit must be positive")

        params: dict[str, Any] = {
            "action": "query",
            "prop": "images",
            "titles": title,
            "imlimit": limit,
            "format": "json",
            "formatversion": 2,
        }

        return self._get_json(lang=lang, params=params)

    def get_image_info(
        self,
        image_title: str,
        lang: str = DEFAULT_LANGUAGE,
    ) -> dict[str, Any]:
        """Fetch direct URL, size and MIME type for one image file."""
        params: dict[str, Any] = {
            "action": "query",
            "titles": image_title,
            "prop": "imageinfo",
            "iiprop": "url|size|mime",
            "format": "json",
            "formatversion": 2,
        }

        return self._get_json(lang=lang, params=params)

    def get_article_categories(
        self,
        title: str,
        lang: str = DEFAULT_LANGUAGE,
        limit: int = DEFAULT_CATEGORIES_LIMIT,
    ) -> dict[str, Any]:
        """Fetch raw article categories from MediaWiki Action API."""
        if limit <= 0:
            raise ValueError("limit must be positive")

        params: dict[str, Any] = {
            "action": "query",
            "prop": "categories",
            "titles": title,
            "cllimit": limit,
            "format": "json",
            "formatversion": 2,
        }

        return self._get_json(lang=lang, params=params)

    def get_category_subcategories(
        self,
        category_title: str,
        lang: str = DEFAULT_LANGUAGE,
        limit: int = DEFAULT_CATEGORIES_LIMIT,
    ) -> dict[str, Any]:
        """Fetch direct subcategories for a category title."""
        if limit <= 0:
            raise ValueError("limit must be positive")

        params: dict[str, Any] = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": category_title,
            "cmtype": "subcat",
            "cmlimit": limit,
            "format": "json",
            "formatversion": 2,
        }

        return self._get_json(lang=lang, params=params)

    def _get_json(self, lang: str, params: dict[str, Any]) -> dict[str, Any]:
        """Perform GET request and return JSON response."""
        url = MEDIAWIKI_API_URL.format(lang=lang)
        self.last_url = url
        self.last_status_code = None
        self.last_elapsed_seconds = None
        start_time = time.perf_counter()

        logger.info(
            "Request to MediaWiki API: url=%s, params=%s",
            url,
            self._safe_log_params(params),
        )

        try:
            response = requests.get(
                url,
                params=params,
                timeout=self.timeout,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/json",
                },
            )
            elapsed = time.perf_counter() - start_time
            self.last_status_code = response.status_code
            self.last_elapsed_seconds = elapsed
            logger.info("API response status: %s", response.status_code)
            logger.info("API request time: %.3f seconds", elapsed)
            response.raise_for_status()
        except requests.Timeout as exc:
            elapsed = time.perf_counter() - start_time
            self.last_elapsed_seconds = elapsed
            logger.error("API request failed: timeout exceeded after %.3f seconds", elapsed)
            raise ApiRequestError(
                "Превышено время ожидания ответа от Wikipedia API."
            ) from exc
        except requests.RequestException as exc:
            logger.error("API request failed: %s", exc)
            raise ApiRequestError(
                f"Не удалось подключиться к Wikipedia API. {exc}"
            ) from exc

        try:
            data = response.json()
        except ValueError as exc:
            logger.error("API response processing failed: invalid JSON")
            raise InvalidApiResponseError(
                "API вернул ответ не в формате JSON."
            ) from exc

        if not data:
            logger.error("API response processing failed: empty response")
            raise InvalidApiResponseError("API вернул пустой ответ.")

        logger.info("API response parsed successfully")
        return data

    @staticmethod
    def _safe_log_params(params: dict[str, Any]) -> dict[str, Any]:
        """Return request params for logs without sensitive data."""
        return dict(params)

    @staticmethod
    def _merge_link_pages(pages: list[dict[str, Any]]) -> dict[str, Any]:
        """Merge paginated MediaWiki page objects into one page object."""
        if not pages:
            raise InvalidApiResponseError(
                "API вернул некорректную структуру данных о ссылках."
            )

        merged = dict(pages[0])
        merged_links: list[dict[str, Any]] = []

        for page in pages:
            links = page.get("links", [])
            if isinstance(links, list):
                merged_links.extend(links)

        merged["links"] = merged_links
        return merged
