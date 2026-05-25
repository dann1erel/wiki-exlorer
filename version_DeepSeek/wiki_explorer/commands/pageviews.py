"""Команда CLI для получения статистики просмотров статьи."""

import sys
from datetime import datetime
from typing import List, Dict

import click
from rich.console import Console
from rich.table import Table

from wiki_explorer.api.pageviews import fetch_pageviews
from wiki_explorer.utils.errors import NetworkError

console = Console()


def _print_ascii_chart(data: List[Dict[str, any]], width: int = 50) -> None:
    """
    Выводит горизонтальную столбчатую диаграмму в консоль.
    data: список словарей с ключами 'date' и 'views'
    """
    if not data:
        return
    max_views = max(item["views"] for item in data)
    if max_views == 0:
        console.print("[yellow]Нет данных для построения графика (все просмотры = 0)[/yellow]")
        return

    console.print("\n[bold cyan]ASCII-график просмотров по дням:[/bold cyan]")
    for item in data:
        date = item["date"]
        views = item["views"]
        bar_len = int(views / max_views * width)
        bar = "█" * bar_len if bar_len > 0 else "·"
        console.print(f"{date} | {bar} {views}")


def _save_png_chart(data: List[Dict[str, any]], title: str, output_path: str) -> None:
    """
    Сохраняет график просмотров в PNG-файл через matplotlib.
    Если matplotlib не установлен, выводит предупреждение.
    """
    try:
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        from datetime import datetime as dt
    except ImportError:
        console.print("[yellow]Предупреждение: matplotlib не установлен. График не сохранён.[/yellow]")
        return

    if not data:
        console.print("[yellow]Нет данных для сохранения графика.[/yellow]")
        return

    dates = [dt.strptime(item["date"], "%Y-%m-%d") for item in data]
    views = [item["views"] for item in data]

    plt.figure(figsize=(12, 6))
    plt.bar(dates, views, width=0.8, color='steelblue')
    plt.title(f"Просмотры статьи '{title}'")
    plt.xlabel("Дата")
    plt.ylabel("Количество просмотров")
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    plt.gcf().autofmt_xdate()  # поворот подписей
    plt.tight_layout()
    plt.savefig(output_path, dpi=100)
    plt.close()
    console.print(f"[green]График сохранён в файл: {output_path}[/green]")


@click.command(name="pageviews")
@click.argument("title")
@click.option("--days", default=30, type=int, help="Количество последних дней (макс. 90)", show_default=True)
@click.option("--chart", type=click.Choice(["ascii", "png"]), help="Тип графика: ascii (в консоль) или png (в файл)")
@click.option("--output", type=str, help="Путь для сохранения PNG (по умолчанию pageviews_<title>.png)")
@click.pass_context
def pageviews(ctx, title: str, days: int, chart: str, output: str) -> None:
    """
    Получает статистику просмотров статьи за последние N дней.

    Примеры:
      wiki-explorer pageviews "Python"
      wiki-explorer pageviews "Россия" --days 60 --chart ascii
      wiki-explorer pageviews "Berlin" --chart png --output my_graph.png
    """
    # Ограничение days
    if days > 90:
        console.print("[red]Ошибка: максимальное количество дней — 90.[/red]")
        sys.exit(1)
    if days < 1:
        console.print("[red]Ошибка: количество дней должно быть не меньше 1.[/red]")
        sys.exit(1)

    # Определяем язык из контекста? Пока фиксируем русский, но можно расширить.
    # В реальном проекте язык может браться из глобальной опции или из аргумента.
    # Для простоты используем русский, но можно передать через опцию --lang.
    # Согласно заданию, у нас уже есть lang в других командах, предположим, что
    # cli.py передаёт язык через контекст. Здесь сделаем заглушку: lang = "ru".
    # При необходимости замените на ctx.obj['lang'] или аналогично.
    lang = "ru"  # TODO: получать из контекста или добавить опцию --lang

    try:
        data = fetch_pageviews(title, lang, days)
    except ConnectionError as e:
        console.print(f"[red]Сетевая ошибка: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Неизвестная ошибка: {e}[/red]")
        sys.exit(1)

    if not data:
        console.print("[yellow]Нет данных о просмотрах...[/yellow]")
        sys.exit(0)

    # Обрезаем хвостовые нули
    original_len = len(data)
    data = _trim_trailing_zeros(data)
    if not data:
        console.print("[yellow]Нет данных о просмотрах после удаления дней без информации (все дни были нулевыми).[/yellow]")
        sys.exit(0)
    if len(data) < original_len:
        console.print(f"[dim]Примечание: удалено {original_len - len(data)} последних дней без данных (нулевые просмотры).[/dim]")

    # Таблица с датами и просмотрами
    table = Table(title=f"Статистика просмотров статьи '{title}' (последние {len(data)} дней)", box=None)
    table.add_column("Дата", style="cyan")
    table.add_column("Просмотры", style="white", justify="right")
    for item in data:
        table.add_row(item["date"], str(item["views"]))
    console.print(table)

    # Статистика
    views_list = [item["views"] for item in data]
    total = sum(views_list)
    average = total / len(views_list)
    maximum = max(views_list)
    minimum = min(views_list)

    console.print(f"\n[bold]Сумма:[/bold] {total}")
    console.print(f"[bold]Среднее:[/bold] {average:.1f}")
    console.print(f"[bold]Максимум:[/bold] {maximum}")
    console.print(f"[bold]Минимум:[/bold] {minimum}")

    # График
    if chart == "ascii":
        _print_ascii_chart(data)
    elif chart == "png":
        if not output:
            # Санитизируем название статьи для имени файла
            safe_title = "".join(c for c in title if c.isalnum() or c in " _-").replace(" ", "_")
            output = f"pageviews_{safe_title}.png"
        _save_png_chart(data, title, output)

        # Добавьте эту функцию перед функцией pageviews

def _trim_trailing_zeros(data: List[Dict[str, any]]) -> List[Dict[str, any]]:
    """
    Удаляет последние дни, в которых просмотры = 0.
    Если все дни нулевые, возвращает пустой список.
    """
    if not data:
        return data
    # Идём с конца и отрезаем, пока встречаем views == 0
    trimmed = data[:]
    while trimmed and trimmed[-1]["views"] == 0:
        trimmed.pop()
    return trimmed