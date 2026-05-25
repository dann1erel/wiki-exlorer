"""Tests for the `info` command implementation."""

import pytest

from wiki_explorer.api.mediawiki_client import MediaWikiClient
from wiki_explorer.exceptions import (
    ApiRequestError,
    ArticleNotFoundError,
    InvalidApiResponseError,
)
from wiki_explorer.services.article_service import ArticleService


API_URL = "https://en.wikipedia.org/w/api.php"


def test_get_article_info_success(requests_mock):
    """Service should transform successful API response into ArticleInfo."""
    requests_mock.get(
        API_URL,
        json={
            "query": {
                "pages": [
                    {
                        "pageid": 23862,
                        "title": "Python",
                        "length": 120000,
                        "revisions": [
                            {
                                "timestamp": "2026-05-01T10:00:00Z",
                                "user": "ExampleEditor",
                            }
                        ],
                        "categories": [
                            {"title": "Category:Programming languages"},
                            {"title": "Category:Python"},
                        ],
                        "images": [
                            {"title": "File:Python-logo.png"},
                        ],
                    }
                ]
            }
        },
    )

    client = MediaWikiClient()
    service = ArticleService(client)

    result = service.get_info(
        "Python",
        lang="en",
        include_categories=True,
        include_images=True,
    )

    assert result.title == "Python"
    assert result.page_id == 23862
    assert result.size_bytes == 120000
    assert result.last_editor == "ExampleEditor"
    assert result.categories == [
        "Category:Programming languages",
        "Category:Python",
    ]
    assert result.images == ["File:Python-logo.png"]
    assert result.url == "https://en.wikipedia.org/wiki/Python"

    request = requests_mock.last_request
    assert request.qs["action"] == ["query"]
    assert request.qs["prop"] == ["info|revisions|categories|images"]
    assert request.qs["titles"] == ["python"]
    assert request.qs["rvprop"] == ["timestamp|user"]
    assert request.qs["cllimit"] == ["10"]
    assert request.qs["format"] == ["json"]
    assert request.qs["formatversion"] == ["2"]


def test_get_article_info_article_not_found(requests_mock):
    """Service should raise ArticleNotFoundError for missing pages."""
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
        service.get_info("UnknownArticle123", lang="en")


def test_get_article_info_empty_api_response(requests_mock):
    """Client should raise InvalidApiResponseError for empty JSON."""
    requests_mock.get(API_URL, json={})

    service = ArticleService(MediaWikiClient())

    with pytest.raises(InvalidApiResponseError):
        service.get_info("Python", lang="en")


def test_get_article_info_api_error(requests_mock):
    """Client should raise ApiRequestError for HTTP errors."""
    requests_mock.get(API_URL, status_code=500)

    service = ArticleService(MediaWikiClient())

    with pytest.raises(ApiRequestError):
        service.get_info("Python", lang="en")
