"""Команда random: выбор случайной статьи с фильтрацией."""

import sys
import random
import re
from typing import List, Optional

import click
from rich.console import Console
from rich.table import Table

from wiki_explorer.api.mediawiki import (
    get_random_page,
    get_category_members,
    fetch_page_extract,
    page_has_images,
)
from wiki_explorer.utils.errors import NotFoundError, ApiError, NetworkError

console = Console()


def count_words(text: str) -> int:
    """Подсчитывает количество слов в тексте (разбиение по пробелам и знакам препинания)."""
    if not text:
        return 0
    # Разбиваем по любым не-буквенным символам (упрощённо)
    words = re.findall(r"\b\w+\b", text)
    return len(words)


def extract_first_sentence(extract: str) -> str:
    """
    Извлекает первое предложение из текста.
    Предложение заканчивается на '.', '!', '?' или конце строки.
    """
    if not extract:
        return ""
    # Ищем первую точку, восклицательный или вопросительный знак
    for i, ch in enumerate(extract):
        if ch in ".!?":
            return extract[:i+1].strip()
    return extract.strip()


@click.command("random")
@click.option("--category", help="Ограничиться статьями из указанной категории")
@click.option("--min-words", type=int, default=0, help="Минимальное количество слов в статье")
@click.option("--with-image", is_flag=True, help="Требовать наличие хотя бы одного изображения")
@click.option("--max-attempts", type=int, default=10, help="Количество попыток подобрать статью")
@click.pass_context
def random_cmd(ctx: click.Context, category: Optional[str], min_words: int,
               with_image: bool, max_attempts: int):
    """
    Выбирает случайную статью с возможной фильтрацией.

    Примеры:
        wiki-explorer random
        wiki-explorer random --category "Science"
        wiki-explorer random --min-words 500 --with-image --max-attempts 20
    """
    lang = ctx.obj.get("lang", "en")
    verbose = ctx.obj.get("verbose", False)

    # Определяем источник случайных статей
    use_category = category is not None
    category_members = None

    if use_category:
        if verbose:
            console.print(f"[dim]Получение списка статей из категории '{category}'...[/dim]")
        try:
            category_members = get_category_members(lang, category)
        except ApiError as e:
            console.print(f"[red]Ошибка API: {e}[/red]")
            sys.exit(1)
        except NetworkError as e:
            console.print(f"[red]Сетевая ошибка: {e}[/red]")
            sys.exit(1)
        if not category_members:
            console.print(f"[yellow]Категория '{category}' не найдена или пуста.[/yellow]")
            sys.exit(1)
        if verbose:
            console.print(f"[dim]Найдено {len(category_members)} статей в категории.[/dim]")

    applied_filters = []
    if category:
        applied_filters.append(f"✅ Категория: {category}")
    if min_words > 0:
        applied_filters.append(f"✅ Минимум слов: {min_words}")
    if with_image:
        applied_filters.append("✅ Есть изображение")

    for attempt in range(1, max_attempts + 1):
        if verbose:
            console.print(f"[dim]Попытка {attempt}/{max_attempts}...[/dim]")

        # 1. Выбираем случайную статью
        if use_category:
            # Случайная статья из категории
            title = random.choice(category_members)
        else:
            # Случайная статья через API
            try:
                rand_page = get_random_page(lang)
                title = rand_page["title"]
            except (ApiError, NetworkError) as e:
                console.print(f"[red]Ошибка при получении случайной статьи: {e}[/red]")
                sys.exit(1)

        # 2. Проверяем фильтры (по одному, чтобы не делать лишних запросов)
        ok = True

        # Проверка min-words
        if min_words > 0:
            try:
                extract = fetch_page_extract(title, lang)
                word_count = count_words(extract)
                if word_count < min_words:
                    if verbose:
                        console.print(f"[dim]  - {title}: слов {word_count} < {min_words}[/dim]")
                    ok = False
            except (ApiError, NetworkError, NotFoundError) as e:
                if verbose:
                    console.print(f"[dim]  - {title}: ошибка при получении описания: {e}[/dim]")
                ok = False

        if not ok:
            continue

        # Проверка with-image
        if with_image:
            try:
                has_img = page_has_images(title, lang)
                if not has_img:
                    if verbose:
                        console.print(f"[dim]  - {title}: нет изображений[/dim]")
                    ok = False
            except (ApiError, NetworkError, NotFoundError) as e:
                if verbose:
                    console.print(f"[dim]  - {title}: ошибка при проверке изображений: {e}[/dim]")
                ok = False

        if not ok:
            continue

        # Если дошли сюда — статья подходит
        # Получаем описание (можно повторно использовать extract)
        if min_words > 0:
            # extract уже был получен
            description = extract_first_sentence(extract) if min_words > 0 else ""
        else:
            try:
                extract = fetch_page_extract(title, lang)
                description = extract_first_sentence(extract)
            except (ApiError, NetworkError, NotFoundError):
                description = "Описание отсутствует"

        # Вывод результата
        url = f"https://{lang}.wikipedia.org/wiki/{title.replace(' ', '_')}"
        console.print(f"\n[bold cyan]{title}[/bold cyan]")
        console.print(f"[white]{description}[/white]")
        console.print(f"[dim]{url}[/dim]")
        if applied_filters:
            console.print("\n[green]Применённые фильтры:[/green]")
            for f in applied_filters:
                console.print(f"  {f}")
        else:
            console.print("\n[green]Фильтры не заданы.[/green]")
        return

    # Попытки закончились
    console.print(f"[red]Не найдено подходящей статьи за {max_attempts} попыток.[/red]")
    sys.exit(1)