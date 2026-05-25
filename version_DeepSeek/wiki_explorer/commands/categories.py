"""Команда для вывода категорий статьи."""

import sys
from typing import List

import click
from rich.console import Console
from rich.table import Table

from wiki_explorer.api.mediawiki import get_categories, get_parent_categories
from wiki_explorer.utils.errors import NotFoundError, ApiError, NetworkError

console = Console()


@click.command(name="categories")
@click.argument("title")
@click.option("--tree", is_flag=True, help="Показать родительские категории для каждой категории")
@click.pass_context
def categories(ctx, title: str, tree: bool):
    """
    Выводит категории, в которые входит статья.

    Примеры:
      wiki-explorer categories "Python"
      wiki-explorer categories "Россия" --tree
    """
    # Получаем язык из контекста (глобальная опция --lang)
    lang = ctx.obj.get("lang", "ru") if ctx.obj else "ru"
    verbose = ctx.obj.get("verbose", False) if ctx.obj else False

    # Получаем список категорий статьи
    try:
        cat_list = get_categories(title, lang)
    except NotFoundError as e:
        console.print(f"[red]Ошибка: {e}[/red]")
        sys.exit(1)
    except (ApiError, NetworkError) as e:
        console.print(f"[red]Ошибка API/сети: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        if verbose:
            console.print_exception()
        else:
            console.print(f"[red]Неожиданная ошибка: {e}[/red]")
        sys.exit(1)

    if not cat_list:
        console.print("Категории отсутствуют")
        return

    # Режим без --tree: плоский список
    if not tree:
        table = Table(title=f"Категории статьи '{title}'", box=None)
        table.add_column("№", style="bold cyan", width=4)
        table.add_column("Категория", style="white")
        for idx, cat in enumerate(cat_list, start=1):
            table.add_row(str(idx), cat)
        console.print(table)
        return

    # Режим с --tree: получаем родительские категории
    try:
        parents = get_parent_categories(cat_list, lang)
    except (ApiError, NetworkError) as e:
        console.print(f"[red]Ошибка при получении родительских категорий: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        if verbose:
            console.print_exception()
        else:
            console.print(f"[red]Неожиданная ошибка: {e}[/red]")
        sys.exit(1)

    table = Table(title=f"Категории статьи '{title}' (с родителями)", box=None)
    table.add_column("Категория", style="white")
    table.add_column("Родительская категория", style="dim")
    for cat in cat_list:
        parent = parents.get(cat, None)
        parent_display = parent if parent else "—"
        table.add_row(cat, parent_display)
    console.print(table)