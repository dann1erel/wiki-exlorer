"""Тесты для команды pageviews CLI."""

from click.testing import CliRunner
import pytest
from unittest.mock import patch, Mock

from wiki_explorer.cli import main


@pytest.fixture
def mock_fetch_pageviews():
    with patch("wiki_explorer.commands.pageviews.fetch_pageviews") as mock:
        yield mock


def normalize_output(output: str) -> str:
    """Убирает лишние пробелы и переносы для удобного поиска."""
    return " ".join(output.split())


def test_pageviews_success(mock_fetch_pageviews):
    """Базовая команда без опций."""
    mock_fetch_pageviews.return_value = [
        {"date": "2026-05-19", "views": 520},
        {"date": "2026-05-20", "views": 443},
        {"date": "2026-05-21", "views": 436},
    ]
    runner = CliRunner()
    result = runner.invoke(main, ["pageviews", "Python"])
    assert result.exit_code == 0
    output = normalize_output(result.output)
    assert "Статистика просмотров статьи 'Python'" in output
    assert "2026-05-19 520" in output
    assert "2026-05-20 443" in output
    assert "2026-05-21 436" in output
    assert "Сумма: 1399" in output
    assert "Среднее: 466.3" in output


def test_pageviews_with_trailing_zeros_trimmed(mock_fetch_pageviews):
    """Хвостовые нули удаляются."""
    mock_fetch_pageviews.return_value = [
        {"date": "2026-05-19", "views": 520},
        {"date": "2026-05-20", "views": 443},
        {"date": "2026-05-21", "views": 0},
        {"date": "2026-05-22", "views": 0},
        {"date": "2026-05-23", "views": 0},
    ]
    runner = CliRunner()
    result = runner.invoke(main, ["pageviews", "Python"])
    assert result.exit_code == 0
    assert "удалено 3 последних дней" in result.output
    assert "2026-05-21" not in result.output
    assert "2026-05-22" not in result.output


def test_pageviews_all_zeros(mock_fetch_pageviews):
    """Все дни нулевые -> сообщение об отсутствии данных."""
    mock_fetch_pageviews.return_value = [
        {"date": "2026-05-19", "views": 0},
        {"date": "2026-05-20", "views": 0},
        {"date": "2026-05-21", "views": 0},
    ]
    runner = CliRunner()
    result = runner.invoke(main, ["pageviews", "Python"])
    assert result.exit_code == 0
    assert "Нет данных о просмотрах после удаления" in result.output


def test_pageviews_empty_data(mock_fetch_pageviews):
    """API вернул пустой список."""
    mock_fetch_pageviews.return_value = []
    runner = CliRunner()
    result = runner.invoke(main, ["pageviews", "Python"])
    assert result.exit_code == 0
    assert "Нет данных о просмотрах" in result.output


def test_pageviews_with_ascii_chart(mock_fetch_pageviews):
    """Опция --chart ascii."""
    mock_fetch_pageviews.return_value = [
        {"date": "2026-05-19", "views": 520},
        {"date": "2026-05-20", "views": 443},
    ]
    runner = CliRunner()
    result = runner.invoke(main, ["pageviews", "Python", "--chart", "ascii"])
    assert result.exit_code == 0
    assert "ASCII-график просмотров" in result.output
    assert "█" in result.output


def test_pageviews_with_png_chart(mock_fetch_pageviews):
    """Опция --chart png (мокаем функцию сохранения)."""
    mock_fetch_pageviews.return_value = [
        {"date": "2026-05-19", "views": 520},
        {"date": "2026-05-20", "views": 443},
    ]
    # Мокаем _save_png_chart, чтобы не трогать matplotlib
    with patch("wiki_explorer.commands.pageviews._save_png_chart") as mock_save:
        runner = CliRunner()
        result = runner.invoke(main, ["pageviews", "Python", "--chart", "png", "--output", "test.png"])
        assert result.exit_code == 0
        mock_save.assert_called_once()
        # Проверяем, что функция была вызвана с правильными аргументами
        args, kwargs = mock_save.call_args
        assert args[1] == "Python"  # title
        assert args[2] == "test.png"  # output path


def test_pageviews_days_exceeds_max():
    """--days > 90 -> ошибка."""
    runner = CliRunner()
    result = runner.invoke(main, ["pageviews", "Python", "--days", "100"])
    assert result.exit_code == 1
    assert "максимальное количество дней — 90" in result.output


def test_pageviews_days_negative():
    """--days < 1 -> ошибка."""
    runner = CliRunner()
    result = runner.invoke(main, ["pageviews", "Python", "--days", "0"])
    assert result.exit_code == 1
    assert "количество дней должно быть не меньше 1" in result.output


def test_pageviews_network_error(mock_fetch_pageviews):
    """Сетевая ошибка -> exit code 1."""
    mock_fetch_pageviews.side_effect = ConnectionError("Network problem")
    runner = CliRunner()
    result = runner.invoke(main, ["pageviews", "Python"])
    assert result.exit_code == 1
    assert "Сетевая ошибка: Network problem" in result.output


def test_pageviews_unknown_error(mock_fetch_pageviews):
    """Неизвестная ошибка -> exit code 1."""
    mock_fetch_pageviews.side_effect = Exception("Something went wrong")
    runner = CliRunner()
    result = runner.invoke(main, ["pageviews", "Python"])
    assert result.exit_code == 1
    assert "Неизвестная ошибка: Something went wrong" in result.output