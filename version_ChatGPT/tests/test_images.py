"""Tests for the `images` command implementation."""

from __future__ import annotations

from pathlib import Path

import pytest
import requests
from click.testing import CliRunner

from wiki_explorer.api.mediawiki_client import MediaWikiClient
from wiki_explorer.cli import cli
from wiki_explorer.exceptions import (
    ApiRequestError,
    ArticleNotFoundError,
    InvalidUserInputError,
)
from wiki_explorer.services.image_service import ImageService

API_URL = "https://en.wikipedia.org/w/api.php"
IMAGE_URL = "https://upload.wikimedia.org/example/Python-logo.png"


def _article_images_response(
    title: str = "Python",
    images: list[dict] | None = None,
    missing: bool = False,
) -> dict:
    page = {"title": title}
    if missing:
        page["missing"] = True
    else:
        page["pageid"] = 23862
        page["images"] = images if images is not None else [
            {"title": "File:Python-logo.png"}
        ]
    return {"query": {"pages": [page]}}


def _imageinfo_response(
    title: str = "File:Python-logo.png",
    url: str = IMAGE_URL,
    size: int = 2048,
    mime: str = "image/png",
) -> dict:
    return {
        "query": {
            "pages": [
                {
                    "pageid": 1,
                    "title": title,
                    "imageinfo": [
                        {
                            "url": url,
                            "size": size,
                            "mime": mime,
                        }
                    ],
                }
            ]
        }
    }


def test_get_images_success(requests_mock):
    """Service should fetch image list and imageinfo."""
    requests_mock.get(
        API_URL,
        [
            {"json": _article_images_response()},
            {"json": _imageinfo_response()},
        ],
    )

    service = ImageService(MediaWikiClient())
    result = service.get_images("Python", lang="en", limit=10)

    assert result.title == "Python"
    assert result.page_id == 23862
    assert len(result.images) == 1
    assert result.images[0].title == "File:Python-logo.png"
    assert result.images[0].url == IMAGE_URL
    assert result.images[0].mime == "image/png"
    assert result.images[0].size_bytes == 2048

    first_request = requests_mock.request_history[0]
    assert first_request.qs["prop"] == ["images"]
    assert first_request.qs["titles"] == ["python"]
    assert first_request.qs["imlimit"] == ["10"]

    second_request = requests_mock.request_history[1]
    assert second_request.qs["prop"] == ["imageinfo"]
    assert second_request.qs["titles"] == ["file:python-logo.png"]
    assert second_request.qs["iiprop"] == ["url|size|mime"]


def test_get_images_article_not_found(requests_mock):
    """Missing article should be converted to ArticleNotFoundError."""
    requests_mock.get(API_URL, json=_article_images_response(missing=True))

    service = ImageService(MediaWikiClient())

    with pytest.raises(ArticleNotFoundError):
        service.get_images("Unknown", lang="en")


def test_get_images_empty_list(requests_mock):
    """Article without images should return an empty image list."""
    requests_mock.get(
        API_URL,
        json=_article_images_response(images=[]),
    )

    service = ImageService(MediaWikiClient())
    result = service.get_images("Python", lang="en")

    assert result.images == []


def test_get_imageinfo_success(requests_mock):
    """Service should normalize imageinfo details."""
    requests_mock.get(API_URL, json=_imageinfo_response())

    service = ImageService(MediaWikiClient())
    image = service._get_single_image_info("File:Python-logo.png", "en")

    assert image.title == "File:Python-logo.png"
    assert image.url == IMAGE_URL
    assert image.size_bytes == 2048
    assert image.mime == "image/png"


def test_download_image_success(requests_mock, tmp_path):
    """Service should download images to the requested directory."""
    requests_mock.get(
        API_URL,
        [
            {"json": _article_images_response()},
            {"json": _imageinfo_response()},
        ],
    )
    requests_mock.get(IMAGE_URL, content=b"image-bytes")

    service = ImageService(MediaWikiClient())
    result = service.get_images(
        "Python",
        lang="en",
        limit=10,
        download=True,
        output=str(tmp_path),
    )

    assert len(result.download_results) == 1
    download_result = result.download_results[0]
    assert download_result.success is True
    assert download_result.path is not None
    assert download_result.path.exists()
    assert download_result.path.read_bytes() == b"image-bytes"


def test_download_error_does_not_break_command(requests_mock, tmp_path):
    """One failed image download should be stored as partial error."""
    requests_mock.get(
        API_URL,
        [
            {"json": _article_images_response()},
            {"json": _imageinfo_response()},
        ],
    )
    requests_mock.get(IMAGE_URL, exc=requests.exceptions.Timeout("timeout"))

    service = ImageService(MediaWikiClient())
    result = service.get_images(
        "Python",
        lang="en",
        download=True,
        output=str(tmp_path),
    )

    assert len(result.download_results) == 1
    assert result.download_results[0].success is False
    assert "timeout" in result.download_results[0].error


def test_images_invalid_limit():
    """Service should reject non-positive limits."""
    service = ImageService(MediaWikiClient())

    with pytest.raises(InvalidUserInputError):
        service.get_images("Python", limit=0)


def test_safe_filename():
    """Image filenames should be safe for common filesystems."""
    service = ImageService(MediaWikiClient())

    assert service._safe_filename('File:Bad<Name>?.jpg') == "Bad_Name__.jpg"
    assert service._safe_filename("Файл:Картинка тест.png") == "Картинка_тест.png"


def test_images_default_download_directory(requests_mock, tmp_path, monkeypatch):
    """Default downloads directory should be created automatically."""
    monkeypatch.chdir(tmp_path)
    requests_mock.get(
        API_URL,
        [
            {"json": _article_images_response()},
            {"json": _imageinfo_response()},
        ],
    )
    requests_mock.get(IMAGE_URL, content=b"image-bytes")

    service = ImageService(MediaWikiClient())
    result = service.get_images("Python", lang="en", download=True)

    assert Path("downloads").exists()
    assert result.download_results[0].success is True


def test_images_cli_verbose_outputs_logs(requests_mock):
    """Local --verbose should enable logging for the images command."""
    requests_mock.get(
        API_URL,
        [
            {"json": _article_images_response()},
            {"json": _imageinfo_response()},
        ],
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["images", "Python", "--lang", "en", "--verbose"],
    )

    assert result.exit_code == 0
    assert "Command started: images" in result.output
    assert "Python-logo" in result.output


def test_images_api_error(requests_mock):
    """Client request errors should be converted to ApiRequestError."""
    requests_mock.get(API_URL, exc=requests.exceptions.Timeout("timeout"))

    service = ImageService(MediaWikiClient())

    with pytest.raises(ApiRequestError):
        service.get_images("Python", lang="en")


def test_download_retries_after_rate_limit(requests_mock, tmp_path, monkeypatch):
    """429 Too Many Requests should be retried instead of breaking immediately."""
    monkeypatch.setattr(
        "wiki_explorer.services.image_service.time.sleep",
        lambda seconds: None,
    )
    requests_mock.get(
        API_URL,
        [
            {"json": _article_images_response()},
            {"json": _imageinfo_response()},
        ],
    )
    requests_mock.get(
        IMAGE_URL,
        [
            {"status_code": 429, "headers": {"Retry-After": "1"}},
            {"content": b"image-bytes"},
        ],
    )

    service = ImageService(MediaWikiClient())
    result = service.get_images(
        "Python",
        lang="en",
        download=True,
        output=str(tmp_path),
    )

    assert result.download_results[0].success is True
    assert result.download_results[0].path is not None
    assert result.download_results[0].path.read_bytes() == b"image-bytes"


def test_download_persistent_rate_limit_is_partial_error(
    requests_mock,
    tmp_path,
    monkeypatch,
):
    """Repeated 429 responses should be reported as one image download error."""
    monkeypatch.setattr(
        "wiki_explorer.services.image_service.time.sleep",
        lambda seconds: None,
    )
    requests_mock.get(
        API_URL,
        [
            {"json": _article_images_response()},
            {"json": _imageinfo_response()},
        ],
    )
    requests_mock.get(IMAGE_URL, status_code=429)

    service = ImageService(MediaWikiClient())
    result = service.get_images(
        "Python",
        lang="en",
        download=True,
        output=str(tmp_path),
    )

    assert result.download_results[0].success is False
    assert "429" in result.download_results[0].error
