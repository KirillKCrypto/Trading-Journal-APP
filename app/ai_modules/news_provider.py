import os
import json
import time
import random
import threading
import requests
import logging

logger = logging.getLogger(__name__)


class ForexNewsProvider:
    """Класс для загрузки и кеширования экономических новостей ForexFactory"""

    def __init__(self, cache_dir="cache", static_cache_file="forexfactory_static.json"):
        # Создаём папку cache, если её нет
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

        self.static_cache_file = os.path.join(self.cache_dir, static_cache_file)
        self.static_cache = {}
        self.news_cache = {"timestamp": 0, "news": []}
        self.url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36"
            )
        }

        # Загрузка и сохранение статичного кеша при старте
        self._load_static_cache()
        self._save_static_cache()

        # Запуск периодического обновления новостей
        self._start_periodic_update()

    def _load_static_cache(self):
        """Загрузка статичного кеша с диска при старте"""
        if os.path.exists(self.static_cache_file):
            try:
                with open(self.static_cache_file, "r", encoding="utf-8") as f:
                    self.static_cache = json.load(f)
                logger.info("Статичный кеш загружен с диска.")
            except Exception as e:
                logger.error(f"Не удалось загрузить статичный кеш: {e}")
                self.static_cache = {}

    def _save_static_cache(self):
        """Сохранение статичного кеша на диск"""
        try:
            with open(self.static_cache_file, "w", encoding="utf-8") as f:
                json.dump(self.static_cache, f, ensure_ascii=False, indent=2)
            logger.info(f"Статичный кеш сохранён на диск: {self.static_cache_file}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении статичного кеша: {e}")

    def _update_news_cache(self):
        """Загрузка новостей и обновление кеша"""
        try:
            resp = requests.get(self.url, headers=self.headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            now = int(time.time())

            # Обновляем статичный кеш раз в сутки
            if not self.static_cache or (now - self.static_cache.get("timestamp", 0) > 86400):
                self.static_cache = {
                    "timestamp": now,
                    "events": [
                        {
                            "date": item.get("date"),
                            "title": item.get("title"),
                            "impact": item.get("impact"),
                            "country": item.get("country"),
                        }
                        for item in data if item.get("country") == "USD"
                    ]
                }
                self._save_static_cache()

            # Динамический кеш: только важные события
            important_news = [
                {
                    "date": item.get("date"),
                    "title": item.get("title"),
                    "forecast": item.get("forecast") or "нет данных",
                    "previous": item.get("previous") or "нет данных",
                    "actual": item.get("actual") or "ещё не вышло",
                    "impact": item.get("impact"),
                }
                for item in data if item.get("impact") in ["High", "Medium"] and item.get("country") == "USD"
            ]
            self.news_cache = {"timestamp": now, "news": important_news}
            logger.info(f"Новости ForexFactory обновлены ({len(important_news)} событий).")

        except Exception as e:
            logger.error(f"Ошибка при получении данных с ForexFactory: {e}")
            if not self.news_cache["news"]:
                self.news_cache["news"] = [{"error": "Не удалось получить новости"}]

    def _start_periodic_update(self):
        """Запуск периодического обновления новостей каждый час ± 5 минут"""

        def updater():
            self._update_news_cache()
            delay = 3600 + random.randint(-300, 300)
            threading.Timer(delay, updater).start()

        updater()

    def get_latest_news(self, top_k: int = None):
        """
        Возвращает актуальные новости
        :param top_k: если указано, вернёт не более top_k новостей
        """
        news = self.news_cache.get("news", [])
        if top_k:
            return news[:top_k]
        return news