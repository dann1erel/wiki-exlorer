"""Функции для получения статистики просмотров статей через Pageviews API."""

import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from urllib.parse import quote
import logging

logger = logging.getLogger(__name__)

# User-Agent для соблюдения правил
APP_USER_AGENT = "WikiExplorerCLI/1.0 (https://github.com/yourusername/wiki-explorer; your-email@example.com)"


def fetch_pageviews(title: str, lang: str, days: int) -> List[Dict[str, any]]:
    """
    Получает ежедневную статистику просмотров статьи за последние N дней.

    Параметры:
        title: название статьи
        lang: языковой код (ru, en и т.д.)
        days: количество дней (максимум 90)

    Возвращает:
        Список словарей [{"date": "YYYY-MM-DD", "views": int}, ...]
        от самой старой даты к новой. Для дней без данных views = 0.
    """
    # Ограничиваем дни
    days = min(max(days, 1), 90)
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days - 1)

    # Формируем URL
    project = f"{lang}.wikipedia"
    # Кодируем название статьи (заменяем пробелы на _, остальное кодируется)
    encoded_title = quote(title.replace(' ', '_'))
    granularity = "daily"
    # Формат дат: YYYYMMDDHHMMSS
    start_str = start_date.strftime("%Y%m%d") + "00"
    end_str = end_date.strftime("%Y%m%d") + "00"

    url = (f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
           f"{project}/all-access/user/{encoded_title}/{granularity}/{start_str}/{end_str}")

    headers = {'User-Agent': APP_USER_AGENT}

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 404:
            # Статья не найдена в статистике или нет данных
            logger.info(f"No pageviews data for '{title}' in {lang}.wikipedia")
            return []
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"Ошибка при запросе к Pageviews API: {e}") from e

    items = data.get("items", [])
    # Создаём словарь views по дате (YYYY-MM-DD)
    views_by_date = {}
    for item in items:
        timestamp = item.get("timestamp")  # формат YYYYMMDDHH
        if timestamp and len(timestamp) >= 8:
            date_str = f"{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]}"
            views = item.get("views", 0)
            views_by_date[date_str] = views

    # Формируем полный список дат от start_date до end_date
    result = []
    current = start_date
    while current <= end_date:
        date_str = current.strftime("%Y-%m-%d")
        views = views_by_date.get(date_str, 0)
        result.append({"date": date_str, "views": views})
        current += timedelta(days=1)

    return result