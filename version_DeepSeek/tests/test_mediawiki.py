"""Тесты для api/mediawiki.py."""

import pytest
import requests
from unittest.mock import Mock, patch
from wiki_explorer.api.mediawiki import (
    fetch_article_info,
    fetch_image_url,
    _make_request,
)
from wiki_explorer.utils.errors import NotFoundError, ApiError, NetworkError


SAMPLE_RESPONSE = {
    "query": {
        "pages": {
            "12345": {
                "pageid": 12345,
                "ns": 0,
                "title": "Python",
                "info": {
                    "size": 123456,
                    "links": 789,
                },
                "revisions": [
                    {
                        "timestamp": "2025-05-24T10:00:00Z",
                        "user": "LastEditor",
                        "size": 123456,
                    },
                    {
                        "timestamp": "2000-01-01T00:00:00Z",
                        "user": "FirstEditor",
                        "size": 100,
                    },
                ],
                "categories": [
                    {"title": "Category:Programming languages"},
                    {"title": "Category:Software"},
                ],
                "images": [
                    {"title": "File:Python_logo.svg"},
                ],
            }
        }
    }
}


def test_fetch_article_info_success():
    """Успешное получение информации о статье."""
    with patch("wiki_explorer.api.mediawiki._make_request") as mock_request:
        mock_request.return_value = SAMPLE_RESPONSE
        result = fetch_article_info("Python", "en")
        assert result["title"] == "Python"
        assert result["size"] == 123456
        assert result["links"] == 789
        assert result["created"] == "2000-01-01T00:00:00Z"
        assert result["last_modified"] == "2025-05-24T10:00:00Z"
        assert result["last_editor"] == "LastEditor"
        assert result["categories"] == ["Programming languages", "Software"]
        assert result["image_title"] == "File:Python_logo.svg"


def test_fetch_article_info_not_found():
    """Статья не найдена -> NotFoundError."""
    not_found_response = {
        "query": {
            "pages": {
                "-1": {
                    "title": "Nonexistent",
                    "missing": ""
                }
            }
        }
    }
    with patch("wiki_explorer.api.mediawiki._make_request") as mock_request:
        mock_request.return_value = not_found_response
        with pytest.raises(NotFoundError, match="Nonexistent.*не найдена"):
            fetch_article_info("Nonexistent", "en")


def test_fetch_article_info_no_revisions():
    """Статья без ревизий (редко, но обрабатываем)."""
    response_no_revisions = {
        "query": {
            "pages": {
                "123": {
                    "title": "Empty",
                    "info": {"size": 0, "links": 0},
                }
            }
        }
    }
    with patch("wiki_explorer.api.mediawiki._make_request") as mock_request:
        mock_request.return_value = response_no_revisions
        result = fetch_article_info("Empty", "en")
        assert result["created"] == ""
        assert result["last_modified"] == ""
        assert result["last_editor"] == ""


def test_fetch_article_info_no_categories_or_images():
    """Статья без категорий и изображений."""
    response_minimal = {
        "query": {
            "pages": {
                "123": {
                    "title": "Minimal",
                    "info": {"size": 100, "links": 2},
                    "revisions": [{"timestamp": "2025-01-01T00:00:00Z", "user": "U"}],
                }
            }
        }
    }
    with patch("wiki_explorer.api.mediawiki._make_request") as mock_request:
        mock_request.return_value = response_minimal
        result = fetch_article_info("Minimal", "en")
        assert result["categories"] == []
        assert result["image_title"] is None


def test_fetch_article_info_bad_response():
    """Некорректный ответ API -> ApiError."""
    with patch("wiki_explorer.api.mediawiki._make_request") as mock_request:
        mock_request.return_value = {}  # нет query.pages
        with pytest.raises(ApiError, match="не содержит поле 'query.pages'"):
            fetch_article_info("Any", "en")


def test_fetch_image_url_success():
    """Успешное получение URL изображения."""
    image_response = {
        "query": {
            "pages": {
                "999": {
                    "imageinfo": [{"url": "https://upload.wikimedia.org/.../logo.svg"}]
                }
            }
        }
    }
    with patch("wiki_explorer.api.mediawiki._make_request") as mock_request:
        mock_request.return_value = image_response
        url = fetch_image_url("File:Logo.svg", "en")
        assert url == "https://upload.wikimedia.org/.../logo.svg"


def test_fetch_image_url_not_found():
    """Изображение не найдено -> возвращает None."""
    empty_response = {"query": {"pages": {"-1": {"missing": ""}}}}
    with patch("wiki_explorer.api.mediawiki._make_request") as mock_request:
        mock_request.return_value = empty_response
        url = fetch_image_url("File:Missing.svg", "en")
        assert url is None


def test_fetch_image_url_network_error():
    """Сетевая ошибка при запросе изображения -> возвращает None (не падаем)."""
    with patch("wiki_explorer.api.mediawiki._make_request") as mock_request:
        mock_request.side_effect = NetworkError("Network problem")
        url = fetch_image_url("File:Some.svg", "en")
        assert url is None


def test_make_request_retries_on_network_error():
    """Проверка повторных попыток при сетевой ошибке."""
    with patch("requests.get") as mock_get:
        mock_get.side_effect = requests.exceptions.ConnectionError("No net")
        with pytest.raises(NetworkError, match="Сетевая ошибка после 3 попыток"):
            _make_request("https://test.com", {})
        assert mock_get.call_count == 3


def test_make_request_retries_on_http_error():
    """Повторные попытки при HTTP ошибке 5xx."""
    with patch("requests.get") as mock_get:
        mock_get.side_effect = requests.exceptions.HTTPError("500 Server Error")
        with pytest.raises(NetworkError):
            _make_request("https://test.com", {})
        assert mock_get.call_count == 3