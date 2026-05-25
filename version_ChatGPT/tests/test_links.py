"""Tests for the `links` command implementation."""

import pytest

from wiki_explorer.api.mediawiki_client import MediaWikiClient
from wiki_explorer.exceptions import ArticleNotFoundError, InvalidApiResponseError
from wiki_explorer.services.article_service import ArticleService


API_URL = "https://en.wikipedia.org/w/api.php"


def test_get_article_links_success(requests_mock):
    """Service should return internal links from a successful API response."""
    requests_mock.get(
        API_URL,
        json={
            "query": {
                "pages": [
                    {
                        "pageid": 23862,
                        "title": "Python",
                        "links": [
                            {"title": "Computer programming"},
                            {"title": "Guido van Rossum"},
                            {"title": "Programming language"},
                        ],
                    }
                ]
            }
        },
    )

    service = ArticleService(MediaWikiClient())

    result = service.get_links("Python", lang="en", limit=50)

    assert result.title == "Python"
    assert result.page_id == 23862
    assert result.links == [
        "Computer programming",
        "Guido van Rossum",
        "Programming language",
    ]

    request = requests_mock.last_request
    assert request.qs["action"] == ["query"]
    assert request.qs["prop"] == ["links"]
    assert request.qs["titles"] == ["python"]
    assert request.qs["pllimit"] == ["50"]
    assert request.qs["format"] == ["json"]
    assert request.qs["formatversion"] == ["2"]
    assert request.headers["User-Agent"].startswith("Wiki-Explorer")


def test_get_article_links_article_not_found(requests_mock):
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
        service.get_links("UnknownArticle123", lang="en")


def test_get_article_links_filter_by_search(requests_mock):
    """Service should filter links by part of title case-insensitively."""
    requests_mock.get(
        API_URL,
        json={
            "query": {
                "pages": [
                    {
                        "pageid": 23862,
                        "title": "Python",
                        "links": [
                            {"title": "Computer programming"},
                            {"title": "Guido van Rossum"},
                            {"title": "Programming language"},
                            {"title": "Software"},
                        ],
                    }
                ]
            }
        },
    )

    service = ArticleService(MediaWikiClient())

    result = service.get_links(
        "Python",
        lang="en",
        limit=50,
        search="programming",
    )

    assert result.links == [
        "Computer programming",
        "Programming language",
    ]


def test_get_article_links_empty_list(requests_mock):
    """Service should return an empty list when article has no links."""
    requests_mock.get(
        API_URL,
        json={
            "query": {
                "pages": [
                    {
                        "pageid": 123,
                        "title": "Small article",
                        "links": [],
                    }
                ]
            }
        },
    )

    service = ArticleService(MediaWikiClient())

    result = service.get_links("Small article", lang="en", limit=50)

    assert result.links == []


def test_get_article_links_empty_api_response(requests_mock):
    """Client should raise InvalidApiResponseError for empty JSON."""
    requests_mock.get(API_URL, json={})

    service = ArticleService(MediaWikiClient())

    with pytest.raises(InvalidApiResponseError):
        service.get_links("Python", lang="en")
