"""Команда images: список изображений статьи и их скачивание."""

import os
import re
from typing import List, Dict, Any, Tuple

import click
import requests
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, TransferSpeedColumn

from wiki_explorer.api.mediawiki import get_image_list
from wiki_explorer.utils.errors import NotFoundError, ApiError, NetworkError

console = Console()

# Регулярное выражение для очистки имени файла от недопустимых символов
INVALID_CHARS = r'[\\/*?:"<>|]'


def sanitize_filename(filename: str) -> str:
    """Очищает имя файла от недопустимых символов и удаляет префикс 'File:'."""
    # Убираем префикс "File:" или "Файл:" (для русской версии)
    if filename.startswith("File:") or filename.startswith("Файл:"):
        filename = filename.split(":", 1)[-1]
    # Заменяем недопустимые символы на '_'
    return re.sub(INVALID_CHARS, "_", filename)


def download_image(url: str, dest_path: str, progress: Progress, task_id: int) -> bool:
    """
    Скачивает изображение по URL и сохраняет в dest_path.

    Параметры:
        url: URL изображения
        dest_path: полный путь для сохранения
        progress: объект Progress для обновления прогресс-бара
        task_id: идентификатор задачи в progress

    Возвращает:
        True при успехе, False при ошибке.
    """

    if not url:
        progress.update(task_id, description="[red]✗ нет URL")
        return False
    
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        total_size = int(response.headers.get('content-length', 0))
        progress.update(task_id, total=total_size if total_size else None)

        with open(dest_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    progress.update(task_id, advance=len(chunk))
        return True
    except Exception as e:
        console.print(f"[yellow]Предупреждение: не удалось скачать {dest_path}: {e}[/yellow]")
        return False


@click.command("images")
@click.argument("title")
@click.option("--download", is_flag=True, help="Скачать все изображения (в папку --output)")
@click.option("--index", default=None, help="Скачать только указанные изображения (номера через запятую, например 1,3,5)")
@click.option("--output", default="./wiki_images/", help="Папка для сохранения изображений (по умолчанию ./wiki_images/)")
@click.pass_context
def images(ctx: click.Context, title: str, download: bool, index: str, output: str) -> None:
    """
    Выводит список изображений, используемых в статье, и может скачать их.

    Примеры:
        wiki-explorer images "Python"                         # только таблица
        wiki-explorer images "Python" --download              # скачать все
        wiki-explorer images "Python" --index 1,3,5           # скачать 1-е, 3-е и 5-е
    """
    lang = ctx.obj.get("lang", "en")
    verbose = ctx.obj.get("verbose", False)

    # Определяем режим скачивания
    download_mode = False
    indices_to_download = None
    if download:
        download_mode = True
    if index:
        try:
            indices_to_download = [int(i.strip()) for i in index.split(",")]
            download_mode = True  # флаг включён неявно
        except ValueError:
            console.print("[red]Ошибка: --index должен содержать номера через запятую (например 1,3,5)[/red]")
            raise SystemExit(1)

    if verbose:
        console.print(f"[dim]Получение списка изображений для статьи '{title}' (lang={lang})...[/dim]")

    try:
        images_data = get_image_list(title, lang)
    except NotFoundError as e:
        console.print(f"[red]Ошибка: {e}[/red]")
        raise SystemExit(1)
    except NetworkError as e:
        console.print(f"[red]Сетевая ошибка: {e}[/red]")
        raise SystemExit(1)
    except ApiError as e:
        console.print(f"[red]Ошибка API: {e}[/red]")
        raise SystemExit(1)

    if not images_data:
        console.print("[yellow]Изображения отсутствуют.[/yellow]")
        return

    # Выводим таблицу (всегда, даже если будем скачивать)
    table = Table(title=f"Изображения в статье: {title}", box=None)
    table.add_column("#", style="bold cyan", width=4)
    table.add_column("Название файла", style="white", no_wrap=False)
    table.add_column("URL оригинала", style="dim", no_wrap=True)
    table.add_column("Размер (байт)", style="green", justify="right")

    for idx, img in enumerate(images_data, start=1):
        filename = img.get("filename", "")
        url_img = img.get("url", "")
        size = img.get("size", 0)
        size_str = f"{size:,}" if size > 0 else "—"
        table.add_row(str(idx), filename, url_img, size_str)
    console.print(table)

    # Если не нужно скачивать, завершаем
    if not download_mode:
        return

    # Подготовка папки для сохранения
    os.makedirs(output, exist_ok=True)

    # Определяем, какие изображения скачивать
    if indices_to_download:
        # Проверяем корректность индексов
        max_idx = len(images_data)
        for idx in indices_to_download:
            if idx < 1 or idx > max_idx:
                console.print(f"[red]Ошибка: индекс {idx} вне допустимого диапазона (1-{max_idx})[/red]")
                raise SystemExit(1)
        selected = [images_data[idx-1] for idx in indices_to_download]
    else:
        selected = images_data

    if verbose:
        console.print(f"[dim]Скачивание {len(selected)} изображений в '{output}'...[/dim]")

    # Настройка прогресс-бара
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        for img in selected:
            filename_raw = img.get("filename", "image")
            safe_name = sanitize_filename(filename_raw)
            dest_path = os.path.join(output, safe_name)
            # Если файл уже существует, пропускаем?
            if os.path.exists(dest_path):
                console.print(f"[yellow]Файл {dest_path} уже существует, пропускаем.[/yellow]")
                continue

            task = progress.add_task(f"[cyan]Скачивание {safe_name}", total=None)
            success = download_image(img.get("url", ""), dest_path, progress, task)
            if success:
                progress.update(task, description=f"[green]✓ {safe_name}")
                console.print(f"[green]Сохранено: {dest_path}[/green]")
            else:
                progress.update(task, description=f"[red]✗ {safe_name} (ошибка)")