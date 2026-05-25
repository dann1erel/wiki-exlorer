"""Tests for the graph command business logic."""

from __future__ import annotations

from pathlib import Path

import pytest

from wiki_explorer.exceptions import ArticleNotFoundError, NoLinksFoundError
from wiki_explorer.services.article_service import ArticleService
from wiki_explorer.services.graph_service import GraphService

API_URL = "https://en.wikipedia.org/w/api.php"


def _mock_links_response(title: str = "Python", links: list[str] | None = None):
    return {
        "query": {
            "pages": [
                {
                    "pageid": 23862,
                    "ns": 0,
                    "title": title,
                    "links": [
                        {"ns": 0, "title": link}
                        for link in (links or [])
                    ],
                }
            ]
        }
    }


def test_graph_edges_success(requests_mock):
    """Graph service should build edge list from article links."""
    requests_mock.get(
        API_URL,
        json=_mock_links_response(
            links=["Programming language", "Guido van Rossum", "Software"]
        ),
    )

    service = GraphService(article_service=ArticleService())
    graph_data = service.get_graph_data("Python", "en", 3)

    assert graph_data.source_title == "Python"
    assert graph_data.edges == [
        ("Python", "Programming language"),
        ("Python", "Guido van Rossum"),
        ("Python", "Software"),
    ]


def test_graph_article_not_found(requests_mock):
    """Graph command should reuse article not found handling."""
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

    service = GraphService(article_service=ArticleService())

    with pytest.raises(ArticleNotFoundError):
        service.get_graph_data("UnknownArticle123", "en", 10)


def test_graph_no_links(requests_mock):
    """Graph service should report when there are no links to draw."""
    requests_mock.get(API_URL, json=_mock_links_response(links=[]))

    service = GraphService(article_service=ArticleService())

    with pytest.raises(NoLinksFoundError):
        service.get_graph_data("Python", "en", 10)


def test_graph_invalid_format(requests_mock):
    """Graph service should reject unsupported output format."""
    requests_mock.get(
        API_URL,
        json=_mock_links_response(links=["Programming language"]),
    )

    service = GraphService(article_service=ArticleService())
    graph_data = service.get_graph_data("Python", "en", 1)

    with pytest.raises(ValueError, match="png или pdf"):
        service.save_graph(graph_data, "graph.jpg", "jpg")


def test_graph_save_to_file(requests_mock, tmp_path: Path):
    """Graph service should save graph file to temporary directory."""
    requests_mock.get(
        API_URL,
        json=_mock_links_response(
            links=["Programming language", "Guido van Rossum"]
        ),
    )

    service = GraphService(article_service=ArticleService())
    graph_data = service.get_graph_data("Python", "en", 2)
    output_path = tmp_path / "graph.png"

    saved_path = service.save_graph(graph_data, output_path, "png")

    assert saved_path == output_path
    assert output_path.exists()
    assert output_path.stat().st_size > 0


class FakeArticleService:
    """Simple fake article service for graph depth tests."""

    def __init__(self, responses: dict[str, list[str]]) -> None:
        self.responses = responses
        self.calls: list[str] = []

    def get_links(self, title: str, lang: str, limit: int, search=None):
        self.calls.append(title)
        return __import__(
            "wiki_explorer.services.article_service",
            fromlist=["ArticleLinks"],
        ).ArticleLinks(
            title=title,
            page_id=1,
            links=self.responses.get(title, [])[:limit],
        )


def test_graph_depth_two_builds_second_level_edges():
    """Depth 2 should add edges from first-level pages to their links."""
    fake_service = FakeArticleService(
        {
            "Python": ["Programming language", "Guido van Rossum"],
            "Programming language": ["Compiler", "Interpreter"],
            "Guido van Rossum": ["Netherlands"],
        }
    )
    service = GraphService(article_service=fake_service)

    graph_data = service.get_graph_data("Python", "en", 2, depth=2)

    assert graph_data.depth == 2
    assert graph_data.edges == [
        ("Python", "Programming language"),
        ("Python", "Guido van Rossum"),
        ("Programming language", "Compiler"),
        ("Programming language", "Interpreter"),
        ("Guido van Rossum", "Netherlands"),
    ]


def test_graph_depth_one_does_not_request_second_level_links():
    """Depth 1 should keep previous graph behavior unchanged."""
    fake_service = FakeArticleService(
        {
            "Python": ["Programming language", "Guido van Rossum"],
            "Programming language": ["Compiler"],
        }
    )
    service = GraphService(article_service=fake_service)

    graph_data = service.get_graph_data("Python", "en", 2, depth=1)

    assert fake_service.calls == ["Python"]
    assert graph_data.edges == [
        ("Python", "Programming language"),
        ("Python", "Guido van Rossum"),
    ]


def test_graph_invalid_depth():
    """Graph service should reject unsupported depth values."""
    fake_service = FakeArticleService({"Python": ["Programming language"]})
    service = GraphService(article_service=fake_service)

    with pytest.raises(ValueError, match="--depth"):
        service.get_graph_data("Python", "en", 1, depth=3)


def test_graph_depth_two_truncates_too_large_graph(monkeypatch):
    """Large depth 2 graphs should be truncated instead of growing forever."""
    from wiki_explorer.services import graph_service as graph_service_module

    monkeypatch.setattr(graph_service_module, "DEFAULT_GRAPH_MAX_NODES", 4)

    fake_service = FakeArticleService(
        {
            "Python": ["A", "B", "C"],
            "A": ["A1", "A2"],
            "B": ["B1"],
        }
    )
    service = GraphService(article_service=fake_service)

    graph_data = service.get_graph_data("Python", "en", 3, depth=2)

    assert graph_data.is_truncated is True
    assert graph_data.edges == [
        ("Python", "A"),
        ("Python", "B"),
        ("Python", "C"),
    ]


def test_graph_data_marks_second_level_nodes_and_edges():
    """Graph data should distinguish first- and second-level links."""
    fake_service = FakeArticleService(
        {
            "Python": ["Programming language"],
            "Programming language": ["Compiler", "Interpreter"],
        }
    )
    service = GraphService(article_service=fake_service)

    graph_data = service.get_graph_data("Python", "en", 2, depth=2)

    assert graph_data.get_edge_level(("Python", "Programming language")) == 1
    assert graph_data.get_edge_level(("Programming language", "Compiler")) == 2
    assert graph_data.first_level_nodes == {"Programming language"}
    assert graph_data.second_level_nodes == {"Compiler", "Interpreter"}
