"""Пользовательские исключения для wiki-explorer."""

class WikiExplorerError(Exception):
    """Базовое исключение для всех ошибок приложения."""
    pass

class NotFoundError(WikiExplorerError):
    """Статья не найдена."""
    pass

class ApiError(WikiExplorerError):
    """Ошибка при обращении к API Wikipedia."""
    pass

class NetworkError(WikiExplorerError):
    """Сетевая ошибка (таймаут, отказ соединения и т.п.)."""
    pass