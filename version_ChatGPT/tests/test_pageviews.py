"""Tests for the `pageviews` command implementation."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
import requests
import requests_mock as requests_mock_module
from click.testing import CliRunner

from wiki_explorer.api.pageviews_client import PageviewsClient
from wiki_explorer.cli import cli
from wiki_explorer.exceptions import (
    ApiRequestError,
    InvalidApiResponseError,
    InvalidDateRangeError,
    PageviewsNotFoundError,
)
from wiki_explorer.output.chart_renderer import ChartRenderer
from wiki_explorer.services.pageviews_service import PageviewsService

API_URL = (
    "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
    "en.wikipedia.org/all-access/user/Python/daily/20231231/20240129"
)


def _mock_pageviews_response():
    return {
        "items": [
            {"timestamp": "2024010200", "views": 100},
            {"timestamp": "2024010300", "views": 200},
            {"timestamp": "2024010400", "views": 50},
        ]
    }


def test_get_pageviews_success(requests_mock):
    """Service should return daily pageviews from a successful API response."""
    requests_mock.get(API_URL, json=_mock_pageviews_response())

    service = PageviewsService(PageviewsClient())
    result = service.get_pageviews(
        "Python",
        lang="en",
        days=30,
        today=date(2024, 2, 1),
    )

    assert result.title == "Python"
    assert result.lang == "en"
    assert result.start_date == date(2023, 12, 31)
    assert result.end_date == date(2024, 1, 29)
    assert [item.views for item in result.items] == [100, 200, 50]

    request = requests_mock.last_request
    assert request.headers["User-Agent"].startswith("Wiki-Explorer")


def test_pageviews_skips_recent_unpublished_days(requests_mock):
    """Service should skip recent days because Pageviews API is delayed."""
    requests_mock.get(API_URL, json=_mock_pageviews_response())

    service = PageviewsService(PageviewsClient())
    result = service.get_pageviews(
        "Python",
        lang="en",
        days=30,
        today=date(2024, 2, 1),
    )

    assert result.end_date == date(2024, 1, 29)
    assert result.start_date == date(2023, 12, 31)


def test_pageviews_summary_calculation(requests_mock):
    """Service should calculate total, average, max and min values."""
    requests_mock.get(API_URL, json=_mock_pageviews_response())

    service = PageviewsService(PageviewsClient())
    result = service.get_pageviews(
        "Python",
        lang="en",
        days=30,
        today=date(2024, 2, 1),
    )

    assert result.summary is not None
    assert result.summary.total_views == 350
    assert result.summary.average_views == pytest.approx(116.6666, rel=1e-3)
    assert result.summary.max_views_day.views == 200
    assert result.summary.min_views_day.views == 50


def test_pageviews_invalid_days():
    """Service should reject non-positive days values."""
    service = PageviewsService(PageviewsClient())

    with pytest.raises(InvalidDateRangeError, match="--days"):
        service.get_pageviews("Python", lang="en", days=0)


def test_pageviews_empty_items(requests_mock):
    """Service should report when Pageviews API returns no items."""
    requests_mock.get(API_URL, json={"items": []})

    service = PageviewsService(PageviewsClient())

    with pytest.raises(PageviewsNotFoundError):
        service.get_pageviews(
            "Python",
            lang="en",
            days=30,
            today=date(2024, 2, 1),
        )


def test_pageviews_empty_api_response(requests_mock):
    """Service should reject an empty API response."""
    requests_mock.get(API_URL, json={})

    service = PageviewsService(PageviewsClient())

    with pytest.raises(InvalidApiResponseError):
        service.get_pageviews(
            "Python",
            lang="en",
            days=30,
            today=date(2024, 2, 1),
        )


def test_pageviews_api_timeout(requests_mock):
    """Client should convert timeout to application error."""
    requests_mock.get(API_URL, exc=requests.Timeout)

    service = PageviewsService(PageviewsClient())

    with pytest.raises(ApiRequestError):
        service.get_pageviews(
            "Python",
            lang="en",
            days=30,
            today=date(2024, 2, 1),
        )


def test_ascii_chart_contains_dates_and_views():
    """ASCII chart should contain daily dates and view counts."""
    service = PageviewsService(PageviewsClient())
    items = service._extract_items(_mock_pageviews_response(), "Python")

    chart = ChartRenderer().render_ascii_chart(items)

    assert "2024-01-02" in chart
    assert "100" in chart
    assert "█" in chart


def test_pageviews_png_chart_save(tmp_path: Path):
    """Chart renderer should save PNG chart to file."""
    service = PageviewsService(PageviewsClient())
    items = service._extract_items(_mock_pageviews_response(), "Python")
    output_path = tmp_path / "pageviews.png"

    saved_path = ChartRenderer().save_pageviews_chart(items, output_path)

    assert saved_path == output_path
    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_ascii_chart_uses_english_labels_for_en_language():
    """ASCII chart should use English labels when lang='en'."""
    service = PageviewsService(PageviewsClient())
    items = service._extract_items(_mock_pageviews_response(), "Python")

    chart = ChartRenderer().render_ascii_chart(items, lang="en")

    assert "Pageviews ASCII chart" in chart
    assert "ASCII-график" not in chart


def test_get_pageviews_uses_default_project_language(requests_mock):
    """Pageviews should use en.wikipedia.org internally without CLI --lang."""
    requests_mock.get(API_URL, json=_mock_pageviews_response())

    service = PageviewsService(PageviewsClient())
    result = service.get_pageviews(
        "Python",
        days=30,
        today=date(2024, 2, 1),
    )

    assert result.lang == "en"
    assert "en.wikipedia.org" in result.verbose_info["project"]


def test_pageviews_verbose_uses_standard_logging(requests_mock):
    """--verbose should enable standard logging diagnostics, not a rich table."""
    requests_mock.get(requests_mock_module.ANY, json=_mock_pageviews_response())

    result = CliRunner().invoke(
        cli,
        ["pageviews", "Python", "--days", "30", "--verbose"],
    )

    assert result.exit_code == 0
    assert "INFO Command started: pageviews" in result.output
    assert "INFO Request to Pageviews API:" in result.output
    assert "INFO API response status: 200" in result.output
    assert "INFO Command finished successfully" in result.output
    assert "Verbose" not in result.output


def test_global_verbose_option_enables_pageviews_logging(requests_mock):
    """Global --verbose should work before the command name."""
    requests_mock.get(requests_mock_module.ANY, json=_mock_pageviews_response())

    result = CliRunner().invoke(
        cli,
        ["--verbose", "pageviews", "Python", "--days", "30"],
    )

    assert result.exit_code == 0
    assert "INFO Command started: pageviews" in result.output
    assert "INFO API response status: 200" in result.output
