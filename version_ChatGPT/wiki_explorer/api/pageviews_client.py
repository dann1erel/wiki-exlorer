"""Client for Wikimedia Pageviews API."""

from __future__ import annotations

from datetime import date
import logging
import time
from typing import Any
from urllib.parse import quote

import requests

from wiki_explorer.config import (
    DEFAULT_PAGEVIEWS_LANGUAGE,
    DEFAULT_TIMEOUT,
    PAGEVIEWS_API_URL,
    USER_AGENT,
)
from wiki_explorer.exceptions import (
    ApiRequestError,
    InvalidApiResponseError,
    PageviewsNotFoundError,
)


logger = logging.getLogger(__name__)


class PageviewsClient:
    """Small wrapper around Wikimedia Pageviews API."""

    def __init__(self, timeout: int = DEFAULT_TIMEOUT) -> None:
        self.timeout = timeout
        self.last_endpoint: str | None = None
        self.last_status_code: int | None = None

    def get_pageviews(
        self,
        title: str,
        lang: str = DEFAULT_PAGEVIEWS_LANGUAGE,
        start_date: date | str | None = None,
        end_date: date | str | None = None,
    ) -> dict[str, Any]:
        """Fetch raw daily pageviews data from Wikimedia Pageviews API."""
        if start_date is None or end_date is None:
            raise ValueError("start_date and end_date are required")

        endpoint = self._build_endpoint(
            title=title,
            lang=lang,
            start_date=start_date,
            end_date=end_date,
        )
        self.last_endpoint = endpoint
        self.last_status_code = None

        start_time = time.perf_counter()
        logger.info("Request to Pageviews API: %s", endpoint)

        try:
            response = requests.get(
                endpoint,
                timeout=self.timeout,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/json",
                },
            )
            elapsed = time.perf_counter() - start_time
            self.last_status_code = response.status_code
            logger.info("API response status: %s", response.status_code)
            logger.info("API request time: %.3f seconds", elapsed)
            response.raise_for_status()
        except requests.Timeout as exc:
            elapsed = time.perf_counter() - start_time
            logger.error("API request failed: timeout exceeded after %.3f seconds", elapsed)
            raise ApiRequestError(
                "Превышено время ожидания ответа от Wikimedia Pageviews API."
            ) from exc
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response else None
            logger.error("API request failed: HTTP status %s", status_code)
            if status_code == 404:
                raise PageviewsNotFoundError(
                    f'Для статьи "{title}" статистика просмотров не найдена.'
                ) from exc
            raise ApiRequestError(
                f"Не удалось получить данные от Wikimedia Pageviews API. {exc}"
            ) from exc
        except requests.RequestException as exc:
            logger.error("API request failed: %s", exc)
            raise ApiRequestError(
                "Не удалось получить данные от Wikimedia Pageviews API. "
                f"{exc}"
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
    def _build_endpoint(
        title: str,
        lang: str,
        start_date: date | str,
        end_date: date | str,
    ) -> str:
        """Build encoded Pageviews API endpoint."""
        project = f"{lang}.wikipedia.org"
        article = quote(title.replace(" ", "_"), safe="")
        start = PageviewsClient._format_date(start_date)
        end = PageviewsClient._format_date(end_date)

        return PAGEVIEWS_API_URL.format(
            project=project,
            access="all-access",
            agent="user",
            article=article,
            granularity="daily",
            start=start,
            end=end,
        )

    @staticmethod
    def _format_date(value: date | str) -> str:
        """Convert date object or date string to Pageviews API format."""
        if isinstance(value, date):
            return value.strftime("%Y%m%d")
        return value
