from . import db
from datetime import datetime

class Trade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date)
    symbol = db.Column(db.String)
    weekday = db.Column(db.String)
    session = db.Column(db.String)
    position = db.Column(db.String)
    direction = db.Column(db.String)
    bias = db.Column(db.String)
    logic = db.Column(db.Text)
    entry_details = db.Column(db.Text)
    risk = db.Column(db.Float)
    rr = db.Column(db.Float)
    result_type = db.Column(db.String)
    mistakes = db.Column(db.Text)
    notes = db.Column(db.Text)
    profit = db.Column(db.Float)
    win_rate = db.Column(db.Float)
    screenshot_1h_path = db.Column(db.String)
    screenshot_5m_path = db.Column(db.String)
    screenshot_3m_path = db.Column(db.String)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    priority = db.Column(db.String(50))
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
