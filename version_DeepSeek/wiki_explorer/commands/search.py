"""Команда search: поиск статей Wikipedia."""

import re
from datetime import datetime

import click
from rich.console import Console
from rich.table import Table

from wiki_explorer.api.mediawiki import search_articles
from wiki_explorer.utils.errors import NetworkError, ApiError

console = Console()


def strip_html_tags(html_text: str) -> str:
    """
    Удаляет HTML-теги из строки (простой regex).
    Заменяет <span class="searchmatch">...</span> и прочие теги на обычный текст.
    """
    # Удаляем все теги
    clean = re.sub(r"<[^>]+>", "", html_text)
    # Преобразуем HTML-сущности
    clean = clean.replace("&quot;", '"').replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return clean


def format_timestamp(ts: str) -> str:
    """Форматирует ISO-8601 дату в читаемый вид."""
    if not ts:
        return "—"
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return ts


@click.command("search")
@click.argument("query")
@click.option("--limit", default=10, help="Количество результатов (макс. 100)", show_default=True)
@click.option("--sort", type=click.Choice(["relevance", "last_edit", "last_edit_desc"]),
              default="relevance", help="Сортировка результатов. last_edit = last_edit_desc", show_default=True)
@click.option("--namespace", default=0, help="Пространство имён (0 = статьи)", show_default=True)
@click.pass_context
def search(ctx: click.Context, query: str, limit: int, sort: str, namespace: int) -> None:
    """
    Выполняет поиск статей по запросу QUERY.

    Пример: wiki-explorer search "Python programming" --limit 5 --sort last_edit
    """
    lang = ctx.obj.get("lang", "en")
    verbose = ctx.obj.get("verbose", False)

    # Ограничение лимита и предупреждение
    if limit > 100:
        console.print("[yellow]Внимание: максимальное значение --limit ограничено 100.[/yellow]")
        effective_limit = 100
    else:
        effective_limit = limit

    # Преобразование sort для обратной совместимости
    if sort == "last_edit":
        sort = "last_edit_desc"
        if verbose:
            console.print("[dim]Замечание: last_edit преобразован в last_edit_desc[/dim]")

    if verbose:
        console.print(f"[dim]Поиск: '{query}' (lang={lang}, limit={effective_limit}, sort={sort}, namespace={namespace})[/dim]")

    try:
        result = search_articles(query, lang, effective_limit, sort, namespace)
    except NetworkError as e:
        console.print(f"[red]Сетевая ошибка: {e}[/red]")
        raise SystemExit(1)
    except ApiError as e:
        console.print(f"[red]Ошибка API: {e}[/red]")
        if verbose:
            # Дополнительная диагностика: подсказка для ручной проверки URL
            url = f"https://{lang}.wikipedia.org/w/api.php"
            params = f"action=query&list=search&srsearch={query}&srlimit={effective_limit}&srsort={sort}&srnamespace={namespace}&format=json"
            console.print(f"[dim]Проверьте в браузере: {url}?{params}[/dim]")
        raise SystemExit(1)

    search_results = result.get("search", [])
    if not search_results:
        console.print("[yellow]Ничего не найдено.[/yellow]")
        return

    # Создаём таблицу
    table = Table(title=f"Результаты поиска: '{query}'", box=None)
    table.add_column("Заголовок", style="bold cyan", no_wrap=False)
    table.add_column("Краткое описание", style="white", no_wrap=False)
    table.add_column("Дата последней правки", style="dim", no_wrap=True)

    for item in search_results:
        title = item.get("title", "")
        snippet_html = item.get("snippet", "")
        snippet_clean = strip_html_tags(snippet_html)
        timestamp = item.get("timestamp", "")
        formatted_date = format_timestamp(timestamp)

        table.add_row(title, snippet_clean, formatted_date)

    console.print(table)

    # Если найдено меньше, чем запрошено, выводим количество
    if len(search_results) < effective_limit and limit <= 100:
        console.print(f"[dim]Найдено {len(search_results)} результатов.[/dim]")