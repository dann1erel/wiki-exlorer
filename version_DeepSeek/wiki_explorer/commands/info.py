"""Команда info: вывод подробной информации о статье Wikipedia."""

from datetime import datetime
import click
from rich.console import Console
from rich.table import Table

from wiki_explorer.api.mediawiki import fetch_article_info, fetch_image_url
from wiki_explorer.utils.errors import NotFoundError, ApiError, NetworkError

console = Console()

def format_timestamp(ts: str) -> str:
    if not ts:
        return "—"
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return ts

@click.command("info")
@click.argument("title")
@click.option("--show-categories", is_flag=True, help="Показать первые 10 категорий")
@click.option("--show-image-url", is_flag=True, help="Показать URL главного изображения")
@click.pass_context
def info(ctx: click.Context, title: str, show_categories: bool, show_image_url: bool) -> None:
    lang = ctx.obj.get("lang", "en")
    verbose = ctx.obj.get("verbose", False)
    if verbose:
        console.print(f"[dim]Запрос информации о статье '{title}' (lang={lang})...[/dim]")
    try:
        data = fetch_article_info(title, lang)
    except NotFoundError as e:
        console.print(f"[red]Ошибка: {e}[/red]")
        raise SystemExit(1)
    except NetworkError as e:
        console.print(f"[red]Сетевая ошибка: {e}[/red]")
        raise SystemExit(1)
    except ApiError as e:
        console.print(f"[red]Ошибка API: {e}[/red]")
        raise SystemExit(1)
    table = Table(title=f"Информация о статье: {data['title']}", show_header=False, box=None)
    table.add_column("Атрибут", style="bold cyan", no_wrap=True)
    table.add_column("Значение", style="white")
    table.add_row("Заголовок", data["title"])
    table.add_row("Размер (байт)", str(data["size"]))
    table.add_row("Внутренние ссылки", str(data["links"]))
    table.add_row("Дата создания", format_timestamp(data["created"]))
    table.add_row("Последняя правка", format_timestamp(data["last_modified"]))
    table.add_row("Последний редактор", data["last_editor"] or "—")
    if show_categories:
        categories = data["categories"]
        if categories:
            cats_text = "\n".join(f"• {cat}" for cat in categories[:10])
            if len(categories) > 10:
                cats_text += f"\n... и ещё {len(categories) - 10}"
        else:
            cats_text = "—"
        table.add_row("Категории (первые 10)", cats_text)
    if show_image_url:
        image_title = data.get("image_title")
        if image_title:
            if verbose:
                console.print(f"[dim]Запрос URL изображения '{image_title}'...[/dim]")
            image_url = fetch_image_url(image_title, lang)
            if image_url:
                table.add_row("URL главного изображения", image_url)
            else:
                table.add_row("URL главного изображения", "[red]Не удалось получить URL[/red]")
        else:
            table.add_row("URL главного изображения", "[yellow]Изображение не найдено[/yellow]")
    console.print(table)