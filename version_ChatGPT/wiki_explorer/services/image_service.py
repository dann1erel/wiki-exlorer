"""Business logic for the `images` command."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from pathlib import Path
import re
import time
from typing import Any
from urllib.parse import unquote, urlparse

import requests

from wiki_explorer.api.mediawiki_client import MediaWikiClient
from wiki_explorer.config import (
    DEFAULT_DOWNLOAD_DIR,
    DEFAULT_IMAGE_DOWNLOAD_DELAY,
    DEFAULT_IMAGE_DOWNLOAD_RETRIES,
    DEFAULT_IMAGES_LIMIT,
    DEFAULT_LANGUAGE,
    DEFAULT_TIMEOUT,
    USER_AGENT,
)
from wiki_explorer.exceptions import (
    ArticleNotFoundError,
    FileSaveError,
    ImageDownloadError,
    InvalidApiResponseError,
    InvalidUserInputError,
)


logger = logging.getLogger(__name__)


def _build_image_download_headers(lang: str = DEFAULT_LANGUAGE) -> dict[str, str]:
    """Return headers for direct Wikimedia file downloads.

    Wikimedia may reject generic Python HTTP clients when downloading
    files from upload.wikimedia.org. MediaWiki API requests already use
    User-Agent, but direct file URLs need the same explicit headers too.
    """
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36 Wiki-Explorer/0.1"
        ),
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
        "Referer": f"https://{lang}.wikipedia.org/",
        "Connection": "keep-alive",
    }


@dataclass(frozen=True)
class ImageInfo:
    """One normalized image item."""

    title: str
    url: str | None = None
    mime: str | None = None
    size_bytes: int | None = None


@dataclass(frozen=True)
class ImageDownloadResult:
    """Result of downloading one image."""

    image_title: str
    success: bool
    path: Path | None = None
    error: str | None = None


@dataclass(frozen=True)
class ArticleImages:
    """Prepared data for the `images` command output."""

    title: str
    page_id: int
    images: list[ImageInfo] = field(default_factory=list)
    download_results: list[ImageDownloadResult] = field(default_factory=list)


class ImageService:
    """Service for retrieving and optionally downloading article images."""

    def __init__(
        self,
        client: MediaWikiClient | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self.client = client or MediaWikiClient()
        self.timeout = timeout

    def get_images(
        self,
        title: str,
        lang: str = DEFAULT_LANGUAGE,
        limit: int = DEFAULT_IMAGES_LIMIT,
        download: bool = False,
        output: str = DEFAULT_DOWNLOAD_DIR,
        all_images: bool = False,
    ) -> ArticleImages:
        """Get article images and optionally download them to a directory."""
        if limit <= 0:
            raise InvalidUserInputError(
                "Параметр --limit должен быть положительным числом."
            )

        logger.info(
            "Images command service started: title=%s, lang=%s, limit=%s, "
            "download=%s, all=%s, output=%s",
            title,
            lang,
            limit,
            download,
            all_images,
            output,
        )

        data = self.client.get_article_images(
            title=title,
            lang=lang,
            limit=limit,
        )
        page = self._extract_page(data, title)
        image_titles = self._extract_image_titles(page)
        logger.info("Images found in article: %s", len(image_titles))

        selected_titles = image_titles if all_images else image_titles[:limit]
        image_infos = [
            self._get_single_image_info(image_title, lang)
            for image_title in selected_titles
        ]
        logger.info("Imageinfo requests completed: %s", len(image_infos))

        download_results: list[ImageDownloadResult] = []
        if download:
            output_dir = self._ensure_output_dir(output)
            for image in image_infos:
                result = self._download_image(image, output_dir, lang)
                download_results.append(result)
                if image is not image_infos[-1]:
                    time.sleep(DEFAULT_IMAGE_DOWNLOAD_DELAY)

        return ArticleImages(
            title=str(page.get("title", title)),
            page_id=int(page.get("pageid", 0)),
            images=image_infos,
            download_results=download_results,
        )

    def _get_single_image_info(self, image_title: str, lang: str) -> ImageInfo:
        """Fetch imageinfo and normalize one image item."""
        data = self.client.get_image_info(image_title=image_title, lang=lang)
        pages = data.get("query", {}).get("pages")

        if not isinstance(pages, list) or not pages:
            raise InvalidApiResponseError(
                "API вернул некорректный ответ. Невозможно получить изображения."
            )

        page = pages[0]
        if not isinstance(page, dict):
            raise InvalidApiResponseError(
                "API вернул некорректную структуру данных изображения."
            )

        imageinfo = page.get("imageinfo", [])
        if imageinfo is None:
            imageinfo = []
        if not isinstance(imageinfo, list):
            raise InvalidApiResponseError(
                "API вернул некорректную структуру imageinfo."
            )

        info = imageinfo[0] if imageinfo else {}
        if not isinstance(info, dict):
            info = {}

        size = info.get("size")
        return ImageInfo(
            title=str(page.get("title") or image_title),
            url=str(info.get("url")) if info.get("url") else None,
            mime=str(info.get("mime")) if info.get("mime") else None,
            size_bytes=size if isinstance(size, int) else None,
        )

    @staticmethod
    def _extract_page(data: dict[str, Any], title: str) -> dict[str, Any]:
        pages = data.get("query", {}).get("pages")

        if not isinstance(pages, list) or not pages:
            raise InvalidApiResponseError(
                "API вернул некорректный ответ. Невозможно получить изображения."
            )

        page = pages[0]
        if not isinstance(page, dict):
            raise InvalidApiResponseError(
                "API вернул некорректную структуру объекта страницы."
            )

        if page.get("missing") is True or "pageid" not in page:
            raise ArticleNotFoundError(f'Статья "{title}" не найдена.')

        return page

    @staticmethod
    def _extract_image_titles(page: dict[str, Any]) -> list[str]:
        images = page.get("images", [])
        if images is None:
            return []
        if not isinstance(images, list):
            raise InvalidApiResponseError(
                "API вернул некорректную структуру списка изображений."
            )

        return [
            str(image.get("title"))
            for image in images
            if isinstance(image, dict) and image.get("title")
        ]

    @staticmethod
    def _ensure_output_dir(output: str) -> Path:
        output_dir = Path(output)
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise FileSaveError(
                "Ошибка: не удалось создать папку для сохранения изображений. "
                "Проверьте путь и права доступа."
            ) from exc

        if not output_dir.is_dir():
            raise FileSaveError(
                "Ошибка: путь для сохранения изображений не является папкой."
            )

        return output_dir

    def _download_image(
        self,
        image: ImageInfo,
        output_dir: Path,
        lang: str = DEFAULT_LANGUAGE,
    ) -> ImageDownloadResult:
        """Download one image and keep command alive on partial failures."""
        if not image.url:
            message = "у изображения нет прямого URL"
            logger.error("Image download skipped: %s: %s", image.title, message)
            return ImageDownloadResult(
                image_title=image.title,
                success=False,
                error=message,
            )

        try:
            file_path = self._build_unique_file_path(image, output_dir)
            logger.info("Downloading image: %s -> %s", image.url, file_path)
            response = self._download_with_retries(
                url=image.url,
                headers=_build_image_download_headers(lang),
                image_title=image.title,
            )
            file_path.write_bytes(response.content)
            logger.info("Image saved: %s", file_path)
            return ImageDownloadResult(
                image_title=image.title,
                success=True,
                path=file_path,
            )
        except (
            requests.RequestException,
            OSError,
            FileSaveError,
            ImageDownloadError,
        ) as exc:
            logger.error("Image download failed for %s: %s", image.title, exc)
            return ImageDownloadResult(
                image_title=image.title,
                success=False,
                error=str(exc) or "неизвестная ошибка скачивания",
            )

    def _download_with_retries(
        self,
        url: str,
        headers: dict[str, str],
        image_title: str,
    ) -> requests.Response:
        """Download one file with retry/backoff for Wikimedia rate limits."""
        last_response: requests.Response | None = None

        for attempt in range(1, DEFAULT_IMAGE_DOWNLOAD_RETRIES + 1):
            response = requests.get(
                url,
                timeout=self.timeout,
                headers=headers,
            )
            last_response = response
            logger.info(
                "Image download response status for %s: %s",
                image_title,
                response.status_code,
            )

            if response.status_code != 429:
                response.raise_for_status()
                return response

            wait_seconds = self._get_retry_delay(response, attempt)
            logger.warning(
                "Too many requests while downloading %s. "
                "Attempt %s/%s. Waiting %s seconds.",
                image_title,
                attempt,
                DEFAULT_IMAGE_DOWNLOAD_RETRIES,
                wait_seconds,
            )
            time.sleep(wait_seconds)

        if last_response is not None:
            last_response.raise_for_status()

        raise ImageDownloadError(
            f"Не удалось скачать изображение {image_title}: превышен лимит повторов."
        )

    @staticmethod
    def _get_retry_delay(response: requests.Response, attempt: int) -> float:
        """Return retry delay from Retry-After header or exponential fallback."""
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return max(float(retry_after), DEFAULT_IMAGE_DOWNLOAD_DELAY)
            except ValueError:
                logger.debug("Invalid Retry-After header: %s", retry_after)

        return max(DEFAULT_IMAGE_DOWNLOAD_DELAY, 3.0 * attempt)

    def _build_unique_file_path(self, image: ImageInfo, output_dir: Path) -> Path:
        filename = self._safe_filename(image.title, image.url)
        candidate = output_dir / filename

        if not candidate.exists():
            return candidate

        stem = candidate.stem
        suffix = candidate.suffix
        counter = 1
        while True:
            candidate = output_dir / f"{stem}_{counter}{suffix}"
            if not candidate.exists():
                return candidate
            counter += 1

    @staticmethod
    def _safe_filename(title: str, url: str | None = None) -> str:
        """Build a filesystem-safe filename from image title or URL."""
        name = title.split(":", 1)[-1].strip() or "image"
        name = unquote(name)

        if "." not in Path(name).name and url:
            url_name = Path(urlparse(url).path).name
            if url_name:
                name = unquote(url_name)

        safe = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", name)
        safe = re.sub(r"\s+", "_", safe).strip("._ ")
        if not safe:
            safe = "image"
        return safe[:180]
