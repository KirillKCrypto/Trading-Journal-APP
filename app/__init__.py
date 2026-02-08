from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
from dotenv import load_dotenv

db = SQLAlchemy()


def create_app():
    load_dotenv()
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    static_dir = os.path.join(root_dir, 'static')

    app = Flask(__name__, static_folder=static_dir, static_url_path='/static')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///trades.db')
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24))

    db.init_app(app)

    from .routes import register_routes
    register_routes(app)

    with app.app_context():
        db.create_all()

    return app