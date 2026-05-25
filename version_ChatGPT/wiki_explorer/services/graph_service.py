"""Business logic for graph-related commands."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx

from wiki_explorer.config import DEFAULT_GRAPH_MAX_NODES
from wiki_explorer.exceptions import (
    ArticleNotFoundError,
    FileSaveError,
    GraphBuildError,
    NoLinksFoundError,
)
from wiki_explorer.services.article_service import ArticleLinks, ArticleService


SUPPORTED_GRAPH_FORMATS = {"png", "pdf"}
SUPPORTED_GRAPH_DEPTHS = {1, 2}


@dataclass(frozen=True)
class GraphData:
    """Prepared graph data for rendering or saving."""

    source_title: str
    depth: int
    links: list[str] = field(default_factory=list)
    edges: list[tuple[str, str]] = field(default_factory=list)
    is_truncated: bool = False

    def get_edge_level(self, edge: tuple[str, str]) -> int:
        """Return graph edge level: 1 for root links, 2 for nested links."""
        source, _ = edge
        return 1 if source == self.source_title else 2

    @property
    def first_level_nodes(self) -> set[str]:
        """Return article nodes linked directly from the source article."""
        return set(self.links)

    @property
    def second_level_nodes(self) -> set[str]:
        """Return nodes that are reached from first-level articles."""
        return {
            target
            for source, target in self.edges
            if source != self.source_title
        } - self.first_level_nodes - {self.source_title}


class GraphService:
    """Service for building and saving article link graphs."""

    def __init__(self, article_service: ArticleService | None = None) -> None:
        self.article_service = article_service or ArticleService()

    def get_graph_data(
        self,
        title: str,
        lang: str,
        limit: int,
        depth: int = 1,
    ) -> GraphData:
        """Get article links and convert them to graph edges."""
        if limit <= 0:
            raise ValueError("Параметр --limit должен быть положительным числом.")

        if depth not in SUPPORTED_GRAPH_DEPTHS:
            raise ValueError("Параметр --depth должен быть равен 1 или 2.")

        article_links: ArticleLinks = self.article_service.get_links(
            title=title,
            lang=lang,
            limit=limit,
        )

        if not article_links.links:
            raise NoLinksFoundError(
                f'Для статьи "{article_links.title}" не найдено внутренних '
                "ссылок для построения графа."
            )

        edges = [(article_links.title, link) for link in article_links.links]
        nodes = {article_links.title, *article_links.links}
        is_truncated = False

        if depth == 2:
            second_level_edges, second_level_truncated = self._get_second_level_edges(
                first_level_links=article_links.links,
                lang=lang,
                limit=limit,
                nodes=nodes,
            )
            edges.extend(second_level_edges)
            is_truncated = second_level_truncated

        return GraphData(
            source_title=article_links.title,
            depth=depth,
            links=article_links.links,
            edges=edges,
            is_truncated=is_truncated,
        )

    def _get_second_level_edges(
        self,
        first_level_links: list[str],
        lang: str,
        limit: int,
        nodes: set[str],
    ) -> tuple[list[tuple[str, str]], bool]:
        """Build edges from first-level articles to their links."""
        edges: list[tuple[str, str]] = []
        is_truncated = False

        for first_level_title in first_level_links:
            if len(nodes) >= DEFAULT_GRAPH_MAX_NODES:
                is_truncated = True
                break

            try:
                nested_links = self.article_service.get_links(
                    title=first_level_title,
                    lang=lang,
                    limit=limit,
                )
            except ArticleNotFoundError:
                # A link may point to a page that was renamed or is unavailable.
                # This should not break the whole graph.
                continue

            for target_title in nested_links.links:
                if target_title not in nodes and len(nodes) >= DEFAULT_GRAPH_MAX_NODES:
                    is_truncated = True
                    break

                nodes.add(nested_links.title)
                nodes.add(target_title)
                edges.append((nested_links.title, target_title))

            if is_truncated:
                break

        return edges, is_truncated

    def build_graph(self, graph_data: GraphData) -> nx.DiGraph:
        """Build directed NetworkX graph from prepared graph data."""
        if not graph_data.edges:
            raise GraphBuildError("Невозможно построить граф без рёбер.")

        graph = nx.DiGraph()
        graph.add_node(graph_data.source_title)
        graph.add_edges_from(graph_data.edges)
        return graph

    def save_graph(
        self,
        graph_data: GraphData,
        output_path: str | Path,
        file_format: str,
    ) -> Path:
        """Save directed graph to PNG or PDF file."""
        normalized_format = file_format.lower()
        if normalized_format not in SUPPORTED_GRAPH_FORMATS:
            raise ValueError("Формат графа должен быть png или pdf.")

        path = Path(output_path)
        if path.suffix.lower() != f".{normalized_format}":
            path = path.with_suffix(f".{normalized_format}")

        try:
            graph = self.build_graph(graph_data)
            self._draw_graph(graph, graph_data, path, normalized_format)
        except (OSError, RuntimeError, ValueError) as exc:
            raise FileSaveError(
                "Не удалось сохранить граф в файл. "
                "Проверьте путь и права доступа."
            ) from exc

        return path

    def _draw_graph(
        self,
        graph: nx.DiGraph,
        graph_data: GraphData,
        output_path: Path,
        file_format: str,
    ) -> None:
        """Draw and save graph with matplotlib."""
        node_count = max(graph.number_of_nodes(), 1)
        figure_width = max(8, min(22, node_count * 0.45))
        figure_height = max(6, min(18, node_count * 0.35))

        plt.figure(figsize=(figure_width, figure_height))
        position = nx.spring_layout(graph, seed=42, k=1.1)

        source_nodes = [graph_data.source_title]
        first_level_nodes = [
            node
            for node in graph.nodes
            if node in graph_data.first_level_nodes
        ]
        second_level_nodes = [
            node
            for node in graph.nodes
            if node in graph_data.second_level_nodes
        ]
        other_nodes = [
            node
            for node in graph.nodes
            if node not in set(source_nodes + first_level_nodes + second_level_nodes)
        ]

        self._draw_nodes_group(
            graph, position, source_nodes, node_size=1300, color="#f4d35e"
        )
        self._draw_nodes_group(
            graph, position, first_level_nodes, node_size=700, color="#90caf9"
        )
        self._draw_nodes_group(
            graph, position, second_level_nodes, node_size=550, color="#ffb74d"
        )
        self._draw_nodes_group(
            graph, position, other_nodes, node_size=500, color="#cfd8dc"
        )

        first_level_edges = [
            edge for edge in graph.edges if graph_data.get_edge_level(edge) == 1
        ]
        second_level_edges = [
            edge for edge in graph.edges if graph_data.get_edge_level(edge) == 2
        ]

        self._draw_edges_group(
            graph, position, first_level_edges, edge_color="#6c757d"
        )
        self._draw_edges_group(
            graph, position, second_level_edges, edge_color="#e76f51"
        )

        nx.draw_networkx_labels(graph, position, font_size=7)

        plt.title(f"Ссылки статьи: {graph_data.source_title}")
        plt.axis("off")
        plt.tight_layout()
        plt.savefig(output_path, format=file_format, bbox_inches="tight")
        plt.close()

    @staticmethod
    def _draw_nodes_group(
        graph: nx.DiGraph,
        position: dict[str, tuple[float, float]],
        nodes: list[str],
        node_size: int,
        color: str,
    ) -> None:
        """Draw one visual group of nodes if it is not empty."""
        if not nodes:
            return

        nx.draw_networkx_nodes(
            graph,
            position,
            nodelist=nodes,
            node_size=node_size,
            node_color=color,
        )

    @staticmethod
    def _draw_edges_group(
        graph: nx.DiGraph,
        position: dict[str, tuple[float, float]],
        edges: list[tuple[str, str]],
        edge_color: str,
    ) -> None:
        """Draw one visual group of edges if it is not empty."""
        if not edges:
            return

        nx.draw_networkx_edges(
            graph,
            position,
            edgelist=edges,
            arrows=True,
            arrowstyle="->",
            arrowsize=12,
            edge_color=edge_color,
            connectionstyle="arc3,rad=0.08",
        )
