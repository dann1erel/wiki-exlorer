"""Команда для построения графа ссылок статьи."""

import sys
from typing import List, Dict, Optional

import click
from rich.console import Console

from wiki_explorer.api.mediawiki import get_links, get_links_batch
from wiki_explorer.utils.errors import NotFoundError, ApiError, NetworkError

console = Console()


def _check_dependencies():
    """Проверяет наличие networkx и matplotlib, иначе завершает программу."""
    try:
        import networkx
        import matplotlib
        matplotlib.use('Agg')  # отключаем интерактивный режим
        return networkx
    except ImportError as e:
        console.print(f"[red]Ошибка: отсутствует необходимая библиотека. Установите networkx и matplotlib.\n{e}[/red]")
        sys.exit(1)


def build_graph(title: str, lang: str, depth: int, max_links: int) -> "networkx.DiGraph":
    """
    Строит ориентированный граф ссылок, присваивая узлам атрибут 'depth'.

    Параметры:
        title: корневая статья
        lang: язык
        depth: глубина (1 или 2)
        max_links: максимальное количество ссылок на уровне 1 (и для каждого потомка при depth=2)

    Возвращает:
        networkx.DiGraph с атрибутами узлов 'depth': 0 (корень), 1, 2

    Исключения:
        NotFoundError, ApiError, NetworkError
    """
    nx = _check_dependencies()
    graph = nx.DiGraph()
    # Корневой узел, глубина 0
    graph.add_node(title, depth=0)

    # Уровень 1: ссылки из корня
    root_links = get_links(title, lang, limit=max_links)
    if not root_links:
        raise ValueError("Нет связей для построения графа")

    root_links = root_links[:max_links]
    for link in root_links:
        graph.add_node(link, depth=1)
        graph.add_edge(title, link)

    # Если depth == 1, возвращаем граф
    if depth == 1:
        return graph

    # depth == 2: для каждой ссылки из корня получаем её ссылки (до max_links)
    batch_size = 50
    for i in range(0, len(root_links), batch_size):
        batch = root_links[i:i + batch_size]
        try:
            batch_result = get_links_batch(batch, lang, limit_per_title=max_links)
            for parent, children in batch_result.items():
                # parent точно есть в графе (depth=1)
                for child in children[:max_links]:
                    # Если узел уже существует, оставляем минимальную глубину (0 или 1)
                    if child not in graph:
                        graph.add_node(child, depth=2)
                    else:
                        # Если узел уже был добавлен (например, на глубине 1), не понижаем глубину
                        pass
                    graph.add_edge(parent, child)
        except (ApiError, NetworkError) as e:
            console.print(f"[yellow]Предупреждение: не удалось получить ссылки второго уровня для некоторых статей: {e}[/yellow]")
            continue

    if graph.number_of_edges() == 0:
        raise ValueError("Нет связей для построения графа (после обрезки)")

    return graph


def save_graph(graph: "networkx.DiGraph", output_path: str) -> None:
    """
    Сохраняет граф в PNG-файл, раскрашивая узлы в зависимости от глубины:
      - глубина 0 (корень): красный
      - глубина 1: светло-голубой
      - глубина 2: светло-зелёный
    """
    import matplotlib.pyplot as plt
    import networkx as nx

    # Определяем цвета в зависимости от атрибута depth
    node_colors = []
    for node in graph.nodes():
        depth = graph.nodes[node].get('depth', 1)  # по умолчанию глубина 1
        if depth == 0:
            node_colors.append('red')
        elif depth == 1:
            node_colors.append('lightblue')
        else:  # depth == 2
            node_colors.append('lightgreen')

    plt.figure(figsize=(12, 10))
    pos = nx.spring_layout(graph, k=1.5, iterations=50, seed=42)
    nx.draw_networkx_nodes(graph, pos, node_color=node_colors, node_size=800)
    nx.draw_networkx_edges(graph, pos, edge_color='gray', arrows=True, arrowsize=15)
    nx.draw_networkx_labels(graph, pos, font_size=8, font_family='sans-serif')
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(output_path, format='png', dpi=150, bbox_inches='tight')
    plt.close()


@click.command(name="graph")
@click.argument("title")
@click.option("--output", required=True, type=click.Path(), help="Путь для сохранения PNG (обязательно)")
@click.option("--depth", type=click.Choice(["1", "2"]), default="1", help="Глубина графа (1 или 2)", show_default=True)
@click.option("--max-links", type=int, default=20, help="Максимум ссылок на уровень", show_default=True)
@click.pass_context
def graph(ctx, title: str, output: str, depth: str, max_links: int):
    """
    Строит граф ссылок из статьи и сохраняет в PNG.

    Примеры:
      wiki-explorer graph "Python" --output graph.png
      wiki-explorer graph "Artificial intelligence" --depth 2 --max-links 10 --output deep_graph.png
    """
    # Получаем язык из контекста
    lang = ctx.obj.get("lang", "ru") if ctx.obj else "ru"
    verbose = ctx.obj.get("verbose", False) if ctx.obj else False

    depth_int = int(depth)
    if depth_int not in (1, 2):
        console.print("[red]Ошибка: depth должен быть 1 или 2[/red]")
        sys.exit(1)

    # Проверяем библиотеки
    try:
        _check_dependencies()
    except SystemExit:
        return

    # Строим граф
    try:
        if verbose:
            console.print(f"[dim]Получение ссылок из '{title}' (depth={depth_int}, max_links={max_links})...[/dim]")
        graph_obj = build_graph(title, lang, depth_int, max_links)
    except NotFoundError as e:
        console.print(f"[red]Ошибка: {e}[/red]")
        sys.exit(1)
    except (ApiError, NetworkError) as e:
        console.print(f"[red]Ошибка API/сети: {e}[/red]")
        sys.exit(1)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)
    except Exception as e:
        if verbose:
            console.print_exception()
        else:
            console.print(f"[red]Неожиданная ошибка: {e}[/red]")
        sys.exit(1)

    # Сохраняем граф
    try:
        save_graph(graph_obj, output)
        console.print(f"[green]Граф сохранён в {output}[/green]")
    except Exception as e:
        console.print(f"[red]Не удалось сохранить граф: {e}[/red]")
        sys.exit(1)