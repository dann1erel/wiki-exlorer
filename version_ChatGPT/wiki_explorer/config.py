"""Project configuration constants."""

DEFAULT_LANGUAGE = "ru"
DEFAULT_TIMEOUT = 10
DEFAULT_CATEGORY_LIMIT = 10
DEFAULT_CATEGORIES_LIMIT = 20
DEFAULT_LINKS_LIMIT = 50
DEFAULT_SEARCH_LIMIT = 10
DEFAULT_SEARCH_SORT = "relevance"
DEFAULT_RANDOM_ATTEMPTS = 10
DEFAULT_IMAGES_LIMIT = 10
DEFAULT_DOWNLOAD_DIR = "downloads"
DEFAULT_IMAGE_DOWNLOAD_DELAY = 1.0
DEFAULT_IMAGE_DOWNLOAD_RETRIES = 3
DEFAULT_CATEGORY_MEMBERS_LIMIT = 50
DEFAULT_GRAPH_LIMIT = 30
DEFAULT_GRAPH_OUTPUT = "graph.png"
DEFAULT_GRAPH_FORMAT = "png"
DEFAULT_GRAPH_DEPTH = 1
DEFAULT_GRAPH_MAX_NODES = 200
DEFAULT_PAGEVIEWS_DAYS = 30
DEFAULT_PAGEVIEWS_LANGUAGE = "en"
DEFAULT_PAGEVIEWS_LAG_DAYS = 3
DEFAULT_CHART_TYPE = "none"
DEFAULT_PAGEVIEWS_OUTPUT = "pageviews.png"

MEDIAWIKI_API_URL = "https://{lang}.wikipedia.org/w/api.php"
ARTICLE_URL = "https://{lang}.wikipedia.org/wiki/{title}"
PAGEVIEWS_API_URL = (
    "https://wikimedia.org/api/rest_v1/metrics/pageviews/"
    "per-article/{project}/{access}/{agent}/{article}/{granularity}/{start}/{end}"
)

USER_AGENT = (
    "Wiki-Explorer/0.1 "
    "(educational CLI project; contact: example@example.com)"
)
