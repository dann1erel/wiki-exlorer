"""Главная точка входа CLI."""

import click
from wiki_explorer.commands.info import info
from wiki_explorer.commands.search import search
from wiki_explorer.commands.links import links   # добавлено
from wiki_explorer.commands.images import images   # вверху
from wiki_explorer.commands.pageviews import pageviews
from wiki_explorer.commands.categories import categories
from wiki_explorer.commands.graph import graph   # <-- добавить
from wiki_explorer.commands.random import random_cmd as random_command

@click.group()
@click.option("--lang", default="en", help="Язык Wikipedia (ru, en и др.)")
@click.option("--verbose", is_flag=True, help="Подробный вывод")
@click.pass_context
def main(ctx: click.Context, lang: str, verbose: bool) -> None:
    """Wiki Explorer — утилита для работы с Wikipedia через REST API."""
    ctx.obj = {"lang": lang, "verbose": verbose}

main.add_command(info)
main.add_command(search)
main.add_command(links)   # добавлено

main.add_command(images)
main.add_command(pageviews)
main.add_command(categories)
main.add_command(graph)   # <-- добавить
main.add_command(random_command)

if __name__ == "__main__":
    main()