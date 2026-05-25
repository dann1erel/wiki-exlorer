"""Tests for the `categories` command implementation."""

from __future__ import annotations

import pytest

from wiki_explorer.api.mediawiki_client import MediaWikiClient
from wiki_explorer.exceptions import ArticleNotFoundError, InvalidApiResponseError
from wiki_explorer.services.article_service import ArticleService

API_URL = "https://en.wikipedia.org/w/api.php"


def _mock_categories_response(
    title: str = "Python",
    categories: list[str] | None = None,
):
    return {
        "query": {
            "pages": [
                {
                    "pageid": 23862,
                    "ns": 0,
                    "title": title,
                    "categories": [
                        {"ns": 14, "title": category}
                        for category in (categories or [])
                    ],
                }
            ]
        }
    }


def _mock_subcategories_response(subcategories: list[str] | None = None):
    return {
        "query": {
            "categorymembers": [
                {"pageid": index, "ns": 14, "title": category}
                for index, category in enumerate(subcategories or [], start=1)
            ]
        }
    }


def test_get_article_categories_success(requests_mock):
    """Service should return categories from a successful API response."""
    requests_mock.get(
        API_URL,
        json=_mock_categories_response(
            categories=[
                "Category:Python",
                "Category:Programming languages",
                "Category:Object-oriented programming languages",
            ]
        ),
    )

    service = ArticleService(MediaWikiClient())

    result = service.get_categories("Python", lang="en", limit=20)

    assert result.title == "Python"
    assert result.page_id == 23862
    assert result.categories == [
        "Category:Python",
        "Category:Programming languages",
        "Category:Object-oriented programming languages",
    ]
    assert result.tree == {}

    request = requests_mock.last_request
    assert request.qs["action"] == ["query"]
    assert request.qs["prop"] == ["categories"]
    assert request.qs["titles"] == ["python"]
    assert request.qs["cllimit"] == ["20"]
    assert request.qs["format"] == ["json"]
    assert request.qs["formatversion"] == ["2"]
    assert request.headers["User-Agent"].startswith("Wiki-Explorer")


def test_get_article_categories_article_not_found(requests_mock):
    """Service should raise ArticleNotFoundError for missing page."""
    requests_mock.get(
        API_URL,
        json={
            "query": {
                "pages": [
                    {
                        "ns": 0,
                        "title": "UnknownArticle123",
                        "missing": True,
                    }
                ]
            }
        },
    )

    service = ArticleService(MediaWikiClient())

    with pytest.raises(ArticleNotFoundError):
        service.get_categories("UnknownArticle123", lang="en")


def test_get_article_categories_empty_list(requests_mock):
    """Service should return an empty list when article has no categories."""
    requests_mock.get(API_URL, json=_mock_categories_response(categories=[]))

    service = ArticleService(MediaWikiClient())

    result = service.get_categories("Python", lang="en", limit=20)

    assert result.categories == []


def test_get_article_categories_tree(requests_mock):
    """Tree mode should map categories to their direct subcategories."""
    requests_mock.get(
        API_URL,
        [
            {
                "json": _mock_categories_response(
                    categories=[
                        "Category:Python",
                        "Category:Programming languages",
                    ]
                )
            },
            {
                "json": _mock_subcategories_response(
                    ["Category:Python implementations"]
                )
            },
            {
                "json": _mock_subcategories_response(
                    [
                        "Category:Object-oriented programming languages",
                        "Category:Scripting languages",
                    ]
                )
            },
        ],
    )

    service = ArticleService(MediaWikiClient())

    result = service.get_categories("Python", lang="en", limit=10, tree=True)

    assert result.categories == [
        "Category:Python",
        "Category:Programming languages",
    ]
    assert result.tree == {
        "Category:Python": ["Category:Python implementations"],
        "Category:Programming languages": [
            "Category:Object-oriented programming languages",
            "Category:Scripting languages",
        ],
    }


def test_get_article_categories_invalid_limit():
    """Service should reject non-positive limit values."""
    service = ArticleService(MediaWikiClient())

    with pytest.raises(ValueError, match="--limit"):
        service.get_categories("Python", lang="en", limit=0)


def test_get_article_categories_empty_api_response(requests_mock):
    """Client should raise InvalidApiResponseError for empty JSON."""
    requests_mock.get(API_URL, json={})

    service = ArticleService(MediaWikiClient())

    with pytest.raises(InvalidApiResponseError):
        service.get_categories("Python", lang="en")
