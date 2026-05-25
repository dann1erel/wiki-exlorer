from rich.table import Table
from rich.console import Console

def print_links_table(links: list, title: str = "Ссылки") -> None:
    """
    Выводит таблицу со ссылками.

    Параметры:
        links: список словарей, каждый должен содержать ключ "title"
        title: заголовок таблицы
    """
    console = Console()
    table = Table(title=title, box=None)
    table.add_column("№", style="bold cyan", width=4)
    table.add_column("Ссылка", style="white")
    for idx, link in enumerate(links, start=1):
        table.add_row(str(idx), link.get("title", ""))
    console.print(table)