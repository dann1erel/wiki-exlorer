"""Console rendering helpers based on rich."""

from __future__ import annotations

from rich.console import Console
from pathlib import Path

from rich.panel import Panel
from rich.table import Table

from wiki_explorer.services.article_service import (
    ArticleCategories,
    ArticleInfo,
    ArticleLinks,
    SearchResults,
    RandomArticle,
)
from wiki_explorer.services.graph_service import GraphData
from wiki_explorer.services.image_service import ArticleImages
from wiki_explorer.services.pageviews_service import PageviewsResult


class ConsoleRenderer:
    """Render application data and errors to terminal."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    def render_search_results(self, search_results: SearchResults) -> None:
        """Print search results as a rich table."""
        if not search_results.results:
            self.console.print(
                Panel(
                    f'По запросу "{search_results.query}" ничего не найдено.',
                    title="Поиск",
                    style="yellow",
                )
            )
            return

        table = Table(title=f"Результаты поиска: {search_results.query}")
        table.add_column("№", justify="right", style="cyan", no_wrap=True)
        table.add_column("Название", style="white")
        table.add_column("Описание", style="white")
        table.add_column("Размер", justify="right", style="cyan")
        table.add_column("Последнее изменение", style="cyan")

        for index, result in enumerate(search_results.results, start=1):
            table.add_row(
                str(index),
                result.title,
                result.snippet or "нет описания",
                str(result.size) if result.size is not None else "нет данных",
                result.timestamp or "нет данных",
            )

        self.console.print(table)


    def render_random_article(self, article: RandomArticle) -> None:
        """Print random article as a rich card/table."""
        table = Table(title=f"Случайная статья: {article.title}")
        table.add_column("Поле", style="cyan", no_wrap=True)
        table.add_column("Значение", style="white")

        table.add_row("Название", article.title)
        table.add_row("Page ID", str(article.page_id))
        table.add_row(
            "Размер",
            f"{article.size_bytes} байт"
            if article.size_bytes is not None
            else "нет данных",
        )
        table.add_row("Примерное количество слов", str(article.words_count))
        table.add_row("URL", article.url)
        table.add_row("Изображение", "есть" if article.has_image else "нет")
        table.add_row("Первое изображение", article.first_image or "нет данных")
        table.add_row("Попыток использовано", str(article.attempts_used))

        if article.category:
            table.add_row("Категория", article.category)

        self.console.print(table)

    def render_article_info(
        self,
        article: ArticleInfo,
        show_categories: bool,
        show_image: bool,
    ) -> None:
        """Print article information as rich tables."""
        table = Table(title=f"Информация о статье: {article.title}")
        table.add_column("Поле", style="cyan", no_wrap=True)
        table.add_column("Значение", style="white")

        table.add_row("Название", article.title)
        table.add_row("ID страницы", str(article.page_id))
        table.add_row(
            "Размер",
            f"{article.size_bytes} байт"
            if article.size_bytes is not None
            else "не указан",
        )
        table.add_row(
            "Последняя правка",
            article.last_edit_timestamp or "нет данных",
        )
        table.add_row("Последний редактор", article.last_editor or "нет данных")
        table.add_row("Ссылка", article.url)

        self.console.print(table)

        if show_categories:
            self._render_list_block(
                title="Категории",
                items=article.categories,
                empty_message="У статьи нет категорий.",
            )

        if show_image:
            self._render_list_block(
                title="Изображения",
                items=article.images,
                empty_message="У статьи нет изображений.",
            )


    def render_categories(self, article_categories: ArticleCategories) -> None:
        """Print article categories as a rich table."""
        if not article_categories.categories:
            self.console.print(
                Panel(
                    f'Для статьи "{article_categories.title}" категории не найдены.',
                    title="Категории",
                    style="yellow",
                )
            )
            return

        table = Table(title=f"Категории статьи: {article_categories.title}")
        table.add_column("№", justify="right", style="cyan", no_wrap=True)
        table.add_column("Категория", style="white")

        for index, category in enumerate(article_categories.categories, start=1):
            table.add_row(str(index), category)

        self.console.print(table)

    def render_category_tree(self, article_categories: ArticleCategories) -> None:
        """Print simple category tree using rich tree."""
        from rich.tree import Tree

        if not article_categories.categories:
            self.console.print(
                Panel(
                    f'Для статьи "{article_categories.title}" категории не найдены.',
                    title="Категории",
                    style="yellow",
                )
            )
            return

        root = Tree(f"[bold]{article_categories.title}[/bold]")

        for category in article_categories.categories:
            category_node = root.add(f"[cyan]{category}[/cyan]")
            subcategories = article_categories.tree.get(category, [])

            if not subcategories:
                category_node.add("[yellow]Подкатегории не найдены[/yellow]")
                continue

            for subcategory in subcategories:
                category_node.add(str(subcategory))

        self.console.print(root)

    def render_links(self, article_links: ArticleLinks) -> None:
        """Print article links as a rich table."""
        if not article_links.links:
            self.console.print(
                Panel(
                    f'Для статьи "{article_links.title}" ссылки не найдены.',
                    title="Ссылки",
                    style="yellow",
                )
            )
            return

        table = Table(title=f"Внутренние ссылки статьи: {article_links.title}")
        table.add_column("№", justify="right", style="cyan", no_wrap=True)
        table.add_column("Название страницы", style="white")

        for index, link in enumerate(article_links.links, start=1):
            table.add_row(str(index), link)

        self.console.print(table)

    def render_graph_edges(self, graph_data: GraphData) -> None:
        """Print graph edges in text table format."""
        if not graph_data.edges:
            self.console.print(
                Panel(
                    f'Для статьи "{graph_data.source_title}" не найдено '
                    "внутренних ссылок для построения графа.",
                    title="Граф",
                    style="yellow",
                )
            )
            return

        table = Table(
            title=(
                f"Граф ссылок статьи: {graph_data.source_title} "
                f"(depth={graph_data.depth})"
            )
        )
        table.add_column("№", justify="right", style="cyan", no_wrap=True)
        table.add_column("Уровень", justify="center")
        table.add_column("Ребро", style="white")

        for index, edge in enumerate(graph_data.edges, start=1):
            source, target = edge
            edge_level = graph_data.get_edge_level(edge)
            row_style = "orange3" if edge_level == 2 else "white"
            table.add_row(
                str(index),
                str(edge_level),
                f"{source} -> {target}",
                style=row_style,
            )

        self.console.print(table)

        if graph_data.is_truncated:
            self.console.print(
                Panel(
                    "Граф был ограничен, чтобы не стать слишком большим. "
                    "Уменьшите --limit или используйте --depth 1.",
                    title="Предупреждение",
                    style="yellow",
                )
            )

    def render_graph_saved(self, output_path: Path, truncated: bool = False) -> None:
        """Print successful graph save message."""
        message = f"Граф успешно сохранён в файл {output_path}"
        if truncated:
            message += (
                "\nГраф был ограничен, чтобы не стать слишком большим. "
                "Уменьшите --limit или используйте --depth 1."
            )

        self.console.print(
            Panel(
                message,
                title="Граф",
                style="green",
            )
        )



    def render_images(self, article_images: ArticleImages) -> None:
        """Print article images and optional download results."""
        if not article_images.images:
            self.console.print(
                Panel(
                    f'Для статьи "{article_images.title}" изображения не найдены.',
                    title="Изображения",
                    style="yellow",
                )
            )
            return

        table = Table(title=f"Изображения статьи: {article_images.title}")
        table.add_column("№", justify="right", style="cyan", no_wrap=True)
        table.add_column("Файл", style="white")
        table.add_column("MIME-тип", style="cyan")
        table.add_column("Размер", justify="right", style="cyan")
        table.add_column("URL", style="white")

        for index, image in enumerate(article_images.images, start=1):
            table.add_row(
                str(index),
                image.title,
                image.mime or "нет данных",
                self._format_size(image.size_bytes),
                image.url or "нет данных",
            )

        self.console.print(table)

        if article_images.download_results:
            self._render_image_download_results(article_images)

    def _render_image_download_results(self, article_images: ArticleImages) -> None:
        """Print image download results."""
        table = Table(title="Результаты скачивания изображений")
        table.add_column("№", justify="right", style="cyan", no_wrap=True)
        table.add_column("Файл", style="white")
        table.add_column("Статус", style="cyan")
        table.add_column("Путь / ошибка", style="white")

        for index, result in enumerate(article_images.download_results, start=1):
            status = "скачано" if result.success else "ошибка"
            details = str(result.path) if result.path else (result.error or "нет данных")
            style = "green" if result.success else "red"
            table.add_row(
                str(index),
                result.image_title,
                status,
                details,
                style=style,
            )

        self.console.print(table)

    def render_pageviews(self, result: PageviewsResult) -> None:
        """Print pageviews table and summary."""
        labels = self._get_pageviews_labels()

        if not result.items or result.summary is None:
            self.console.print(
                Panel(
                    labels["not_found"].format(title=result.title),
                    title="Pageviews",
                    style="yellow",
                )
            )
            return

        table = Table(
            title=(
                f"{labels['table_title']}: {result.title} "
                f"({result.start_date.isoformat()} — {result.end_date.isoformat()})"
            )
        )
        table.add_column(labels["date"], style="cyan", no_wrap=True)
        table.add_column(labels["views"], justify="right", style="white")

        for item in result.items:
            table.add_row(item.date.isoformat(), str(item.views))

        self.console.print(table)

        summary = result.summary
        summary_table = Table(title=labels["summary_title"])
        summary_table.add_column(labels["metric"], style="cyan")
        summary_table.add_column(labels["value"], style="white")
        summary_table.add_row(labels["total"], str(summary.total_views))
        summary_table.add_row(
            labels["average"],
            f"{summary.average_views:.2f}",
        )
        summary_table.add_row(
            labels["maximum"],
            f"{summary.max_views_day.date.isoformat()} — "
            f"{summary.max_views_day.views}",
        )
        summary_table.add_row(
            labels["minimum"],
            f"{summary.min_views_day.date.isoformat()} — "
            f"{summary.min_views_day.views}",
        )

        self.console.print(summary_table)

    def render_ascii_chart(self, chart_text: str, lang: str = "ru") -> None:
        """Print ASCII chart text."""
        title = "ASCII chart" if self._is_english(lang) else "ASCII-график"
        self.console.print(Panel(chart_text, title=title, style="cyan"))

    def render_chart_saved(self, output_path: Path, lang: str = "ru") -> None:
        """Print successful chart save message."""
        message = (
            f"Chart successfully saved to {output_path}"
            if self._is_english(lang)
            else f"График успешно сохранён в файл {output_path}"
        )
        self.console.print(
            Panel(
                message,
                title="Pageviews",
                style="green",
            )
        )

    def render_verbose_info(
        self,
        verbose_info: dict[str, str],
        lang: str = "ru",
    ) -> None:
        """Print technical verbose information."""
        if not verbose_info:
            return

        labels = self._get_verbose_labels(lang)
        table = Table(title="Verbose")
        table.add_column(labels["parameter"], style="cyan")
        table.add_column(labels["value"], style="white")

        for key, value in verbose_info.items():
            table.add_row(key, value)

        self.console.print(table)


    @staticmethod
    def _is_english(lang: str) -> bool:
        """Return True when user selected English Wikipedia/output."""
        return lang.lower().startswith("en")

    @staticmethod
    def _get_pageviews_labels() -> dict[str, str]:
        """Return Russian labels for pageviews output."""
        return {
            "not_found": 'Для статьи "{title}" статистика просмотров не найдена.',
            "table_title": "Просмотры статьи",
            "date": "Дата",
            "views": "Просмотры",
            "summary_title": "Сводка",
            "metric": "Показатель",
            "value": "Значение",
            "total": "Всего просмотров",
            "average": "Среднее в день",
            "maximum": "Максимум",
            "minimum": "Минимум",
        }

    def _get_verbose_labels(self, lang: str) -> dict[str, str]:
        """Return labels for verbose output."""
        if self._is_english(lang):
            return {"parameter": "Parameter", "value": "Value"}

        return {"parameter": "Параметр", "value": "Значение"}

    def render_error(self, message: str) -> None:
        """Print user-friendly error message."""
        self.console.print(Panel(message, title="Ошибка", style="bold red"))

    @staticmethod
    def _format_size(size_bytes: int | None) -> str:
        """Format byte size for console output."""
        if size_bytes is None:
            return "нет данных"

        units = ["байт", "КБ", "МБ", "ГБ"]
        size = float(size_bytes)
        unit_index = 0
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1

        if unit_index == 0:
            return f"{int(size)} {units[unit_index]}"
        return f"{size:.2f} {units[unit_index]}"

    def _render_list_block(
        self,
        title: str,
        items: list[str],
        empty_message: str,
    ) -> None:
        if not items:
            self.console.print(Panel(empty_message, title=title, style="yellow"))
            return

        table = Table(title=title)
        table.add_column("№", justify="right", style="cyan")
        table.add_column("Значение", style="white")

        for index, item in enumerate(items, start=1):
            table.add_row(str(index), item)

        self.console.print(table)
