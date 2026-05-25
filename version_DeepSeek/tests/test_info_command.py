"""Тесты для команды info."""

from click.testing import CliRunner
import pytest
from wiki_explorer.cli import main
from wiki_explorer.commands.info import info
from wiki_explorer.utils.errors import NotFoundError, NetworkError, ApiError


def test_info_command_success_without_options():
    """Базовая команда без опций."""
    runner = CliRunner()
    with pytest.MonkeyPatch.context() as mp:
        # Мокаем fetch_article_info, чтобы не ходить в сеть
        def mock_fetch(*args, **kwargs):
            return {
                "title": "Python",
                "size": 12345,
                "links": 100,
                "created": "2000-01-01T00:00:00Z",
                "last_modified": "2025-05-24T10:00:00Z",
                "last_editor": "LastEditor",
                "categories": ["Programming", "Software"],
                "image_title": "File:Logo.svg",
            }
        mp.setattr("wiki_explorer.commands.info.fetch_article_info", mock_fetch)
        result = runner.invoke(main, ["--lang", "en", "info", "Python"])
        assert result.exit_code == 0
        assert "Информация о статье: Python" in result.output
        assert "Размер (байт)" in result.output
        assert "Последний редактор" in result.output


def test_info_command_with_categories():
    """Опция --show-categories."""
    runner = CliRunner()
    with pytest.MonkeyPatch.context() as mp:
        def mock_fetch(*args, **kwargs):
            return {
                "title": "Python",
                "size": 12345,
                "links": 100,
                "created": "",
                "last_modified": "",
                "last_editor": "",
                "categories": ["Programming", "Software", "Third"],
                "image_title": None,
            }
        mp.setattr("wiki_explorer.commands.info.fetch_article_info", mock_fetch)
        result = runner.invoke(main, ["--lang", "en", "info", "Python", "--show-categories"])
        assert result.exit_code == 0
        assert "Категории (первые 10)" in result.output
        assert "• Programming" in result.output


def test_info_command_with_image_url():
    """Опция --show-image-url."""
    runner = CliRunner()
    with pytest.MonkeyPatch.context() as mp:
        def mock_fetch(*args, **kwargs):
            return {
                "title": "Python",
                "size": 12345,
                "links": 100,
                "created": "",
                "last_modified": "",
                "last_editor": "",
                "categories": [],
                "image_title": "File:Logo.svg",
            }
        def mock_image_url(*args, **kwargs):
            return "https://example.com/logo.png"
        mp.setattr("wiki_explorer.commands.info.fetch_article_info", mock_fetch)
        mp.setattr("wiki_explorer.commands.info.fetch_image_url", mock_image_url)
        result = runner.invoke(main, ["--lang", "en", "info", "Python", "--show-image-url"])
        assert result.exit_code == 0
        assert "URL главного изображения" in result.output
        assert "https://example.com/logo.png" in result.output


def test_info_command_not_found_error():
    """Статья не найдена -> exit code 1."""
    runner = CliRunner()
    with pytest.MonkeyPatch.context() as mp:
        def mock_fetch(*args, **kwargs):
            raise NotFoundError("Статья не найдена")
        mp.setattr("wiki_explorer.commands.info.fetch_article_info", mock_fetch)
        result = runner.invoke(main, ["--lang", "en", "info", "Nonexistent"])
        assert result.exit_code == 1
        assert "Ошибка: Статья не найдена" in result.output


def test_info_command_network_error():
    """Сетевая ошибка -> exit code 1."""
    runner = CliRunner()
    with pytest.MonkeyPatch.context() as mp:
        def mock_fetch(*args, **kwargs):
            raise NetworkError("Network problem")
        mp.setattr("wiki_explorer.commands.info.fetch_article_info", mock_fetch)
        result = runner.invoke(main, ["--lang", "en", "info", "Python"])
        assert result.exit_code == 1
        assert "Сетевая ошибка: Network problem" in result.output