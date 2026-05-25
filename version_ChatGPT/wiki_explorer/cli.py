"""Command-line interface for Wiki-Explorer."""

from __future__ import annotations

import logging

import click

from wiki_explorer.config import (
    DEFAULT_CATEGORIES_LIMIT,
    DEFAULT_DOWNLOAD_DIR,
    DEFAULT_GRAPH_DEPTH,
    DEFAULT_GRAPH_FORMAT,
    DEFAULT_GRAPH_LIMIT,
    DEFAULT_GRAPH_OUTPUT,
    DEFAULT_IMAGES_LIMIT,
    DEFAULT_LANGUAGE,
    DEFAULT_LINKS_LIMIT,
    DEFAULT_PAGEVIEWS_DAYS,
    DEFAULT_PAGEVIEWS_OUTPUT,
    DEFAULT_SEARCH_LIMIT,
    DEFAULT_SEARCH_SORT,
)
from wiki_explorer.exceptions import WikiExplorerError
from wiki_explorer.logging_config import setup_logging
from wiki_explorer.output.chart_renderer import ChartRenderer
from wiki_explorer.output.console_renderer import ConsoleRenderer
from wiki_explorer.services.article_service import ArticleService
from wiki_explorer.services.graph_service import GraphService
from wiki_explorer.services.image_service import ImageService
from wiki_explorer.services.pageviews_service import PageviewsService


logger = logging.getLogger(__name__)


@click.group()
@click.option(
    "--verbose",
    is_flag=True,
    help="Включить подробное логирование работы команды.",
)
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """Wiki-Explorer: CLI-утилита для работы с Wikipedia."""
    setup_logging(verbose)
    ctx.obj = {"verbose": verbose}


def _is_verbose(ctx: click.Context, local_verbose: bool) -> bool:
    verbose_enabled = local_verbose or bool((ctx.obj or {}).get("verbose"))
    if verbose_enabled:
        setup_logging(True)
    return verbose_enabled


@cli.command()
@click.argument("title")
@click.option(
    "--lang",
    default=DEFAULT_LANGUAGE,
    show_default=True,
    help="Язык Wikipedia, например ru или en.",
)
@click.option(
    "--show-categories",
    is_flag=True,
    help="Показать первые 10 категорий статьи.",
)
@click.option(
    "--show-image",
    is_flag=True,
    help="Показать изображения статьи.",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Включить подробное логирование работы команды.",
)
@click.pass_context
def info(
    ctx: click.Context,
    title: str,
    lang: str,
    show_categories: bool,
    show_image: bool,
    verbose: bool,
) -> None:
    """Показать базовую информацию о статье Wikipedia."""
    renderer = ConsoleRenderer()
    service = ArticleService()
    _is_verbose(ctx, verbose)

    logger.info("Command started: info")
    logger.info(
        "Command parameters: title=%s, lang=%s, show_categories=%s, show_image=%s",
        title,
        lang,
        show_categories,
        show_image,
    )

    try:
        article = service.get_info(
            title=title,
            lang=lang,
            include_categories=show_categories,
            include_images=show_image,
        )
        renderer.render_article_info(article, show_categories, show_image)
        logger.info("Command finished successfully")
    except (WikiExplorerError, ValueError) as exc:
        logger.error("Command failed: %s", exc)
        renderer.render_error(str(exc))
        raise click.Abort() from exc



@cli.command()
@click.argument("title")
@click.option(
    "--lang",
    default=DEFAULT_LANGUAGE,
    show_default=True,
    help="Язык Wikipedia, например ru или en.",
)
@click.option(
    "--limit",
    default=DEFAULT_LINKS_LIMIT,
    show_default=True,
    type=click.IntRange(min=1),
    help="Максимальное количество ссылок.",
)
@click.option(
    "--search",
    default=None,
    help="Фильтр по части названия ссылки.",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Включить подробное логирование работы команды.",
)
@click.pass_context
def links(
    ctx: click.Context,
    title: str,
    lang: str,
    limit: int,
    search: str | None,
    verbose: bool,
) -> None:
    """Показать внутренние ссылки из статьи Wikipedia."""
    renderer = ConsoleRenderer()
    service = ArticleService()
    _is_verbose(ctx, verbose)

    logger.info("Command started: links")
    logger.info(
        "Command parameters: title=%s, lang=%s, limit=%s, search=%s",
        title,
        lang,
        limit,
        search,
    )

    try:
        article_links = service.get_links(
            title=title,
            lang=lang,
            limit=limit,
            search=search,
        )
        renderer.render_links(article_links)
        logger.info("Links received: %s", len(article_links.links))
        logger.info("Command finished successfully")
    except (WikiExplorerError, ValueError) as exc:
        logger.error("Command failed: %s", exc)
        renderer.render_error(str(exc))
        raise click.Abort() from exc

@cli.command()
@click.argument("title")
@click.option(
    "--lang",
    default=DEFAULT_LANGUAGE,
    show_default=True,
    help="Язык Wikipedia, например ru или en.",
)
@click.option(
    "--limit",
    default=DEFAULT_GRAPH_LIMIT,
    show_default=True,
    type=click.IntRange(min=1),
    help="Максимальное количество ссылок для графа.",
)
@click.option(
    "--output",
    default=DEFAULT_GRAPH_OUTPUT,
    show_default=True,
    help="Путь для сохранения графа.",
)
@click.option(
    "--format",
    "file_format",
    default=DEFAULT_GRAPH_FORMAT,
    show_default=True,
    type=click.Choice(["png", "pdf"], case_sensitive=False),
    help="Формат файла графа.",
)
@click.option(
    "--depth",
    default=DEFAULT_GRAPH_DEPTH,
    show_default=True,
    type=click.IntRange(min=1, max=2),
    help="Глубина графа: 1 или 2 уровня ссылок.",
)
@click.option(
    "--text",
    "text_mode",
    is_flag=True,
    help="Вывести граф текстом без сохранения изображения.",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Включить подробное логирование работы команды.",
)
@click.pass_context
def graph(
    ctx: click.Context,
    title: str,
    lang: str,
    limit: int,
    output: str,
    file_format: str,
    depth: int,
    text_mode: bool,
    verbose: bool,
) -> None:
    """Построить граф внутренних ссылок статьи Wikipedia."""
    renderer = ConsoleRenderer()
    service = GraphService()
    _is_verbose(ctx, verbose)

    normalized_format = file_format.lower()
    logger.info("Command started: graph")
    logger.info(
        "Command parameters: title=%s, lang=%s, limit=%s, output=%s, "
        "format=%s, depth=%s, text=%s",
        title,
        lang,
        limit,
        output,
        normalized_format,
        depth,
        text_mode,
    )

    try:
        graph_data = service.get_graph_data(
            title=title,
            lang=lang,
            limit=limit,
            depth=depth,
        )
        logger.info(
            "Graph prepared: nodes=%s, edges=%s, truncated=%s",
            len({graph_data.source_title, *graph_data.links}
                | {target for _, target in graph_data.edges}),
            len(graph_data.edges),
            graph_data.is_truncated,
        )

        if text_mode:
            renderer.render_graph_edges(graph_data)
            logger.info("Command finished successfully")
            return

        saved_path = service.save_graph(
            graph_data=graph_data,
            output_path=output,
            file_format=normalized_format,
        )
        logger.info("Graph saved to: %s", saved_path)
        renderer.render_graph_saved(saved_path, graph_data.is_truncated)
        logger.info("Command finished successfully")
    except (WikiExplorerError, ValueError) as exc:
        logger.error("Command failed: %s", exc)
        renderer.render_error(str(exc))
        raise click.Abort() from exc

@cli.command()
@click.argument("title")
@click.option(
    "--lang",
    default=DEFAULT_LANGUAGE,
    show_default=True,
    help="Язык Wikipedia, например ru или en.",
)
@click.option(
    "--limit",
    default=DEFAULT_CATEGORIES_LIMIT,
    show_default=True,
    type=click.IntRange(min=1),
    help="Максимальное количество категорий.",
)
@click.option(
    "--tree",
    "tree_mode",
    is_flag=True,
    help="Показать простое дерево категорий.",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Включить подробное логирование работы команды.",
)
@click.pass_context
def categories(
    ctx: click.Context,
    title: str,
    lang: str,
    limit: int,
    tree_mode: bool,
    verbose: bool,
) -> None:
    """Показать категории статьи Wikipedia."""
    renderer = ConsoleRenderer()
    service = ArticleService()
    _is_verbose(ctx, verbose)

    logger.info("Command started: categories")
    logger.info(
        "Command parameters: title=%s, lang=%s, limit=%s, tree=%s",
        title,
        lang,
        limit,
        tree_mode,
    )

    try:
        article_categories = service.get_categories(
            title=title,
            lang=lang,
            limit=limit,
            tree=tree_mode,
        )
        logger.info(
            "Categories received: %s, tree roots=%s",
            len(article_categories.categories),
            len(article_categories.tree),
        )

        if tree_mode:
            renderer.render_category_tree(article_categories)
            logger.info("Command finished successfully")
            return

        renderer.render_categories(article_categories)
        logger.info("Command finished successfully")
    except (WikiExplorerError, ValueError) as exc:
        logger.error("Command failed: %s", exc)
        renderer.render_error(str(exc))
        raise click.Abort() from exc

@cli.command()
@click.argument("title")
@click.option(
    "--days",
    default=DEFAULT_PAGEVIEWS_DAYS,
    show_default=True,
    type=click.IntRange(min=1),
    help="Количество дней для анализа просмотров.",
)
@click.option(
    "--chart",
    default="none",
    show_default=True,
    type=click.Choice(["none", "ascii", "png"], case_sensitive=False),
    help="Тип графика: none, ascii или png.",
)
@click.option(
    "--output",
    default=DEFAULT_PAGEVIEWS_OUTPUT,
    show_default=True,
    help="Путь для сохранения PNG-графика.",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Включить подробное логирование работы команды.",
)
@click.pass_context
def pageviews(
    ctx: click.Context,
    title: str,
    days: int,
    chart: str,
    output: str,
    verbose: bool,
) -> None:
    """Показать статистику просмотров статьи Wikipedia."""
    renderer = ConsoleRenderer()
    chart_renderer = ChartRenderer()
    service = PageviewsService()
    _is_verbose(ctx, verbose)

    normalized_chart = chart.lower()
    logger.info("Command started: pageviews")
    logger.info(
        "Command parameters: title=%s, days=%s, chart=%s, output=%s",
        title,
        days,
        normalized_chart,
        output,
    )

    try:
        result = service.get_pageviews(title=title, days=days)
        renderer.render_pageviews(result)

        if normalized_chart == "ascii":
            renderer.render_ascii_chart(
                chart_renderer.render_ascii_chart(result.items),
            )
        elif normalized_chart == "png":
            saved_path = chart_renderer.save_pageviews_chart(
                items=result.items,
                output_path=output,
            )
            renderer.render_chart_saved(saved_path)

        logger.info("Command finished successfully")
    except (WikiExplorerError, ValueError) as exc:
        logger.error("Command failed: %s", exc)
        renderer.render_error(str(exc))
        raise click.Abort() from exc


@cli.command()
@click.argument("query")
@click.option(
    "--lang",
    default=DEFAULT_LANGUAGE,
    show_default=True,
    help="Язык Wikipedia, например ru или en.",
)
@click.option(
    "--limit",
    default=DEFAULT_SEARCH_LIMIT,
    show_default=True,
    type=click.IntRange(min=1),
    help="Максимальное количество результатов поиска.",
)
@click.option(
    "--sort",
    "sort_mode",
    default=DEFAULT_SEARCH_SORT,
    show_default=True,
    type=click.Choice(["relevance", "last_edit"], case_sensitive=False),
    help="Сортировка результатов: relevance или last_edit.",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Включить подробное логирование работы команды.",
)
@click.pass_context
def search(
    ctx: click.Context,
    query: str,
    lang: str,
    limit: int,
    sort_mode: str,
    verbose: bool,
) -> None:
    """Найти статьи Wikipedia по ключевым словам."""
    renderer = ConsoleRenderer()
    service = ArticleService()
    _is_verbose(ctx, verbose)

    normalized_sort = sort_mode.lower()
    logger.info("Command started: search")
    logger.info(
        "Command parameters: query=%s, lang=%s, limit=%s, sort=%s",
        query,
        lang,
        limit,
        normalized_sort,
    )

    try:
        search_results = service.search_articles(
            query=query,
            lang=lang,
            limit=limit,
            sort=normalized_sort,
        )
        renderer.render_search_results(search_results)
        logger.info("Command finished successfully")
    except (WikiExplorerError, ValueError) as exc:
        logger.error("Command failed: %s", exc)
        renderer.render_error(str(exc))
        raise click.Abort() from exc


@cli.command("random")
@click.option(
    "--lang",
    default=DEFAULT_LANGUAGE,
    show_default=True,
    help="Язык Wikipedia, например ru или en.",
)
@click.option(
    "--category",
    default=None,
    help="Категория Wikipedia для выбора случайной статьи.",
)
@click.option(
    "--min-words",
    default=None,
    type=click.IntRange(min=1),
    help="Минимальное примерное количество слов в статье.",
)
@click.option(
    "--with-image",
    is_flag=True,
    help="Искать только статьи с изображениями.",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Включить подробное логирование работы команды.",
)
@click.pass_context
def random_article(
    ctx: click.Context,
    lang: str,
    category: str | None,
    min_words: int | None,
    with_image: bool,
    verbose: bool,
) -> None:
    """Показать случайную статью Wikipedia."""
    renderer = ConsoleRenderer()
    service = ArticleService()
    _is_verbose(ctx, verbose)

    logger.info("Command started: random")
    logger.info(
        "Command parameters: lang=%s, category=%s, min_words=%s, with_image=%s",
        lang,
        category,
        min_words,
        with_image,
    )

    try:
        article = service.get_random_article(
            lang=lang,
            category=category,
            min_words=min_words,
            with_image=with_image,
        )
        renderer.render_random_article(article)
        logger.info("Command finished successfully")
    except (WikiExplorerError, ValueError) as exc:
        logger.error("Command failed: %s", exc)
        renderer.render_error(str(exc))
        raise click.Abort() from exc


@cli.command()
@click.argument("title")
@click.option(
    "--lang",
    default=DEFAULT_LANGUAGE,
    show_default=True,
    help="Язык Wikipedia, например ru или en.",
)
@click.option(
    "--limit",
    default=DEFAULT_IMAGES_LIMIT,
    show_default=True,
    type=click.IntRange(min=1),
    help="Максимальное количество изображений.",
)
@click.option(
    "--download",
    is_flag=True,
    help="Скачать изображения в папку.",
)
@click.option(
    "--output",
    default=DEFAULT_DOWNLOAD_DIR,
    show_default=True,
    help="Папка для сохранения изображений.",
)
@click.option(
    "--all",
    "all_images",
    is_flag=True,
    help="Обработать все изображения, полученные командой.",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Включить подробное логирование работы команды.",
)
@click.pass_context
def images(
    ctx: click.Context,
    title: str,
    lang: str,
    limit: int,
    download: bool,
    output: str,
    all_images: bool,
    verbose: bool,
) -> None:
    """Показать и при необходимости скачать изображения статьи Wikipedia."""
    renderer = ConsoleRenderer()
    service = ImageService()
    _is_verbose(ctx, verbose)

    logger.info("Command started: images")
    logger.info(
        "Command parameters: title=%s, lang=%s, limit=%s, download=%s, "
        "all=%s, output=%s",
        title,
        lang,
        limit,
        download,
        all_images,
        output,
    )

    try:
        article_images = service.get_images(
            title=title,
            lang=lang,
            limit=limit,
            download=download,
            output=output,
            all_images=all_images,
        )
        renderer.render_images(article_images)
        logger.info("Command finished successfully")
    except (WikiExplorerError, ValueError) as exc:
        logger.error("Command failed: %s", exc)
        renderer.render_error(str(exc))
        raise click.Abort() from exc
