"""Custom exceptions for Wiki-Explorer."""


class WikiExplorerError(Exception):
    """Base application exception."""


class ArticleNotFoundError(WikiExplorerError):
    """Raised when requested Wikipedia article does not exist."""


class ApiRequestError(WikiExplorerError):
    """Raised when HTTP request to API fails."""


class InvalidApiResponseError(WikiExplorerError):
    """Raised when API response has unexpected structure."""


class InvalidUserInputError(WikiExplorerError):
    """Raised when user passed invalid command arguments."""


class NoLinksFoundError(WikiExplorerError):
    """Raised when requested article has no internal links."""


class GraphBuildError(WikiExplorerError):
    """Raised when graph cannot be built."""


class FileSaveError(WikiExplorerError):
    """Raised when output file cannot be saved."""


class NoCategoriesFoundError(WikiExplorerError):
    """Raised when requested article has no categories."""

class PageviewsNotFoundError(WikiExplorerError):
    """Raised when pageviews statistics are not found."""


class InvalidDateRangeError(WikiExplorerError):
    """Raised when pageviews date range is invalid."""


class ChartSaveError(WikiExplorerError):
    """Raised when chart image cannot be saved."""



class NoSearchResultsError(WikiExplorerError):
    """Raised when search query has no results."""


class RandomArticleNotFoundError(WikiExplorerError):
    """Raised when random article cannot be found with given filters."""


class NoCategoryMembersError(WikiExplorerError):
    """Raised when requested category contains no pages."""


class NoImagesFoundError(WikiExplorerError):
    """Raised when requested article has no images."""


class ImageDownloadError(WikiExplorerError):
    """Raised when an image cannot be downloaded."""
