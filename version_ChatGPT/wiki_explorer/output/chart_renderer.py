"""Chart rendering helpers for Wiki-Explorer."""

from __future__ import annotations

from pathlib import Path
import logging

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from wiki_explorer.exceptions import ChartSaveError
from wiki_explorer.services.pageviews_service import PageviewItem


logger = logging.getLogger(__name__)


class ChartRenderer:
    """Render small text and image charts."""

    def render_ascii_chart(
        self,
        items: list[PageviewItem],
        width: int = 40,
        lang: str = "ru",
    ) -> str:
        """Build a simple ASCII bar chart for pageviews."""
        is_english = lang.lower().startswith("en")

        if not items:
            return (
                "No data to build a chart."
                if is_english
                else "Нет данных для построения графика."
            )

        max_views = max(item.views for item in items)
        if max_views <= 0:
            max_views = 1

        lines = [
            "Pageviews ASCII chart:"
            if is_english
            else "ASCII-график просмотров:"
        ]
        for item in items:
            bar_length = int((item.views / max_views) * width)
            bar = "█" * max(bar_length, 1 if item.views > 0 else 0)
            lines.append(f"{item.date.isoformat()} | {bar} {item.views}")

        return "\n".join(lines)

    def save_pageviews_chart(
        self,
        items: list[PageviewItem],
        output_path: str | Path,
        lang: str = "ru",
    ) -> Path:
        """Save a PNG chart with daily pageviews."""
        path = Path(output_path)
        if path.suffix.lower() != ".png":
            path = path.with_suffix(".png")

        logger.info("Saving pageviews chart to: %s", path)

        try:
            dates = [item.date.isoformat() for item in items]
            views = [item.views for item in items]

            figure_width = max(8, min(18, len(items) * 0.45))
            plt.figure(figsize=(figure_width, 6))
            plt.plot(dates, views, marker="o")
            if lang.lower().startswith("en"):
                plt.title("Article pageviews")
                plt.xlabel("Date")
                plt.ylabel("Views")
            else:
                plt.title("Статистика просмотров статьи")
                plt.xlabel("Дата")
                plt.ylabel("Просмотры")
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()
            plt.savefig(path, format="png", bbox_inches="tight")
            plt.close()
        except (OSError, RuntimeError, ValueError) as exc:
            logger.error("Chart save failed: %s", exc)
            raise ChartSaveError(
                "Не удалось сохранить график. Проверьте путь и права доступа."
            ) from exc

        logger.info("Chart saved successfully: %s", path)
        return path
