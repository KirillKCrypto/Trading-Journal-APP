import os
import requests
import numpy as np
import faiss
import re
from datetime import datetime
from sqlalchemy.orm import Session
from typing import List, Optional
from sentence_transformers import SentenceTransformer
from app.models import Trade

# Импортируем провайдер новостей
from ..ai_modules.news_provider import ForexNewsProvider


class AI_Client:
    """
    Оптимизированная AI-система для анализа торговых операций и новостей
    """

    def __init__(self, db_session: Session):
        self.db = db_session
        self.api_key = os.getenv("OPENROUTER_API_KEY")

        # Инициализация AI компонентов
        self._initialize_ai_components()

        # Загрузка и индексация данных
        self._load_and_index_trades()
        self._load_news_data()

    def _initialize_ai_components(self):
        """Инициализация AI моделей и настроек"""
        print("🔄 Инициализация AI системы...")
        self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        self.dim = 384

        # FAISS индексы
        self.trade_index = None
        self.news_index = None
        self.trade_texts = []
        self.news_texts = []
        self.all_trades = []

        # Настройки API
        self.ai_model = "meta-llama/llama-3.3-70b-instruct:free"
        self.base_url = "https://openrouter.ai/api/v1"

    def _load_and_index_trades(self):
        """Загрузка и векторная индексация сделок из БД"""
        print("📊 Загрузка сделок из базы данных...")
        self.all_trades = self.db.query(Trade).order_by(Trade.date.desc()).all()

        if not self.all_trades:
            print("⚠️ В базе данных отсутствуют сделки")
            return

        # Формирование текстовых описаний сделок
        self.trade_texts = [
            f"СДЕЛКА: Дата={trade.date.strftime('%Y-%m-%d')}, "
            f"Символ={trade.symbol}, Направление={trade.direction}, "
            f"R:R={trade.rr}, Профит=${trade.profit}, Результат={trade.result_type}, "
            f"Сессия={trade.session}, Позиция={trade.position}, "
            f"Комментарий={trade.notes or 'нет комментария'}"
            for trade in self.all_trades
        ]

        print(f"📈 Загружено {len(self.trade_texts)} сделок")

        # Построение векторного индекса для сделок
        embeddings = [
            self.embedding_model.encode(text, convert_to_numpy=True).astype("float32")
            for text in self.trade_texts
        ]

        if embeddings:
            embeddings_array = np.vstack(embeddings)
            self.trade_index = faiss.IndexFlatL2(self.dim)
            self.trade_index.add(embeddings_array)
            print("✅ Векторный индекс сделок построен")

    def _load_news_data(self):
        """Загрузка и индексация новостей через ForexNewsProvider"""
        try:
            # Инициализация провайдера
            provider = ForexNewsProvider()

            # Получаем все новости (top_k=None)
            news_data = provider.get_latest_news(top_k=None)

            if not news_data:
                print("📰 Новости не загружены")
                return

            # Формируем текстовые описания новостей для AI
            self.news_texts = [
                f"НОВОСТЬ: Дата={news.get('date')}, Заголовок={news.get('title')}, "
                f"Источник=ForexFactory, Важность={news.get('impact')}, "
                f"Прогноз={news.get('forecast', 'нет данных')}, "
                f"Предыдущее={news.get('previous', 'нет данных')}, "
                f"Фактическое={news.get('actual', 'ещё не вышло')}"
                for news in news_data
            ]

            # Создание векторных эмбеддингов и FAISS индекса
            embeddings = [
                self.embedding_model.encode(text, convert_to_numpy=True).astype("float32")
                for text in self.news_texts
            ]

            if embeddings:
                embeddings_array = np.vstack(embeddings)
                self.news_index = faiss.IndexFlatL2(self.dim)
                self.news_index.add(embeddings_array)
                print(f"📰 Проиндексировано {len(news_data)} новостей")

        except Exception as e:
            print(f"⚠️ Ошибка загрузки новостей: {e}")

    def _extract_date_from_query(self, user_query: str) -> Optional[str]:
        """Извлечение даты из текстового запроса"""
        date_patterns = [
            r'(\d{4}\.\d{2}\.\d{2})',  # 2025.07.10
            r'(\d{1,2}\.\d{1,2}\.\d{4})',  # 10.07.2025
            r'(\d{1,2}\.\d{1,2})',  # 10.07
            r'(\d{4}-\d{2}-\d{2})',  # 2025-07-10
        ]

        for pattern in date_patterns:
            match = re.search(pattern, user_query)
            if match:
                return match.group(1)
        return None

    def _normalize_date(self, date_str: str) -> Optional[str]:
        """Нормализация даты к формату YYYY-MM-DD"""
        date_formats = [
            '%Y.%m.%d',  # 2025.07.10
            '%d.%m.%Y',  # 10.07.2025
            '%Y-%m-%d',  # 2025-07-10
        ]

        # Для дат без года добавляем текущий год
        if re.match(r'^\d{1,2}\.\d{1,2}$', date_str):
            date_str = f"{date_str}.{datetime.now().year}"
            date_formats.append('%d.%m.%Y')

        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                return parsed_date.strftime('%Y-%m-%d')
            except ValueError:
                continue
        return None

    def _find_trades_by_date(self, date_str: str) -> List[str]:
        """Поиск сделок по конкретной дате"""
        normalized_date = self._normalize_date(date_str)
        if not normalized_date:
            return []

        found_trades = []
        for trade_text in self.trade_texts:
            # Извлечение даты из описания сделки
            date_match = re.search(r'Дата=([^,]+)', trade_text)
            if date_match and date_match.group(1) == normalized_date:
                found_trades.append(trade_text)

        return found_trades

    def _get_trade_count_from_query(self, user_query: str) -> int:
        """Определение количества запрашиваемых сделок"""
        user_query_lower = user_query.lower()

        # Поиск числовых указаний
        numbers = re.findall(r'\d+', user_query)
        if numbers:
            return min(int(numbers[0]), 15)

        # Анализ семантических указаний
        count_mapping = {
            'несколько': 3, 'немного': 3, 'пару': 2,
            'десяток': 10, 'около десяти': 10,
            'много': 8, 'все': min(15, len(self.trade_texts)),
            'полный': min(15, len(self.trade_texts))
        }

        for keyword, count in count_mapping.items():
            if keyword in user_query_lower:
                return count

        return 5  # Значение по умолчанию

    def _search_relevant_trades(self, query: str, top_k: int = 5) -> List[str]:
        """Семантический поиск релевантных сделок"""
        if not self.trade_index or not self.trade_texts:
            return []

        try:
            query_embedding = self.embedding_model.encode(query, convert_to_numpy=True)
            query_embedding = query_embedding.astype("float32").reshape(1, -1)

            distances, indices = self.trade_index.search(query_embedding, top_k)

            return [
                self.trade_texts[idx] for idx in indices[0]
                if 0 <= idx < len(self.trade_texts)
            ]
        except Exception as e:
            print(f"❌ Ошибка семантического поиска сделок: {e}")
            return []

    def _search_relevant_news(self, query: str, top_k: int = 15) -> List[str]:
        """Семантический поиск релевантных новостей"""
        if not self.news_index or not self.news_texts:
            return []

        try:
            query_embedding = self.embedding_model.encode(query, convert_to_numpy=True)
            query_embedding = query_embedding.astype("float32").reshape(1, -1)

            distances, indices = self.news_index.search(query_embedding, top_k)

            return [
                self.news_texts[idx] for idx in indices[0]
                if 0 <= idx < len(self.news_texts)
            ]
        except Exception as e:
            print(f"❌ Ошибка поиска новостей: {e}")
            return []

    def _get_latest_trades(self, n: int) -> List[str]:
        """Получение последних сделок по хронологии"""
        return self.trade_texts[:n]

    def _classify_query_intent(self, user_query: str) -> dict:
        """Классификация намерения пользователя"""
        query_lower = user_query.lower()

        # Проверка на наличие даты в запросе
        has_date = self._extract_date_from_query(user_query) is not None

        # Ключевые слова для классификации
        intent_patterns = {
            'analysis': ['анализ', 'проанализир', 'разбор', 'разбери', 'посмотри'],
            'psychology': ['психолог', 'эмоц', 'дисциплин', 'жадност', 'страх', 'fomo'],
            'mistakes': ['ошибк', 'проблем', 'неправ', 'исправ', 'улучш'],
            'news': ['новости', 'news', 'события', 'экономика', 'рынок', 'фундаментал']
        }

        # Определение основного намерения
        intent = "general"
        for intent_type, keywords in intent_patterns.items():
            if any(keyword in query_lower for keyword in keywords):
                intent = intent_type
                break

        # Определение необходимости данных
        needs_trades = any(word in query_lower for word in
                           ['сделк', 'последн', 'недавн', 'мои', 'журнал', 'истори']) or has_date

        needs_news = intent == "news" or any(word in query_lower for word in
                                             ['новости', 'события', 'экономика'])

        return {
            "intent": intent,
            "needs_trades": needs_trades,
            "needs_news": needs_news,
            "has_date": has_date,
            "is_general_question": not needs_trades and not needs_news and intent in ["psychology", "general"]
        }

    def _call_ai_api(self, prompt: str) -> str:
        """Вызов внешнего AI API"""
        if not self.api_key:
            return "❌ Отсутствует API ключ для доступа к AI"

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:5000",
                "X-Title": "Trade Analysis AI"
            }

            payload = {
                "model": self.ai_model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2000,
                "temperature": 0.7,
            }

            response = requests.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=60
            )

            if response.status_code != 200:
                error_msg = response.json().get('error', {}).get('message', 'Unknown error')
                raise Exception(f"API Error {response.status_code}: {error_msg}")

            data = response.json()
            return data["choices"][0]["message"]["content"].strip()

        except Exception as e:
            print(f"❌ Ошибка вызова AI API: {e}")
            return f"⚠️ Временная недоступность AI сервиса. Пожалуйста, повторите запрос позже."

    def _clean_response(self, text: str) -> str:
        """Очистка и форматирование ответа AI"""
        # Удаление избыточных пробелов и переносов
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        return text.strip()

    def _create_adaptive_prompt(self, user_query: str, trades: List[str], query_intent: dict) -> str:
        """Создание адаптивного промпта для анализа сделок"""
        if not trades and query_intent["needs_trades"]:
            return self._create_no_data_prompt(user_query)

        trades_context = "\n".join([f"{i + 1}. {trade}" for i, trade in enumerate(trades)])

        # Базовый контекст для AI
        base_context = f"""
Пользовательский запрос: "{user_query}"

Контекст сделок:
{trades_context}
"""

        # Специализированные инструкции по типам запросов
        intent_instructions = {
            "analysis": "Проведи детальный анализ представленных сделок. Выяви паттерны, сильные стороны и зоны роста. Будь конкретен и дай практические рекомендации.",
            "psychology": "Сфокусируйся на психологических аспектах трейдинга. Проанализируй эмоциональные паттерны и дай советы по улучшению психологической устойчивости.",
            "mistakes": "Выяви системные ошибки и слабые места. Предложи конкретные шаги по исправлению и улучшению торговой дисциплины.",
            "general": "Ответь на вопрос, используя контекст сделок для примеров. Будь поддерживающим и практичным."
        }

        instruction = intent_instructions.get(query_intent["intent"], intent_instructions["general"])

        # Добавляем специфические инструкции для запросов с датами
        if query_intent["has_date"]:
            extracted_date = self._extract_date_from_query(user_query)
            instruction += f"\n\nПользователь запросил анализ конкретно за дату {extracted_date}. Сфокусируйся на сделках за эту дату и дай детальный разбор именно этих операций."

        prompt = f"""
Ты - опытный трейдер-наставник с глубоким пониманием рынков и психологии трейдинга.

{base_context}

{instruction}

Требования к ответу:
- Используй естественный, поддерживающий тон общения
- Обращайся к пользователю на "ты"
- Будь конкретен и практичен
- Используй 2-3 эмодзи для эмоциональных акцентов
- Структурируй ответ логически, но без жестких шаблонов
- Сфокусируйся на самых важных insights
- Предлагай actionable рекомендации

Ответь так, как будто даешь совет коллеге-трейдеру.
"""
        return prompt

    def _create_news_prompt(self, user_query: str, news: List[str]) -> str:
        """Создание промпта для анализа новостей"""
        if not news:
            return f"""
Пользователь запросил: "{user_query}"

В настоящий момент новости не загружены или отсутствуют релевантные данные.

Предложи пользователю:
- Уточнить период для анализа новостей
- Задать вопрос о текущей рыночной ситуации
- Обратиться к другим аспектам трейдинга
"""

        news_context = "\n".join([f"{i + 1}. {item}" for i, item in enumerate(news)])

        return f"""
Ты - опытный финансовый аналитик. Пользователь запросил: "{user_query}"

Актуальные новости для анализа:
{news_context}

Проанализируй эти новости и:
1. Выдели ключевые события, влияющие на рынки
2. Оцени потенциальное влияние на основные активы (акции, валюты, индексы)
3. Дай практические рекомендации для трейдеров
4. Укажи на возможные риски и возможности

Будь конкретен и используй только предоставленные данные.
"""

    def _create_no_data_prompt(self, user_query: str) -> str:
        """Промпт для случаев отсутствия данных"""
        return f"""
Пользователь запросил: "{user_query}"

В настоящий момент в базе данных отсутствуют сделки для анализа.

Вежливо сообщи об этом пользователю и предложи:
- Добавить сделки в торговый журнал
- Уточнить критерии поиска
- Задать общий вопрос о трейдинге

Будь поддерживающим и предложи альтернативные варианты помощи.
"""

    def analyze(self, user_query: str) -> str:
        """
        Универсальный метод анализа (сделки + новости)
        """
        print(f"🎯 Обработка запроса: '{user_query}'")

        # Анализ намерения пользователя
        query_intent = self._classify_query_intent(user_query)
        print(f"🔍 Распознано намерение: {query_intent['intent']}")

        # Выбор стратегии анализа
        if query_intent["needs_news"]:
            print("📰 Анализ новостей...")
            relevant_news = self._search_relevant_news(user_query, top_k=15)
            print(f"📊 Найдено новостей для анализа: {len(relevant_news)}")
            prompt = self._create_news_prompt(user_query, relevant_news)
        else:
            # Анализ сделок
            relevant_trades = self._find_relevant_trades(user_query, query_intent)
            print(f"📊 Найдено сделок для анализа: {len(relevant_trades)}")
            prompt = self._create_adaptive_prompt(user_query, relevant_trades, query_intent)

        print("🚀 Генерация AI ответа...")
        response = self._call_ai_api(prompt)
        return self._clean_response(response)

    def _find_relevant_trades(self, user_query: str, query_intent: dict) -> List[str]:
        """Интеллектуальный поиск релевантных сделок"""

        # Приоритетный поиск по дате
        if query_intent["has_date"]:
            extracted_date = self._extract_date_from_query(user_query)
            if extracted_date:
                date_trades = self._find_trades_by_date(extracted_date)
                if date_trades:
                    print(f"📅 Найдено сделок по дате {extracted_date}: {len(date_trades)}")
                    return date_trades
                else:
                    print(f"📅 Сделок по дате {extracted_date} не найдено, используем семантический поиск")

        # Стандартные стратегии поиска
        if query_intent["needs_trades"]:
            trade_count = self._get_trade_count_from_query(user_query)

            if any(word in user_query.lower() for word in ['последн', 'недавн']):
                return self._get_latest_trades(trade_count)
            else:
                return self._search_relevant_trades(user_query, trade_count)

        return []  # Для общих вопросов не требуются сделки