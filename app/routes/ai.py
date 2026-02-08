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
last_api_key = None


def get_trade_ai(api_key: str = None):
    global trade_ai, last_api_key

    # Если ключ изменился или AI_Client не создан
    if trade_ai is None or (api_key and api_key != last_api_key):
        print(f"🔄 Создаем/обновляем AI_Client с новым ключом...")
        trade_ai = AI_Client(db.session, api_key=api_key)
        last_api_key = api_key
    elif api_key and trade_ai:
        # Если ключ передан, обновляем существующий
        print(f"🔄 Обновляем API ключ в существующем AI_Client...")
        trade_ai.set_api_key(api_key)
        last_api_key = api_key

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
    data = request.get_json()
    user_text = (data.get("text") or "").strip()
    api_key = (data.get("api_key") or "").strip()

    print(f"🎯 Получен запрос: {user_text}")
    print(f"🔑 Получен API ключ: {api_key[:20] if api_key else 'NO KEY'}...")

    if not user_text:
        return jsonify({"error": "Введите текст запроса."}), 400

    if not api_key:
        return jsonify({"error": "API ключ не передан в запросе."}), 400

    try:
        ai_engine = get_trade_ai(api_key=api_key)

        print(f"✅ AI_Client готов. API ключ: {ai_engine.api_key[:20] if ai_engine.api_key else 'NO KEY'}...")

        response = ai_engine.analyze(user_text)

        html_response = render_markdown_safe(response)
        return jsonify({"response": html_response, "mode": "trades"})

    except Exception as e:
        logger.error(f"[AI] Критическая ошибка: {e}", exc_info=True)
        return jsonify({"error": f"Системная ошибка: {str(e)}"}), 500