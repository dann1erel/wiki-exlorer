"""Tests for the `random` command implementation."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from wiki_explorer.api.mediawiki_client import MediaWikiClient
from wiki_explorer.cli import cli
from wiki_explorer.exceptions import (
    InvalidUserInputError,
    NoCategoryMembersError,
    RandomArticleNotFoundError,
)
from wiki_explorer.services import article_service as article_service_module
from wiki_explorer.services.article_service import ArticleService

API_URL = "https://en.wikipedia.org/w/api.php"
RU_API_URL = "https://ru.wikipedia.org/w/api.php"


def _random_response(title: str = "Python") -> dict:
    return {
        "query": {
            "random": [
                {
                    "id": 23862,
                    "ns": 0,
                    "title": title,
                }
            ]
        }
    }


def _summary_response(
    title: str = "Python",
    pageid: int = 23862,
    length: int = 12000,
    images: list[dict] | None = None,
) -> dict:
    page = {
        "pageid": pageid,
        "title": title,
        "length": length,
        "fullurl": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
    }
    if images is not None:
        page["images"] = images

    return {"query": {"pages": [page]}}


def _category_response(*titles: str) -> dict:
    return {
        "query": {
            "categorymembers": [
                {"pageid": index + 1, "ns": 0, "title": title}
                for index, title in enumerate(titles)
            ]
        }
    }


def test_get_random_article_without_category_success(requests_mock):
    """Service should fetch a random article and then its summary info."""
    requests_mock.get(
        API_URL,
        [
            {"json": _random_response("Python")},
            {
                "json": _summary_response(
                    "Python",
                    images=[{"title": "File:Python-logo.png"}],
                )
            },
        ],
    )

    service = ArticleService(MediaWikiClient())
    article = service.get_random_article(lang="en")

    assert article.title == "Python"
    assert article.page_id == 23862
    assert article.size_bytes == 12000
    assert article.words_count == 2000
    assert article.has_image is True
    assert article.first_image == "File:Python-logo.png"
    assert article.url == "https://en.wikipedia.org/wiki/Python"


def test_get_random_article_from_category_success(requests_mock):
    """Service should pick a random article from category members."""
    requests_mock.get(
        API_URL,
        [
            {"json": _category_response("Python")},
            {"json": _summary_response("Python")},
        ],
    )

    service = ArticleService(MediaWikiClient())
    article = service.get_random_article(
        lang="en",
        category="Science",
    )

    assert article.title == "Python"
    assert article.category == "Category:Science"

    first_request = requests_mock.request_history[0]
    assert first_request.qs["list"] == ["categorymembers"]
    assert first_request.qs["cmtitle"] == ["category:science"]
    assert first_request.qs["cmtype"] == ["page"]


def test_get_random_article_empty_category(requests_mock):
    """Empty category should be converted to user-friendly error."""
    requests_mock.get(API_URL, json=_category_response())

    service = ArticleService(MediaWikiClient())

    with pytest.raises(NoCategoryMembersError):
        service.get_random_article(lang="en", category="Empty")


def test_get_random_article_invalid_min_words():
    """Service should reject non-positive min_words."""
    service = ArticleService(MediaWikiClient())

    with pytest.raises(InvalidUserInputError):
        service.get_random_article(lang="en", min_words=0)


def test_get_random_article_with_image_skips_articles_without_image(requests_mock):
    """with_image filter should skip articles without images."""
    requests_mock.get(
        API_URL,
        [
            {"json": _random_response("No image")},
            {"json": _summary_response("No image", images=[])},
            {"json": _random_response("With image")},
            {
                "json": _summary_response(
                    "With image",
                    images=[{"title": "File:Example.png"}],
                )
            },
        ],
    )

    service = ArticleService(MediaWikiClient())
    article = service.get_random_article(lang="en", with_image=True)

    assert article.title == "With image"
    assert article.has_image is True
    assert article.attempts_used == 2


def test_get_random_article_filters_fail_after_max_attempts(
    requests_mock,
    monkeypatch,
):
    """Service should stop after configured attempt limit."""
    monkeypatch.setattr(article_service_module, "DEFAULT_RANDOM_ATTEMPTS", 2)
    requests_mock.get(
        API_URL,
        [
            {"json": _category_response("Small article")},
            {"json": _summary_response("Small article", length=60)},
            {"json": _summary_response("Small article", length=60)},
        ],
    )

    service = ArticleService(MediaWikiClient())

    with pytest.raises(RandomArticleNotFoundError):
        service.get_random_article(
            lang="en",
            category="Science",
            min_words=1000,
        )


def test_random_category_prefix_ru_and_en():
    """Category prefix helper should use localized prefixes."""
    service = ArticleService(MediaWikiClient())

    assert service._normalize_category_title("Наука", "ru") == "Категория:Наука"
    assert service._normalize_category_title("Science", "en") == "Category:Science"
    assert (
        service._normalize_category_title("Category:Science", "en")
        == "Category:Science"
    )


def test_random_cli_verbose_outputs_logs(requests_mock):
    """Local --verbose should enable logging for the random command."""
    requests_mock.get(
        API_URL,
        [
            {"json": _random_response("Python")},
            {"json": _summary_response("Python")},
        ],
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["random", "--lang", "en", "--verbose"])

    assert result.exit_code == 0
    assert "Command started: random" in result.output
    assert "Python" in result.output


def test_random_cli_global_verbose_outputs_logs(requests_mock):
    """Global --verbose should enable logging for the random command."""
    requests_mock.get(
        API_URL,
        [
            {"json": _random_response("Python")},
            {"json": _summary_response("Python")},
        ],
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["--verbose", "random", "--lang", "en"])

    assert result.exit_code == 0
    assert "Command started: random" in result.output
    assert "Python" in result.output
