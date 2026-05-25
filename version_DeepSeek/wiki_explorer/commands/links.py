"""Команда links: вывод списка внутренних ссылок статьи."""

import click
from rich.console import Console

from wiki_explorer.api.mediawiki import fetch_page_links
from wiki_explorer.utils.errors import NotFoundError, ApiError, NetworkError
from wiki_explorer.utils.output import print_links_table

console = Console()


@click.command("links")
@click.argument("title")
@click.option("--limit", default=50, help="Количество ссылок (макс. 500)", show_default=True)
@click.option("--offset", default=0, help="Смещение для пагинации", show_default=True)
@click.option("--search", default=None, help="Фильтр по названию ссылки (регистронезависимо)")
@click.pass_context
def links(ctx: click.Context, title: str, limit: int, offset: int, search: str) -> None:
    """
    Выводит список внутренних ссылок из указанной статьи.

    Пример: wiki-explorer links "Python" --limit 20 --search "програм"
    """
    lang = ctx.obj.get("lang", "en")
    verbose = ctx.obj.get("verbose", False)

    if limit > 500:
        console.print("[yellow]Внимание: максимальное значение --limit ограничено 500.[/yellow]")
        limit = 500

    if verbose:
        console.print(f"[dim]Запрос ссылок для статьи '{title}' (lang={lang}, limit={limit}, offset={offset})[/dim]")

    try:
        data = fetch_page_links(title, lang, limit, offset)
    except NotFoundError as e:
        console.print(f"[red]Ошибка: {e}[/red]")
        raise SystemExit(1)
    except NetworkError as e:
        console.print(f"[red]Сетевая ошибка: {e}[/red]")
        raise SystemExit(1)
    except ApiError as e:
        console.print(f"[red]Ошибка API: {e}[/red]")
        raise SystemExit(1)

    all_links = data.get("links", [])

    # Фильтрация по подстроке (регистронезависимо)
    if search:
        search_lower = search.lower()
        filtered = [link for link in all_links if search_lower in link.get("title", "").lower()]
    else:
        filtered = all_links

    if not filtered:
        if search:
            console.print(f"[yellow]Не найдено ссылок, соответствующих фильтру '{search}'.[/yellow]")
        else:
            console.print("[yellow]Ссылки не найдены.[/yellow]")
        return

    print_links_table(filtered, title=f"Ссылки из статьи: {title}")

    # Если API сообщил, что есть ещё невыгруженные ссылки, подскажем пользователю
    if data.get("has_more"):
        next_offset = offset + limit
        console.print(f"[dim]Ещё есть ссылки. Используйте --offset {next_offset} для следующей страницы.[/dim]")