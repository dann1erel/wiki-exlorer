"""Тесты для команды categories."""

from click.testing import CliRunner
import pytest
from wiki_explorer.cli import main
from wiki_explorer.utils.errors import NotFoundError, ApiError, NetworkError


def test_categories_success_without_tree():
    """Вывод плоского списка категорий (без --tree)."""
    runner = CliRunner()
    with pytest.MonkeyPatch.context() as mp:
        def mock_get_categories(title, lang):
            return ["Programming languages", "Software", "Python"]
        mp.setattr("wiki_explorer.commands.categories.get_categories", mock_get_categories)
        result = runner.invoke(main, ["--lang", "en", "categories", "Python"])
        assert result.exit_code == 0
        assert "Категории статьи 'Python'" in result.output
        assert "1" in result.output
        assert "Programming languages" in result.output
        assert "Software" in result.output
        assert "Python" in result.output


def test_categories_success_with_tree():
    """Вывод категорий с родителями (--tree)."""
    runner = CliRunner()
    with pytest.MonkeyPatch.context() as mp:
        def mock_get_categories(title, lang):
            return ["Programming languages", "Software", "Python"]
        def mock_get_parent_categories(cats, lang):
            return {
                "Programming languages": "Computer science",
                "Software": None,
                "Python": "Programming languages"
            }
        mp.setattr("wiki_explorer.commands.categories.get_categories", mock_get_categories)
        mp.setattr("wiki_explorer.commands.categories.get_parent_categories", mock_get_parent_categories)
        result = runner.invoke(main, ["categories", "Python", "--tree"])
        assert result.exit_code == 0
        assert "Категории статьи 'Python' (с родителями)" in result.output
        assert "Programming languages" in result.output
        assert "Computer science" in result.output
        assert "Software" in result.output
        assert "—" in result.output  # для родителя None
        assert "Python" in result.output


def test_categories_empty():
    """Статья без категорий."""
    runner = CliRunner()
    with pytest.MonkeyPatch.context() as mp:
        def mock_get_categories(title, lang):
            return []
        mp.setattr("wiki_explorer.commands.categories.get_categories", mock_get_categories)
        result = runner.invoke(main, ["categories", "EmptyArticle"])
        assert result.exit_code == 0
        assert "Категории отсутствуют" in result.output


def test_categories_not_found():
    """Статья не найдена."""
    runner = CliRunner()
    with pytest.MonkeyPatch.context() as mp:
        def mock_get_categories(title, lang):
            raise NotFoundError("Статья 'NotFound' не найдена")
        mp.setattr("wiki_explorer.commands.categories.get_categories", mock_get_categories)
        result = runner.invoke(main, ["categories", "NotFound"])
        assert result.exit_code == 1
        assert "Ошибка: Статья 'NotFound' не найдена" in result.output


def test_categories_api_error():
    """Ошибка API при получении категорий."""
    runner = CliRunner()
    with pytest.MonkeyPatch.context() as mp:
        def mock_get_categories(title, lang):
            raise ApiError("API limit exceeded")
        mp.setattr("wiki_explorer.commands.categories.get_categories", mock_get_categories)
        result = runner.invoke(main, ["categories", "Python"])
        assert result.exit_code == 1
        assert "Ошибка API/сети: API limit exceeded" in result.output


def test_categories_network_error():
    """Сетевая ошибка при получении категорий."""
    runner = CliRunner()
    with pytest.MonkeyPatch.context() as mp:
        def mock_get_categories(title, lang):
            raise NetworkError("Connection timeout")
        mp.setattr("wiki_explorer.commands.categories.get_categories", mock_get_categories)
        result = runner.invoke(main, ["categories", "Python"])
        assert result.exit_code == 1
        assert "Ошибка API/сети: Connection timeout" in result.output


def test_categories_tree_parents_api_error():
    """Ошибка API при получении родительских категорий (--tree)."""
    runner = CliRunner()
    with pytest.MonkeyPatch.context() as mp:
        def mock_get_categories(title, lang):
            return ["Cat1", "Cat2"]
        def mock_get_parent_categories(cats, lang):
            raise ApiError("Failed to fetch parents")
        mp.setattr("wiki_explorer.commands.categories.get_categories", mock_get_categories)
        mp.setattr("wiki_explorer.commands.categories.get_parent_categories", mock_get_parent_categories)
        result = runner.invoke(main, ["categories", "Python", "--tree"])
        assert result.exit_code == 1
        assert "Ошибка при получении родительских категорий: Failed to fetch parents" in result.output


def test_categories_verbose_unexpected_error():
    """Неожиданная ошибка с verbose."""
    runner = CliRunner()
    with pytest.MonkeyPatch.context() as mp:
        def mock_get_categories(title, lang):
            raise ValueError("Unexpected value")
        mp.setattr("wiki_explorer.commands.categories.get_categories", mock_get_categories)
        # Запускаем с --verbose, чтобы проверить вывод traceback
        result = runner.invoke(main, ["--verbose", "categories", "Python"])
        assert result.exit_code == 1
        # При verbose ошибка не перехватывается, а выводится через console.print_exception()
        # Можно проверить, что в выводе есть traceback (например, "Traceback")
        assert "Traceback" in result.output or "Unexpected value" in result.output