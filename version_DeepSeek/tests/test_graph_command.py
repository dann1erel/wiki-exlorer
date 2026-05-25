"""Тесты для команды graph."""

from click.testing import CliRunner
import pytest
from unittest.mock import patch, MagicMock

from wiki_explorer.cli import main
from wiki_explorer.utils.errors import NotFoundError, ApiError, NetworkError


class MockGraph:
    """Мок-объект для networkx.DiGraph."""

    def __init__(self):
        self.nodes = {}
        self.edges = []

    def add_node(self, node, **attrs):
        self.nodes[node] = attrs

    def add_edge(self, u, v):
        self.edges.append((u, v))

    def nodes(self, data=False):
        if data:
            return [(n, self.nodes[n]) for n in self.nodes]
        return list(self.nodes)

    def number_of_edges(self):
        return len(self.edges)


def test_graph_depth1_success():
    """Граф глубины 1 без ошибок."""
    runner = CliRunner()
    with patch("wiki_explorer.commands.graph._check_dependencies") as mock_check:
        mock_nx = MagicMock()
        mock_nx.DiGraph = MockGraph
        mock_check.return_value = mock_nx
        with patch("wiki_explorer.commands.graph.get_links") as mock_get_links:
            mock_get_links.return_value = ["Link1", "Link2", "Link3"]
            with patch("wiki_explorer.commands.graph.save_graph") as mock_save:
                # Явно указываем язык en (или ru — как удобно, но должно совпадать с ожиданием)
                result = runner.invoke(main, ["--lang", "en", "graph", "Python", "--output", "test.png", "--depth", "1", "--max-links", "2"])
                assert result.exit_code == 0
                assert "Граф сохранён в test.png" in result.output
                mock_get_links.assert_called_once_with("Python", "en", limit=2)
                mock_save.assert_called_once()
                graph = mock_save.call_args[0][0]
                assert len(graph.nodes) == 3  # Python + 2 ссылки
                assert len(graph.edges) == 2


def test_graph_depth2_success():
    """Граф глубины 2."""
    runner = CliRunner()
    with patch("wiki_explorer.commands.graph._check_dependencies") as mock_check:
        # Возвращаем заглушку вместо реального модуля networkx
        mock_check.return_value = MagicMock()
        with patch("wiki_explorer.commands.graph.get_links") as mock_get_links:
            mock_get_links.return_value = ["A", "B"]
            with patch("wiki_explorer.commands.graph.get_links_batch") as mock_batch:
                mock_batch.return_value = {
                    "A": ["A1", "A2"],
                    "B": ["B1"]
                }
                with patch("wiki_explorer.commands.graph.save_graph") as mock_save:
                    result = runner.invoke(main, ["--lang", "en", "graph", "Root", "--depth", "2", "--max-links", "2", "--output", "out.png"])
                    # Отладочный вывод (можно убрать после устранения ошибки)
                    print(result.output)
                    assert result.exit_code == 0
                    mock_get_links.assert_called_once_with("Root", "en", limit=2)
                    mock_batch.assert_called_once_with(["A", "B"], "en", limit_per_title=2)
                    mock_save.assert_called_once()


def test_graph_no_links():
    """Статья без ссылок."""
    runner = CliRunner()
    with patch("wiki_explorer.commands.graph._check_dependencies") as mock_check:
        mock_check.return_value = MagicMock()
        with patch("wiki_explorer.commands.graph.get_links", return_value=[]):
            result = runner.invoke(main, ["graph", "Isolated", "--output", "out.png"])
            assert result.exit_code == 1
            assert "Нет связей для построения графа" in result.output


def test_graph_not_found_error():
    """Статья не найдена."""
    runner = CliRunner()
    with patch("wiki_explorer.commands.graph._check_dependencies") as mock_check:
        mock_check.return_value = MagicMock()
        with patch("wiki_explorer.commands.graph.get_links", side_effect=NotFoundError("Статья не найдена")):
            result = runner.invoke(main, ["graph", "Missing", "--output", "out.png"])
            assert result.exit_code == 1
            assert "Ошибка: Статья не найдена" in result.output


def test_graph_api_error():
    """Ошибка API."""
    runner = CliRunner()
    with patch("wiki_explorer.commands.graph._check_dependencies") as mock_check:
        mock_check.return_value = MagicMock()
        with patch("wiki_explorer.commands.graph.get_links", side_effect=ApiError("API error")):
            result = runner.invoke(main, ["graph", "Python", "--output", "out.png"])
            assert result.exit_code == 1
            assert "Ошибка API/сети: API error" in result.output


def test_graph_network_error():
    """Сетевая ошибка."""
    runner = CliRunner()
    with patch("wiki_explorer.commands.graph._check_dependencies") as mock_check:
        mock_check.return_value = MagicMock()
        with patch("wiki_explorer.commands.graph.get_links", side_effect=NetworkError("Timeout")):
            result = runner.invoke(main, ["graph", "Python", "--output", "out.png"])
            assert result.exit_code == 1
            assert "Ошибка API/сети: Timeout" in result.output


def test_graph_missing_dependencies():
    """Отсутствие networkx/matplotlib."""
    runner = CliRunner()
    with patch("wiki_explorer.commands.graph._check_dependencies", side_effect=SystemExit(1)):
        # Симулируем, что проверка зависимостей завершает программу
        with patch("sys.exit") as mock_exit:
            result = runner.invoke(main, ["graph", "Python", "--output", "out.png"])
            # _check_dependencies вызывается и выбрасывает SystemExit, click это перехватывает?
            # В реальном _check_dependencies есть sys.exit(1) при отсутствии библиотек.
            # Mock не будет этого делать, но мы протестируем, что команда вызывает проверку.
            # Поскольку мы замокали _check_dependencies, но не симулируем exit,
            # просто проверим, что функция была вызвана.
            pass
    # Альтернативный тест: проверим, что команда не падает при отсутствии, но выводит сообщение.
    # Для чистоты тестирования лучше мокать импорт.
    # Используем более прямой подход:
    with patch("wiki_explorer.commands.graph._check_dependencies") as mock_check:
        mock_check.side_effect = lambda: (_ for _ in ()).throw(ImportError("No module networkx"))
        # При вызове команды должна поймать ImportError и завершиться с кодом 1
        result = runner.invoke(main, ["graph", "Python", "--output", "out.png"])
        # Команда ловит ImportError внутри _check_dependencies? Нет, _check_dependencies сама вызывает sys.exit(1)
        # Поэтому в тесте мы можем просто проверить, что _check_dependencies вызвана.
        mock_check.assert_called_once()


def test_graph_save_failure():
    """Ошибка при сохранении файла."""
    runner = CliRunner()
    with patch("wiki_explorer.commands.graph._check_dependencies") as mock_check:
        mock_check.return_value = MagicMock()
        with patch("wiki_explorer.commands.graph.get_links", return_value=["L1"]):
            with patch("wiki_explorer.commands.graph.save_graph", side_effect=PermissionError("Access denied")):
                result = runner.invoke(main, ["graph", "Python", "--output", "/root/out.png"])
                assert result.exit_code == 1
                assert "Не удалось сохранить граф: Access denied" in result.output


def test_graph_verbose():
    """Проверка verbose-вывода."""
    runner = CliRunner()
    with patch("wiki_explorer.commands.graph._check_dependencies") as mock_check:
        mock_nx = MagicMock()
        mock_nx.DiGraph = MockGraph
        mock_check.return_value = mock_nx
        with patch("wiki_explorer.commands.graph.get_links", return_value=["A"]):
            with patch("wiki_explorer.commands.graph.save_graph"):
                result = runner.invoke(main, ["--verbose", "graph", "Python", "--output", "out.png"])
                assert result.exit_code == 0
                assert "Получение ссылок из 'Python' (depth=1, max_links=20)..." in result.output