"""Business logic for Wikimedia pageviews statistics."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from datetime import date, datetime, timedelta
from typing import Any

from wiki_explorer.api.pageviews_client import PageviewsClient
from wiki_explorer.config import (
    DEFAULT_PAGEVIEWS_DAYS,
    DEFAULT_PAGEVIEWS_LANGUAGE,
    DEFAULT_PAGEVIEWS_LAG_DAYS,
)
from wiki_explorer.exceptions import (
    InvalidApiResponseError,
    InvalidDateRangeError,
    PageviewsNotFoundError,
)


@dataclass(frozen=True)
class PageviewItem:
    """One daily pageviews data point."""

    date: date
    views: int


@dataclass(frozen=True)
class PageviewsSummary:
    """Calculated pageviews summary values."""

    total_views: int
    average_views: float
    max_views_day: PageviewItem
    min_views_day: PageviewItem


@dataclass(frozen=True)
class PageviewsResult:
    """Prepared data for the `pageviews` command output."""

    title: str
    lang: str
    start_date: date
    end_date: date
    items: list[PageviewItem] = field(default_factory=list)
    summary: PageviewsSummary | None = None
    verbose_info: dict[str, str] = field(default_factory=dict)


logger = logging.getLogger(__name__)


class PageviewsService:
    """Service for preparing article pageviews data."""

    def __init__(self, client: PageviewsClient | None = None) -> None:
        self.client = client or PageviewsClient()

    def get_pageviews(
        self,
        title: str,
        lang: str = DEFAULT_PAGEVIEWS_LANGUAGE,
        days: int = DEFAULT_PAGEVIEWS_DAYS,
        today: date | None = None,
    ) -> PageviewsResult:
        """Get daily pageviews and calculate summary statistics."""
        if days <= 0:
            raise InvalidDateRangeError(
                "Параметр --days должен быть положительным числом."
            )

        # Wikimedia Pageviews data usually appears with a delay.
        # We intentionally skip the most recent days to avoid 404 responses
        # for dates that have not been published by the API yet.
        end_date = (today or date.today()) - timedelta(
            days=DEFAULT_PAGEVIEWS_LAG_DAYS
        )
        start_date = end_date - timedelta(days=days - 1)
        logger.info(
            "Calculated pageviews period: %s — %s",
            start_date.isoformat(),
            end_date.isoformat(),
        )

        raw_data = self.client.get_pageviews(
            title=title,
            lang=lang,
            start_date=start_date,
            end_date=end_date,
        )
        items = self._extract_items(raw_data, title)
        logger.info("Pageviews records received: %s", len(items))
        summary = self._calculate_summary(items)

        verbose_info = {
            "command": "pageviews",
            "project": f"{lang}.wikipedia.org",
            "period": f"{start_date.isoformat()} — {end_date.isoformat()}",
            "endpoint": self.client.last_endpoint or "нет данных",
            "http_status": str(self.client.last_status_code or "нет данных"),
            "records": str(len(items)),
        }

        return PageviewsResult(
            title=title,
            lang=lang,
            start_date=start_date,
            end_date=end_date,
            items=items,
            summary=summary,
            verbose_info=verbose_info,
        )

    @staticmethod
    def _extract_items(data: dict[str, Any], title: str) -> list[PageviewItem]:
        """Extract daily pageviews items from raw API response."""
        raw_items = data.get("items")

        if raw_items is None:
            raise InvalidApiResponseError(
                "API вернул некорректный ответ. "
                "Невозможно получить статистику просмотров."
            )

        if not isinstance(raw_items, list):
            raise InvalidApiResponseError(
                "API вернул некорректную структуру списка просмотров."
            )

        if not raw_items:
            raise PageviewsNotFoundError(
                f'Для статьи "{title}" статистика просмотров не найдена.'
            )

        items: list[PageviewItem] = []
        for raw_item in raw_items:
            if not isinstance(raw_item, dict):
                raise InvalidApiResponseError(
                    "API вернул некорректный элемент статистики просмотров."
                )

            timestamp = raw_item.get("timestamp")
            views = raw_item.get("views")
            if not isinstance(timestamp, str) or not isinstance(views, int):
                raise InvalidApiResponseError(
                    "API вернул неполные данные статистики просмотров."
                )

            try:
                item_date = datetime.strptime(timestamp[:8], "%Y%m%d").date()
            except ValueError as exc:
                raise InvalidApiResponseError(
                    "API вернул некорректную дату статистики просмотров."
                ) from exc

            items.append(PageviewItem(date=item_date, views=views))

        return items

    @staticmethod
    def _calculate_summary(items: list[PageviewItem]) -> PageviewsSummary:
        """Calculate total, average, maximum and minimum views."""
        total_views = sum(item.views for item in items)
        average_views = total_views / len(items)
        max_views_day = max(items, key=lambda item: item.views)
        min_views_day = min(items, key=lambda item: item.views)

        return PageviewsSummary(
            total_views=total_views,
            average_views=average_views,
            max_views_day=max_views_day,
            min_views_day=min_views_day,
        )
