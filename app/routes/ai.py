import logging
from app import db
from app.ai_modules.ai_client import AI_Client
from dotenv import load_dotenv
from flask import Blueprint, request, jsonify, render_template
import markdown2

load_dotenv()
logger = logging.getLogger(__name__)



ai_bp = Blueprint("ai", __name__, url_prefix="/ai")


trade_ai = None


def get_trade_ai():
    global trade_ai
    if trade_ai is None:
        trade_ai = AI_Client(db.session)
    return trade_ai


@ai_bp.route("/", methods=["GET"])
def ai_home():
    return render_template("ai_helper.html")


def render_markdown_safe(text: str) -> str:
    return markdown2.markdown(
        text,
        extras=["fenced-code-blocks", "break-on-newline", "tables"]
    )


@ai_bp.route("/ask", methods=["POST"])
def ai_ask():
    # Получает JSON с вопросом пользователя
    data = request.get_json()
    user_text = (data.get("text") or "").strip()

    # Валидация запроса
    if not user_text:
        return jsonify({"error": "Введите текст запроса."}), 400

    print(f"🎯 Получен запрос: {user_text}")

    try:
        ai_engine = get_trade_ai()
        response = ai_engine.analyze(user_text)  # Отправляет запрос в AI

        # Конвертирует Markdown в HTML для красивого отображения
        html_response = render_markdown_safe(response)
        return jsonify({"response": html_response, "mode": "trades"})

    except Exception as e:
        logger.error(f"[AI] Критическая ошибка: {e}", exc_info=True)
        return jsonify({"error": f"Системная ошибка: {str(e)}"}), 500