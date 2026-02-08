from flask import Blueprint

# Импортируем все blueprints из отдельных модулей
from .trades import trades_bp
from .profile import profile_bp
from .tasks import tasks_bp
from .ai import ai_bp

def register_routes(app):
    app.register_blueprint(trades_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(ai_bp)