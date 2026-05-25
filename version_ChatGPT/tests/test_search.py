"""Tests for the `search` command implementation."""

from __future__ import annotations

import pytest
import requests
import requests_mock as requests_mock_module
from click.testing import CliRunner

from wiki_explorer.api.mediawiki_client import MediaWikiClient
from wiki_explorer.cli import cli
from wiki_explorer.exceptions import ApiRequestError, InvalidUserInputError
from wiki_explorer.services.article_service import ArticleService

API_URL = "https://en.wikipedia.org/w/api.php"


def _mock_search_response():
    return {
        "query": {
            "search": [
                {
                    "title": "Python (programming language)",
                    "snippet": '<span class="searchmatch">Python</span> is a programming language.',
                    "size": 123456,
                    "timestamp": "2026-05-01T10:00:00Z",
                },
                {
                    "title": "Python",
                    "snippet": "Python may refer to...",
                    "size": 10000,
                    "timestamp": "2026-04-01T10:00:00Z",
                },
            ]
        }
    }


def test_search_articles_success(requests_mock):
    """Service should return normalized search results."""
    requests_mock.get(API_URL, json=_mock_search_response())

    service = ArticleService(MediaWikiClient())
    result = service.search_articles(
        "Python programming",
        lang="en",
        limit=10,
    )

    assert result.query == "Python programming"
    assert result.lang == "en"
    assert len(result.results) == 2
    assert result.results[0].title == "Python (programming language)"
    assert result.results[0].snippet == "Python is a programming language."
    assert result.results[0].size == 123456

    request = requests_mock.last_request
    assert request.qs["action"] == ["query"]
    assert request.qs["list"] == ["search"]
    assert request.qs["srsearch"] == ["python programming"]
    assert request.qs["srlimit"] == ["10"]
    assert request.qs["srprop"] == ["snippet|size|timestamp"]
    assert request.qs["format"] == ["json"]
    assert request.qs["formatversion"] == ["2"]
    assert request.headers["User-Agent"].startswith("Wiki-Explorer")


def test_search_articles_empty_result(requests_mock):
    """Service should return empty results when nothing is found."""
    requests_mock.get(API_URL, json={"query": {"search": []}})

    service = ArticleService(MediaWikiClient())
    result = service.search_articles("UnknownQuery", lang="en", limit=10)

    assert result.results == []


def test_search_articles_invalid_limit():
    """Service should reject non-positive limit values."""
    service = ArticleService(MediaWikiClient())

    with pytest.raises(InvalidUserInputError):
        service.search_articles("Python", limit=0)


def test_search_articles_invalid_sort():
    """Service should reject unsupported sorting values."""
    service = ArticleService(MediaWikiClient())

    with pytest.raises(InvalidUserInputError):
        service.search_articles("Python", sort="date")


def test_search_articles_api_error(requests_mock):
    """Client should convert request errors to ApiRequestError."""
    requests_mock.get(
        API_URL,
        exc=requests.exceptions.Timeout("timeout"),
    )

    service = ArticleService(MediaWikiClient())

    with pytest.raises(ApiRequestError):
        service.search_articles("Python", lang="en")


def test_search_articles_sort_by_last_edit(requests_mock):
    """Service should sort results by timestamp descending."""
    requests_mock.get(
        API_URL,
        json={
            "query": {
                "search": [
                    {
                        "title": "Old",
                        "snippet": "old",
                        "size": 1,
                        "timestamp": "2024-01-01T00:00:00Z",
                    },
                    {
                        "title": "New",
                        "snippet": "new",
                        "size": 1,
                        "timestamp": "2026-01-01T00:00:00Z",
                    },
                ]
            }
        },
    )

    service = ArticleService(MediaWikiClient())
    result = service.search_articles(
        "Python",
        lang="en",
        limit=10,
        sort="last_edit",
    )

    assert [item.title for item in result.results] == ["New", "Old"]


def test_search_cli_verbose_outputs_logs(requests_mock):
    """Local --verbose should enable logging for the search command."""
    requests_mock.get(API_URL, json=_mock_search_response())

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["search", "Python", "--lang", "en", "--verbose"],
    )

    assert result.exit_code == 0
    assert "Command started: search" in result.output
    assert "Python" in result.output


def test_search_cli_global_verbose_outputs_logs(requests_mock):
    """Global --verbose should also enable logging for the search command."""
    requests_mock.get(API_URL, json=_mock_search_response())

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--verbose", "search", "Python", "--lang", "en"],
    )

    assert result.exit_code == 0
    assert "Command started: search" in result.output
    assert "Python" in result.output
