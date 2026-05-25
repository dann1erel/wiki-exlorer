"""Тесты для модуля errors."""

import pytest
from wiki_explorer.utils.errors import (
    WikiExplorerError,
    NotFoundError,
    ApiError,
    NetworkError,
)


def test_exceptions_inheritance():
    """Проверка иерархии исключений."""
    assert issubclass(NotFoundError, WikiExplorerError)
    assert issubclass(ApiError, WikiExplorerError)
    assert issubclass(NetworkError, WikiExplorerError)


def test_exceptions_can_be_raised():
    """Проверка, что исключения можно поднимать и они содержат сообщение."""
    with pytest.raises(NotFoundError, match="Статья не найдена"):
        raise NotFoundError("Статья не найдена")

    with pytest.raises(ApiError, match="API error"):
        raise ApiError("API error")

    with pytest.raises(NetworkError, match="Таймаут"):
        raise NetworkError("Таймаут")