"""Тесты для команды search."""

from click.testing import CliRunner
import pytest
from wiki_explorer.cli import main
from wiki_explorer.utils.errors import ApiError, NetworkError


def test_search_success_basic():
    """Базовая команда поиска."""
    runner = CliRunner()
    with pytest.MonkeyPatch.context() as mp:
        def mock_search(query, lang, limit, sort, namespace):
            return {
                "search": [
                    {
                        "title": "Python (programming language)",
                        "snippet": "Python is an interpreted high-level programming language.",
                        "timestamp": "2025-05-24T10:00:00Z"
                    },
                    {
                        "title": "Python (genus)",
                        "snippet": "Python is a genus of constricting snakes.",
                        "timestamp": "2025-05-23T08:00:00Z"
                    }
                ]
            }
        mp.setattr("wiki_explorer.commands.search.search_articles", mock_search)
        result = runner.invoke(main, ["--lang", "en", "search", "python"])
        assert result.exit_code == 0
        assert "Результаты поиска: 'python'" in result.output
        # Проверяем фрагменты заголовков (из-за переносов)
        assert "Python (programming" in result.output
        assert "language)" in result.output
        assert "Python (genus)" in result.output
        # Проверяем фрагменты сниппетов (по частям)
        assert "interpreted" in result.output
        assert "high-level programming" in result.output  # часть до разрыва
        assert "language" in result.output               # часть после разрыва
        assert "constricting snakes" in result.output
        # Проверяем даты
        assert "2025-05-24 10:00:00" in result.output
        assert "2025-05-23 08:00:00" in result.output
        


def test_search_with_limit():
    """Опция --limit."""
    runner = CliRunner()
    with pytest.MonkeyPatch.context() as mp:
        mock_called = {}
        def mock_search(query, lang, limit, sort, namespace):
            mock_called['limit'] = limit
            return {"search": [{"title": "Test", "snippet": "", "timestamp": ""}]}
        mp.setattr("wiki_explorer.commands.search.search_articles", mock_search)
        result = runner.invoke(main, ["search", "test", "--limit", "5"])
        assert result.exit_code == 0
        assert mock_called['limit'] == 5


def test_search_limit_exceeds_max():
    """--limit больше 100 -> предупреждение и ограничение до 100."""
    runner = CliRunner()
    with pytest.MonkeyPatch.context() as mp:
        mock_called = {}
        def mock_search(query, lang, limit, sort, namespace):
            mock_called['limit'] = limit
            return {"search": []}
        mp.setattr("wiki_explorer.commands.search.search_articles", mock_search)
        result = runner.invoke(main, ["search", "test", "--limit", "150"])
        assert result.exit_code == 0
        assert "Внимание: максимальное значение --limit ограничено 100" in result.output
        assert mock_called['limit'] == 100


def test_search_with_sort():
    """Опция --sort."""
    runner = CliRunner()
    with pytest.MonkeyPatch.context() as mp:
        mock_called = {}
        def mock_search(query, lang, limit, sort, namespace):
            mock_called['sort'] = sort
            return {"search": [{"title": "Test", "snippet": "", "timestamp": ""}]}
        mp.setattr("wiki_explorer.commands.search.search_articles", mock_search)
        result = runner.invoke(main, ["search", "test", "--sort", "last_edit"])
        assert result.exit_code == 0
        # last_edit должен преобразоваться в last_edit_desc
        assert mock_called['sort'] == "last_edit_desc"


def test_search_with_namespace():
    """Опция --namespace."""
    runner = CliRunner()
    with pytest.MonkeyPatch.context() as mp:
        mock_called = {}
        def mock_search(query, lang, limit, sort, namespace):
            mock_called['namespace'] = namespace
            return {"search": [{"title": "Test", "snippet": "", "timestamp": ""}]}
        mp.setattr("wiki_explorer.commands.search.search_articles", mock_search)
        result = runner.invoke(main, ["search", "test", "--namespace", "1"])
        assert result.exit_code == 0
        assert mock_called['namespace'] == 1


def test_search_no_results():
    """Поиск без результатов."""
    runner = CliRunner()
    with pytest.MonkeyPatch.context() as mp:
        def mock_search(*args, **kwargs):
            return {"search": []}
        mp.setattr("wiki_explorer.commands.search.search_articles", mock_search)
        result = runner.invoke(main, ["search", "nonexistent_query_xyz"])
        assert result.exit_code == 0
        assert "Ничего не найдено" in result.output


def test_search_api_error():
    """Ошибка API -> exit code 1."""
    runner = CliRunner()
    with pytest.MonkeyPatch.context() as mp:
        def mock_search(*args, **kwargs):
            raise ApiError("API error: bad request")
        mp.setattr("wiki_explorer.commands.search.search_articles", mock_search)
        result = runner.invoke(main, ["search", "test"])
        assert result.exit_code == 1
        assert "Ошибка API: API error: bad request" in result.output


def test_search_network_error():
    """Сетевая ошибка -> exit code 1."""
    runner = CliRunner()
    with pytest.MonkeyPatch.context() as mp:
        def mock_search(*args, **kwargs):
            raise NetworkError("Connection refused")
        mp.setattr("wiki_explorer.commands.search.search_articles", mock_search)
        result = runner.invoke(main, ["search", "test"])
        assert result.exit_code == 1
        assert "Сетевая ошибка: Connection refused" in result.output


def test_search_verbose_mode():
    """Опция --verbose добавляет отладочную информацию."""
    runner = CliRunner()
    with pytest.MonkeyPatch.context() as mp:
        def mock_search(query, lang, limit, sort, namespace):
            return {"search": [{"title": "Test", "snippet": "", "timestamp": ""}]}
        mp.setattr("wiki_explorer.commands.search.search_articles", mock_search)
        result = runner.invoke(main, ["--verbose", "search", "test"])
        assert result.exit_code == 0
        assert "Поиск: 'test' (lang=en" in result.output


def test_search_with_html_snippet_cleaning():
    """Проверка очистки HTML-тегов в сниппете."""
    runner = CliRunner()
    with pytest.MonkeyPatch.context() as mp:
        def mock_search(*args, **kwargs):
            return {
                "search": [
                    {
                        "title": "Test",
                        "snippet": "This is a <span class='searchmatch'>test</span> snippet.",
                        "timestamp": ""
                    }
                ]
            }
        mp.setattr("wiki_explorer.commands.search.search_articles", mock_search)
        result = runner.invoke(main, ["search", "test"])
        assert result.exit_code == 0
        # HTML-теги должны быть удалены
        assert "<span" not in result.output
        assert "test" in result.output


def test_search_fewer_results_than_limit():
    """Когда найдено меньше результатов, чем лимит, выводится сообщение."""
    runner = CliRunner()
    with pytest.MonkeyPatch.context() as mp:
        def mock_search(*args, **kwargs):
            return {"search": [{"title": "Only one", "snippet": "", "timestamp": ""}]}
        mp.setattr("wiki_explorer.commands.search.search_articles", mock_search)
        result = runner.invoke(main, ["search", "test", "--limit", "10"])
        assert result.exit_code == 0
        assert "Найдено 1 результатов" in result.output