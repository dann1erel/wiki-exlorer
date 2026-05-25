"""Тесты для команды images."""

from click.testing import CliRunner
import pytest
import os
from unittest.mock import patch, MagicMock, call

from wiki_explorer.cli import main
from wiki_explorer.utils.errors import NotFoundError, NetworkError, ApiError


def test_images_success_no_download():
    """Вывод таблицы без скачивания."""
    runner = CliRunner()
    with pytest.MonkeyPatch.context() as mp:
        mock_images = [
            {"filename": "File:Example1.jpg", "url": "https://example.com/1.jpg", "size": 12345},
            {"filename": "File:Example2.png", "url": "https://example.com/2.png", "size": 67890},
        ]
        mp.setattr("wiki_explorer.commands.images.get_image_list", lambda *args, **kwargs: mock_images)
        result = runner.invoke(main, ["--lang", "en", "images", "Python"])
        assert result.exit_code == 0
        assert "Изображения в статье: Python" in result.output
        assert "Example1.jpg" in result.output
        assert "Example2.png" in result.output
        # Размеры выводятся с разделителями тысяч (12,345 и 67,890)
        assert "12,345" in result.output
        assert "67,890" in result.output


def test_images_no_images():
    """Статья без изображений."""
    runner = CliRunner()
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("wiki_explorer.commands.images.get_image_list", lambda *args, **kwargs: [])
        result = runner.invoke(main, ["images", "NoImagesArticle"])
        assert result.exit_code == 0
        assert "Изображения отсутствуют" in result.output


def test_images_not_found_error():
    """Статья не найдена."""
    runner = CliRunner()
    with pytest.MonkeyPatch.context() as mp:
        def mock_get_image_list(*args, **kwargs):
            raise NotFoundError("Статья не найдена")
        mp.setattr("wiki_explorer.commands.images.get_image_list", mock_get_image_list)
        result = runner.invoke(main, ["images", "Nonexistent"])
        assert result.exit_code == 1
        assert "Ошибка: Статья не найдена" in result.output


def test_images_network_error():
    """Сетевая ошибка."""
    runner = CliRunner()
    with pytest.MonkeyPatch.context() as mp:
        def mock_get_image_list(*args, **kwargs):
            raise NetworkError("Connection refused")
        mp.setattr("wiki_explorer.commands.images.get_image_list", mock_get_image_list)
        result = runner.invoke(main, ["images", "Python"])
        assert result.exit_code == 1
        assert "Сетевая ошибка: Connection refused" in result.output


def test_images_api_error():
    """Ошибка API."""
    runner = CliRunner()
    with pytest.MonkeyPatch.context() as mp:
        def mock_get_image_list(*args, **kwargs):
            raise ApiError("Invalid API response")
        mp.setattr("wiki_explorer.commands.images.get_image_list", mock_get_image_list)
        result = runner.invoke(main, ["images", "Python"])
        assert result.exit_code == 1
        assert "Ошибка API: Invalid API response" in result.output


def test_images_download_all():
    """Скачивание всех изображений (флаг --download)."""
    runner = CliRunner()
    mock_images = [
        {"filename": "File:pic1.jpg", "url": "http://example.com/pic1.jpg", "size": 1000},
        {"filename": "File:pic2.png", "url": "http://example.com/pic2.png", "size": 2000},
    ]
    with patch("wiki_explorer.commands.images.get_image_list", return_value=mock_images):
        with patch("wiki_explorer.commands.images.download_image") as mock_download:
            mock_download.return_value = True
            with patch("os.makedirs") as mock_makedirs:
                result = runner.invoke(main, ["images", "TestArticle", "--download", "--output", "./my_images"])
                assert result.exit_code == 0
                mock_makedirs.assert_called_once_with("./my_images", exist_ok=True)
                assert mock_download.call_count == 2
                first_call = mock_download.call_args_list[0]
                assert first_call[0][0] == "http://example.com/pic1.jpg"
                # Используем os.path.normpath для кроссплатформенного сравнения
                expected_path = os.path.normpath("./my_images/pic1.jpg")
                assert os.path.normpath(first_call[0][1]) == expected_path
                second_call = mock_download.call_args_list[1]
                expected_path2 = os.path.normpath("./my_images/pic2.png")
                assert os.path.normpath(second_call[0][1]) == expected_path2


def test_images_download_with_index():
    """Скачивание выбранных изображений по индексам."""
    runner = CliRunner()
    mock_images = [
        {"filename": "File:first.jpg", "url": "http://example.com/first.jpg", "size": 100},
        {"filename": "File:second.jpg", "url": "http://example.com/second.jpg", "size": 200},
        {"filename": "File:third.jpg", "url": "http://example.com/third.jpg", "size": 300},
    ]
    with patch("wiki_explorer.commands.images.get_image_list", return_value=mock_images):
        with patch("wiki_explorer.commands.images.download_image") as mock_download:
            mock_download.return_value = True
            with patch("os.makedirs"):
                result = runner.invoke(main, ["images", "Test", "--index", "1,3"])
                assert result.exit_code == 0
                # Должны скачать только первое и третье изображения
                assert mock_download.call_count == 2
                args_first = mock_download.call_args_list[0][0]
                args_second = mock_download.call_args_list[1][0]
                assert args_first[1].endswith("first.jpg")
                assert args_second[1].endswith("third.jpg")


def test_images_index_out_of_range():
    """Индекс вне диапазона."""
    runner = CliRunner()
    mock_images = [
        {"filename": "File:only.jpg", "url": "http://example.com/only.jpg", "size": 100},
    ]
    with patch("wiki_explorer.commands.images.get_image_list", return_value=mock_images):
        result = runner.invoke(main, ["images", "Test", "--index", "2,3"])
        assert result.exit_code == 1
        assert "индекс 2 вне допустимого диапазона (1-1)" in result.output


def test_images_invalid_index_format():
    """Неправильный формат --index."""
    runner = CliRunner()
    with patch("wiki_explorer.commands.images.get_image_list", return_value=[]):
        result = runner.invoke(main, ["images", "Test", "--index", "one,two"])
        assert result.exit_code == 1
        assert "--index должен содержать номера через запятую" in result.output


def test_images_download_skip_existing():
    """Существующий файл не скачивается повторно."""
    runner = CliRunner()
    mock_images = [
        {"filename": "File:existing.jpg", "url": "http://example.com/existing.jpg", "size": 100},
    ]
    with patch("wiki_explorer.commands.images.get_image_list", return_value=mock_images):
        with patch("wiki_explorer.commands.images.download_image") as mock_download:
            with patch("os.path.exists", return_value=True):  # файл уже существует
                with patch("os.makedirs"):
                    result = runner.invoke(main, ["images", "Test", "--download"])
                    assert result.exit_code == 0
                    assert "уже существует, пропускаем" in result.output
                    mock_download.assert_not_called()  # скачивание не вызывалось


def test_images_download_failure():
    """Ошибка при скачивании одного из изображений."""
    runner = CliRunner()
    mock_images = [
        {"filename": "File:good.jpg", "url": "http://example.com/good.jpg", "size": 100},
        {"filename": "File:bad.jpg", "url": "", "size": 200},  # нет URL
    ]
    with patch("wiki_explorer.commands.images.get_image_list", return_value=mock_images):
        with patch("wiki_explorer.commands.images.download_image", return_value=False) as mock_download:
            with patch("os.makedirs"):
                result = runner.invoke(main, ["images", "Test", "--download"])
                assert result.exit_code == 0  # команда не падает при ошибке скачивания
                assert mock_download.call_count == 2
                # Проверяем, что в выводе есть сообщение об ошибке (хотя бы предупреждение)
                # В реальном выводе есть "[yellow]Предупреждение: не удалось скачать ..."
                # Но в тесте мы замокали download_image и она возвращает False,
                # сообщение выводится внутри download_image, а не в команде.
                # Можем проверить, что команда не выбросила исключение.